document.addEventListener("DOMContentLoaded", () => {
  const mapElement = document.getElementById("city-map");
  const reportData = document.getElementById("public-reports");
  if (!mapElement || !reportData) return;
  const mapStatus = document.getElementById("public-map-status");

  if (!window.L) {
    mapElement.setAttribute("aria-label", "Mappa non disponibile: libreria cartografica non caricata");
    if (mapStatus) {
      mapStatus.hidden = false;
      mapStatus.textContent = "La libreria della mappa non è disponibile. Le segnalazioni restano consultabili nell’elenco.";
    }
    return;
  }

  const reports = JSON.parse(reportData.textContent || "[]");
  const map = L.map(mapElement, { scrollWheelZoom: false }).setView([45.4642, 9.19], 12);
  const tileLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    referrerPolicy: "strict-origin-when-cross-origin",
    crossOrigin: true,
  }).addTo(map);
  const failedTiles = new Set();
  tileLayer.on("loading", () => failedTiles.clear());
  tileLayer.on("tileerror", () => {
    failedTiles.add("error");
    if (mapStatus) {
      mapStatus.hidden = false;
      mapStatus.textContent = "OpenStreetMap non ha caricato tutte le tessere. Puoi consultare le segnalazioni nell’elenco.";
    }
  });
  tileLayer.on("load", () => {
    if (failedTiles.size === 0 && mapStatus) mapStatus.hidden = true;
  });

  const markers = new Map();
  reports.forEach((report) => {
    const marker = L.circleMarker([report.latitude, report.longitude], {
      radius: 7,
      color: "#fbfcf9",
      weight: 2,
      fillColor: "#d35d48",
      fillOpacity: 1,
    }).addTo(map);
    const media = report.attachments?.[0];
    const mediaPreview = media
      ? media.media_type === "FOTO"
        ? `<br><img src="${escapeHtml(media.url)}" alt="" width="180">`
        : `<br><a href="${escapeHtml(media.url)}" target="_blank" rel="noopener">Guarda il video</a>`
      : "";
    marker.bindPopup(`<strong>${escapeHtml(report.title)}</strong><br>${escapeHtml(report.published_at)}${mediaPreview}`);
    markers.set(String(report.id), marker);
  });

  document.querySelectorAll("[data-report-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const marker = markers.get(row.dataset.reportId);
      if (!marker) return;
      map.setView(marker.getLatLng(), 16);
      marker.openPopup();
    });
  });

  function escapeHtml(value) {
    const node = document.createElement("span");
    node.textContent = value ?? "";
    return node.innerHTML;
  }
});