document.addEventListener("DOMContentLoaded", () => {
  const mapElement = document.getElementById("report-location-map");
  const latitudeInput = document.getElementById("latitude");
  const longitudeInput = document.getElementById("longitude");
  const locateButton = document.getElementById("use-current-location");
  const locationStatus = document.getElementById("location-status");
  const mapStatus = document.getElementById("map-status");

  if (!mapElement || !latitudeInput || !longitudeInput) return;

  if (!window.L) {
    mapStatus.hidden = false;
    mapStatus.textContent = "Mappa non caricata. Puoi inserire le coordinate manualmente.";
    return;
  }

  const defaultLocation = [45.4642, 9.19];
  const existingLatitude = Number(latitudeInput.value);
  const existingLongitude = Number(longitudeInput.value);
  const hasCoordinates =
    latitudeInput.value.trim() !== "" &&
    longitudeInput.value.trim() !== "" &&
    Number.isFinite(existingLatitude) &&
    Number.isFinite(existingLongitude) &&
    existingLatitude >= -90 && existingLatitude <= 90 &&
    existingLongitude >= -180 && existingLongitude <= 180;
  const initialLocation = hasCoordinates ? [existingLatitude, existingLongitude] : defaultLocation;
  const map = L.map(mapElement, { scrollWheelZoom: false }).setView(initialLocation, hasCoordinates ? 16 : 12);
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
    mapStatus.hidden = false;
    mapStatus.textContent = "Lo sfondo cartografico non è disponibile. Puoi comunque selezionare la posizione o inserire le coordinate.";
  });
  tileLayer.on("load", () => {
    if (failedTiles.size === 0) mapStatus.hidden = true;
  });

  let marker = hasCoordinates ? L.marker(initialLocation, { draggable: true }).addTo(map) : null;

  function setLocation(latitude, longitude, zoom = 16) {
    latitudeInput.value = latitude.toFixed(6);
    longitudeInput.value = longitude.toFixed(6);
    const location = [latitude, longitude];
    if (!marker) {
      marker = L.marker(location, { draggable: true }).addTo(map);
      marker.on("dragend", updateInputsFromMarker);
    } else {
      marker.setLatLng(location);
    }
    map.setView(location, zoom);
    locationStatus.textContent = `Posizione selezionata: ${latitudeInput.value}, ${longitudeInput.value}`;
  }

  function updateInputsFromMarker() {
    const location = marker.getLatLng();
    setLocation(location.lat, location.lng, map.getZoom());
  }

  if (marker) {
    marker.on("dragend", updateInputsFromMarker);
    locationStatus.textContent = `Posizione selezionata: ${latitudeInput.value}, ${longitudeInput.value}`;
  }

  map.on("click", (event) => setLocation(event.latlng.lat, event.latlng.lng));

  function syncMapFromInputs() {
    const latitude = Number(latitudeInput.value);
    const longitude = Number(longitudeInput.value);
    if (
      latitudeInput.value === "" ||
      longitudeInput.value === "" ||
      latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180
    ) {
      return;
    }
    setLocation(latitude, longitude);
  }

  latitudeInput.addEventListener("change", syncMapFromInputs);
  longitudeInput.addEventListener("change", syncMapFromInputs);

  locateButton?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      locationStatus.textContent = "Geolocalizzazione non disponibile: inserisci le coordinate manualmente.";
      return;
    }
    locationStatus.textContent = "Richiesta della posizione in corso...";
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setLocation(coords.latitude, coords.longitude),
      () => {
        locationStatus.textContent = "Posizione non ottenuta. Consenti l’accesso o inserisci le coordinate manualmente.";
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  });
});
