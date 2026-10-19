import hashlib
import mimetypes
import os
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from sqlalchemy import and_, func, or_, select
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    Attachment,
    AuditLog,
    Category,
    CategoryAssignment,
    ModerationDecision,
    Publication,
    Report,
    ReportVersion,
    StatusHistory,
    Support,
    User,
    VersionAttachment,
)


main = Blueprint("main", __name__)

LIFECYCLE_TRANSITIONS = {
    "PUBBLICATA": {"IN_CARICO_COMITATO", "ARCHIVIATA", "RITIRATA"},
    "IN_CARICO_COMITATO": {"SELEZIONATA", "ARCHIVIATA", "RITIRATA"},
    "SELEZIONATA": {"INVIATA_CANDIDATI", "ARCHIVIATA", "RITIRATA"},
    "INVIATA_CANDIDATI": {"ARCHIVIATA"},
}
DEFAULT_CATEGORIES = (
    "Accessibilità",
    "Acqua e fognature",
    "Illuminazione",
    "Rifiuti e decoro",
    "Strade e marciapiedi",
    "Verde pubblico",
)


def available_categories():
    categories = set(db.session.scalars(
        select(Category.name).where(Category.active.is_(True)).order_by(Category.name)
    ).all())
    return sorted(categories.union(DEFAULT_CATEGORIES))


def render_report_form(user, categories=None):
    return render_template(
        "new_report.html",
        user=user,
        categories=categories or available_categories(),
    )


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def require_login():
    user = get_current_user()
    if user is None:
        return None
    return user


@main.get("/")
def home():
    preview_mode = current_app.config["PREVIEW_MODE"]
    reports = []

    statement = (
        select(
            Report.id,
            ReportVersion.title,
            ReportVersion.description,
            ReportVersion.latitude,
            ReportVersion.longitude,
            Publication.published_at,
            Attachment.id.label("attachment_id"),
            Attachment.media_type,
        )
        .join(Publication, Publication.report_id == Report.id)
        .join(ReportVersion, ReportVersion.id == Publication.version_id)
        .outerjoin(
            VersionAttachment,
            and_(
                VersionAttachment.version_id == ReportVersion.id,
                VersionAttachment.report_id == Report.id,
            ),
        )
        .outerjoin(Attachment, Attachment.id == VersionAttachment.attachment_id)
        .where(
            Report.operational_status == "PUBBLICATA",
            ReportVersion.moderation_status == "APPROVATA",
            or_(Attachment.id.is_(None), Attachment.file_status == "DISPONIBILE"),
        )
        .order_by(Publication.published_at.asc(), Report.id.asc())
    )
    rows = db.session.execute(statement).mappings()
    reports_by_id = {}
    for row in rows:
        report = reports_by_id.setdefault(
            row["id"],
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "published_at": row["published_at"].strftime("%d/%m/%Y"),
                "attachments": [],
            },
        )
        if row["attachment_id"]:
            report["attachments"].append(
                {
                    "media_type": row["media_type"],
                    "url": url_for(
                        "main.public_attachment",
                        report_id=row["id"],
                        attachment_id=row["attachment_id"],
                    ),
                }
            )
    reports = list(reports_by_id.values())

    return render_template("home.html", reports=reports, preview_mode=preview_mode)


@main.get("/reports/<int:report_id>/attachments/<int:attachment_id>")
def public_attachment(report_id, attachment_id):
    attachment = db.session.scalar(
        select(Attachment)
        .join(VersionAttachment, VersionAttachment.attachment_id == Attachment.id)
        .join(
            Publication,
            and_(
                Publication.report_id == VersionAttachment.report_id,
                Publication.version_id == VersionAttachment.version_id,
            ),
        )
        .join(Report, Report.id == Publication.report_id)
        .join(ReportVersion, ReportVersion.id == Publication.version_id)
        .where(
            Report.id == report_id,
            Report.operational_status == "PUBBLICATA",
            ReportVersion.moderation_status == "APPROVATA",
            Attachment.id == attachment_id,
            Attachment.file_status == "DISPONIBILE",
        )
    )
    if attachment is None:
        return "Allegato non disponibile", 404
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        attachment.storage_ref,
        mimetype=attachment.content_type,
        as_attachment=False,
    )


@main.get("/register")
def register():
    return render_template("register.html")


@main.post("/register")
def register_submit():
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not first_name or not last_name or not email or not password:
        flash("Tutti i campi sono obbligatori.")
        return render_template("register.html")

    if password != confirm_password:
        flash("Le password non coincidono.")
        return render_template("register.html")

    if len(password) < 8:
        flash("La password deve avere almeno 8 caratteri.")
        return render_template("register.html")

    existing_user = db.session.scalar(select(User).where(User.email == email))
    if existing_user:
        flash("Questa email è già registrata.")
        return render_template("register.html")

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=generate_password_hash(password),
        role="UTENTE",
        account_status="ATTIVO",
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(
        AuditLog(
            actor_id=user.id,
            action="UTENTE_REGISTRATO",
            entity_type="utente",
            entity_id=user.id,
            details={"email": user.email},
        )
    )
    db.session.commit()

    flash("Registrazione completata. Effettua l’accesso per continuare.")
    return redirect(url_for("main.login"))


@main.get("/login")
def login():
    if get_current_user():
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@main.post("/login")
def login_submit():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = db.session.scalar(select(User).where(User.email == email))
    if user is None or not check_password_hash(user.password_hash, password) or user.account_status != "ATTIVO":
        db.session.add(
            AuditLog(
                actor_id=user.id if user else None,
                action="ACCESSO_FALLITO",
                entity_type="autenticazione",
                details={"email": email},
            )
        )
        db.session.commit()
        flash("Credenziali non valide.")
        return render_template("login.html")

    session["user_id"] = user.id
    session["user_role"] = user.role
    db.session.add(
        AuditLog(
            actor_id=user.id,
            action="ACCESSO_ESEGUITO",
            entity_type="autenticazione",
            entity_id=user.id,
        )
    )
    db.session.commit()
    flash("Accesso eseguito con successo.")
    return redirect(url_for("main.dashboard"))


@main.get("/logout")
def logout():
    user = get_current_user()
    if user is not None:
        db.session.add(
            AuditLog(
                actor_id=user.id,
                action="DISCONNESSIONE",
                entity_type="autenticazione",
                entity_id=user.id,
            )
        )
        db.session.commit()
    session.clear()
    flash("Sei stato disconnesso.")
    return redirect(url_for("main.login"))


@main.get("/dashboard")
def dashboard():
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per accedere al dashboard.")
        return redirect(url_for("main.login"))

    latest_version = (
        select(func.max(ReportVersion.version_number))
        .where(ReportVersion.report_id == Report.id)
        .correlate(Report)
        .scalar_subquery()
    )
    reports = db.session.execute(
        select(Report.id, Report.operational_status, ReportVersion.title, Report.updated_at)
        .join(
            ReportVersion,
            and_(
                ReportVersion.report_id == Report.id,
                ReportVersion.version_number == latest_version,
            ),
        )
        .where(Report.owner_id == user.id)
        .order_by(Report.updated_at.desc())
    ).all()
    return render_template("dashboard.html", user=user, reports=reports)


@main.get("/admin")
def admin_dashboard():
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per accedere all’area admin.")
        return redirect(url_for("main.login"))
    if user.role != "ADMIN":
        return render_template("access_denied.html", user=user)

    return render_template("admin.html", user=user)


@main.get("/admin/reports")
def admin_reports():
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per accedere all’area admin.")
        return redirect(url_for("main.login"))
    if user.role != "ADMIN":
        return render_template("access_denied.html", user=user)

    pending = db.session.execute(
        select(
            Report.id,
            ReportVersion.title,
            ReportVersion.description,
            ReportVersion.created_at,
            ReportVersion.moderation_status,
            Report.owner_id,
            Attachment.id.label("attachment_id"),
            Attachment.media_type,
        )
        .join(ReportVersion, ReportVersion.report_id == Report.id)
        .outerjoin(VersionAttachment, VersionAttachment.version_id == ReportVersion.id)
        .outerjoin(Attachment, Attachment.id == VersionAttachment.attachment_id)
        .where(ReportVersion.moderation_status.in_(["IN_ATTESA_CONTROLLO", "IN_REVISIONE_ADMIN", "IN_ATTESA_CHIARIMENTI"]))
        .order_by(ReportVersion.created_at.desc())
    ).all()

    managed = db.session.execute(
        select(
            Report.id,
            Report.operational_status,
            ReportVersion.title,
            ReportVersion.description,
        )
        .join(Publication, Publication.report_id == Report.id)
        .join(ReportVersion, ReportVersion.id == Publication.version_id)
        .where(Report.operational_status.in_(LIFECYCLE_TRANSITIONS))
        .order_by(Report.updated_at.desc())
    ).all()

    return render_template(
        "admin_reports.html",
        user=user,
        pending_reports=pending,
        managed_reports=managed,
        lifecycle_transitions=LIFECYCLE_TRANSITIONS,
    )


@main.post("/admin/reports/<int:report_id>/status")
def update_report_status(report_id):
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per aggiornare lo stato.")
        return redirect(url_for("main.login"))
    if user.role != "ADMIN":
        return render_template("access_denied.html", user=user)

    report = db.session.get(Report, report_id)
    if report is None:
        flash("Segnalazione non trovata.")
        return redirect(url_for("main.admin_reports"))

    new_status = (request.form.get("status") or "").upper()
    if new_status not in LIFECYCLE_TRANSITIONS.get(report.operational_status, set()):
        flash("Transizione di stato non consentita.")
        return redirect(url_for("main.admin_reports"))

    previous_status = report.operational_status
    report.operational_status = new_status
    reason = (request.form.get("reason") or "").strip() or "Aggiornamento del ciclo di vita."
    db.session.add(
        StatusHistory(
            report_id=report.id,
            actor_id=user.id,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
        )
    )
    db.session.add(
        AuditLog(
            actor_id=user.id,
            action="STATO_SEGNALAZIONE_AGGIORNATO",
            entity_type="segnalazione",
            entity_id=report.id,
            details={"stato_precedente": previous_status, "stato_nuovo": new_status, "motivazione": reason},
        )
    )
    db.session.commit()
    flash("Stato della segnalazione aggiornato.")
    return redirect(url_for("main.admin_reports"))


@main.post("/admin/reports/<int:report_id>/decision")
def report_decision(report_id):
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per moderare le segnalazioni.")
        return redirect(url_for("main.login"))
    if user.role != "ADMIN":
        return render_template("access_denied.html", user=user)

    report = db.session.get(Report, report_id)
    if report is None:
        flash("Segnalazione non trovata.")
        return redirect(url_for("main.admin_reports"))

    if report.owner_id == user.id:
        flash("Non puoi moderare una tua segnalazione.")
        return redirect(url_for("main.admin_reports"))

    version = db.session.execute(
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_number.desc(), ReportVersion.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if version is None:
        flash("Non esiste alcuna versione da valutare.")
        return redirect(url_for("main.admin_reports"))

    outcome = (request.form.get("outcome") or "").upper()
    reason = (request.form.get("reason") or "").strip() or "Valutazione amministrativa."
    previous_status = report.operational_status

    if outcome == "APPROVATA":
        version.moderation_status = "APPROVATA"
        report.operational_status = "PUBBLICATA"
        publication = db.session.scalar(select(Publication).where(Publication.report_id == report.id))
        if publication is None:
            db.session.add(Publication(report_id=report.id, version_id=version.id))
        else:
            publication.version_id = version.id
        message = "Segnalazione approvata e pubblicata."
    elif outcome == "RIFIUTATA":
        version.moderation_status = "RIFIUTATA"
        report.operational_status = "ARCHIVIATA"
        message = "Segnalazione rifiutata."
    elif outcome == "RICHIESTE_MODIFICHE":
        version.moderation_status = "IN_ATTESA_CHIARIMENTI"
        report.operational_status = "RICEVUTA"
        message = "Sono state richieste modifiche."
    else:
        flash("Esito non valido.")
        return redirect(url_for("main.admin_reports"))

    db.session.add(
        ModerationDecision(
            version_id=version.id,
            admin_id=user.id,
            outcome=outcome,
            reason=reason,
        )
    )
    db.session.add(
        StatusHistory(
            report_id=report.id,
            actor_id=user.id,
            previous_status=previous_status,
            new_status=report.operational_status,
            reason=reason,
        )
    )
    db.session.add(
        AuditLog(
            actor_id=user.id,
            action=f"MODERAZIONE_{outcome}",
            entity_type="segnalazione",
            entity_id=report.id,
            details={"report_id": report.id, "version_id": version.id, "reason": reason},
        )
    )
    db.session.commit()
    flash(message)
    return redirect(url_for("main.admin_reports"))


@main.get("/reports/new")
def new_report():
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per creare una segnalazione.")
        return redirect(url_for("main.login"))
    return render_report_form(user)


@main.post("/reports/new")
def create_report():
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per creare una segnalazione.")
        return redirect(url_for("main.login"))

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    category_name = (request.form.get("category") or "").strip()
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    media_type = (request.form.get("media_type") or "").upper()
    media_file = request.files.get("media_file")
    categories = available_categories()

    if not title or not description or not category_name or not latitude or not longitude:
        flash("Completa titolo, descrizione, categoria e localizzazione.")
        return render_report_form(user, categories)

    if category_name not in categories:
        flash("Scegli una categoria presente nel catalogo.")
        return render_report_form(user, categories)

    try:
        lat_value = float(latitude)
        lon_value = float(longitude)
    except ValueError:
        flash("Latitudine e longitudine devono essere numeri validi.")
        return render_report_form(user, categories)

    if not (-90 <= lat_value <= 90 and -180 <= lon_value <= 180):
        flash("Latitudine e longitudine fuori dai limiti validi.")
        return render_report_form(user, categories)

    if media_type not in {"FOTO", "VIDEO"}:
        flash("Il tipo di media deve essere FOTO o VIDEO.")
        return render_report_form(user, categories)

    if media_file is None or not media_file.filename:
        flash("Carica una foto o un video come prova della segnalazione.")
        return render_report_form(user, categories)

    safe_name = secure_filename(media_file.filename)
    extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    allowed_extensions = {
        "FOTO": {"jpg", "jpeg", "png", "webp"},
        "VIDEO": {"mp4", "webm", "mov"},
    }
    if extension not in allowed_extensions[media_type]:
        flash("Il formato del file non corrisponde al tipo di media selezionato.")
        return render_report_form(user, categories)

    storage_name = f"{uuid.uuid4().hex}.{extension}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    storage_path = os.path.join(upload_folder, storage_name)
    media_file.save(storage_path)
    file_size = os.path.getsize(storage_path)
    if file_size == 0:
        os.remove(storage_path)
        flash("Il file caricato è vuoto.")
        return render_report_form(user, categories)
    checksum = hashlib.sha256()
    with open(storage_path, "rb") as stored_file:
        for chunk in iter(lambda: stored_file.read(65536), b""):
            checksum.update(chunk)

    category = db.session.scalar(select(Category).where(Category.name == category_name))
    if category is None:
        category = Category(name=category_name, description="Categoria inserita dal flusso di creazione segnalazione")
        db.session.add(category)
        db.session.flush()

    report = Report(owner_id=user.id, operational_status="RICEVUTA")
    db.session.add(report)
    db.session.flush()

    version = ReportVersion(
        report_id=report.id,
        version_number=1,
        editor_id=user.id,
        title=title,
        description=description,
        latitude=lat_value,
        longitude=lon_value,
        location_origin="UTENTE",
        moderation_status="IN_ATTESA_CONTROLLO",
    )
    db.session.add(version)
    db.session.flush()

    attachment = Attachment(
        report_id=report.id,
        uploader_id=user.id,
        media_type=media_type,
        content_type=mimetypes.guess_type(storage_name)[0] or "application/octet-stream",
        storage_ref=storage_name,
        size_bytes=file_size,
        checksum=checksum.hexdigest(),
        file_status="DISPONIBILE",
    )
    db.session.add(attachment)
    db.session.flush()
    db.session.add(
        VersionAttachment(
            version_id=version.id,
            attachment_id=attachment.id,
            report_id=report.id,
            order=0,
        )
    )

    assignment = CategoryAssignment(
        version_id=version.id,
        category_id=category.id,
        origin="UTENTE",
        indication="SELEZIONATA",
        confidence=1.0,
    )
    db.session.add(assignment)
    db.session.add(
        StatusHistory(
            report_id=report.id,
            actor_id=user.id,
            previous_status=None,
            new_status=report.operational_status,
            reason="Segnalazione creata dall’utente.",
        )
    )
    db.session.add(
        AuditLog(
            actor_id=user.id,
            action="SEGNALAZIONE_CREATA",
            entity_type="segnalazione",
            entity_id=report.id,
            details={"version_id": version.id, "attachment_id": attachment.id},
        )
    )
    db.session.commit()

    flash("Segnalazione inviata.")
    return redirect(url_for("main.dashboard"))


@main.get("/admin/attachments/<int:attachment_id>")
def admin_attachment(attachment_id):
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per visualizzare gli allegati.")
        return redirect(url_for("main.login"))
    if user.role != "ADMIN":
        return render_template("access_denied.html", user=user)

    attachment = db.session.get(Attachment, attachment_id)
    if attachment is None or attachment.file_status != "DISPONIBILE":
        flash("Allegato non disponibile.")
        return redirect(url_for("main.admin_reports"))
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], attachment.storage_ref)


@main.post("/reports/<int:report_id>/support")
def support_report(report_id):
    user = require_login()
    if user is None:
        flash("Devi effettuare l’accesso per sostenere una segnalazione.")
        return redirect(url_for("main.login"))

    report = db.session.get(Report, report_id)
    if report is None:
        flash("Segnalazione non trovata.")
        return redirect(url_for("main.home"))

    if report.owner_id == user.id:
        flash("Non puoi sostenere la tua segnalazione.")
        return redirect(url_for("main.home"))

    if report.operational_status != "PUBBLICATA":
        flash("Puoi sostenere solo una segnalazione pubblicata.")
        return redirect(url_for("main.home"))

    existing_support = db.session.get(Support, (user.id, report_id))
    if existing_support is not None:
        flash("Hai già registrato il tuo supporto a questa segnalazione.")
        return redirect(url_for("main.home"))

    support = Support(user_id=user.id, report_id=report_id, active=True)
    db.session.add(support)
    db.session.add(
        AuditLog(
            actor_id=user.id,
            action="SUPPORTO_REGISTRATO",
            entity_type="segnalazione",
            entity_id=report.id,
            details={"report_id": report.id, "supporter_id": user.id},
        )
    )
    db.session.commit()
    flash("Supporto registrato.")
    return redirect(url_for("main.home"))