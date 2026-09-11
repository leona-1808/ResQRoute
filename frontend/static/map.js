// Kakinada-area coordinates layered on top of the same synthetic A-I grid.
// Street/area names are real Kakinada locations used only for visual
// realism. Hospital names are fictional (see hospitals.csv / README).

const NODE_COORDS = {
    A: [16.9975, 82.2560], B: [16.9975, 82.2420], C: [16.9975, 82.2300],
    D: [16.9820, 82.2560], E: [16.9820, 82.2420], F: [16.9820, 82.2300],
    G: [16.9670, 82.2560], H: [16.9670, 82.2420], I: [16.9670, 82.2300],
};

const NODE_LABELS = {
    A: "Kakinada Beach Rd", B: "Main Road", C: "Bhanugudi Jn",
    D: "Suryaraopeta", E: "Port Area", F: "Jagannaickpur",
    G: "RTC Complex", H: "Govt Hospital Area", I: "Airport Road",
};

// Static hospital list matching data/synthetic/hospitals.csv.
// Shown permanently on the map regardless of emergency state.
const HOSPITALS = [
    { node: "C", name: "City Care Hospital (Prototype)" },
    { node: "G", name: "Sunrise Multispecialty (Prototype)" },
    { node: "I", name: "Coastal Emergency Center (Prototype)" },
];

// Simple, crisp inline SVG icons (not emoji, renders identically everywhere)
const AMBULANCE_SVG = `
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 16V7a1 1 0 0 1 1-1h9v10H3z" fill="white"/>
  <path d="M13 10h4l3 3v3h-7v-6z" fill="white"/>
  <circle cx="7" cy="17.5" r="1.6" fill="#dc2626"/>
  <circle cx="17" cy="17.5" r="1.6" fill="#dc2626"/>
  <path d="M6.5 9.5h4M8.5 7.5v4" stroke="#dc2626" stroke-width="1.4" stroke-linecap="round"/>
</svg>`;

const HOSPITAL_SVG = `
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M10.5 3h3v6h6v3h-6v9h-3v-9h-6v-3h6V3z" fill="white"/>
</svg>`;

const map = L.map('map').setView([16.9820, 82.2420], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// small grey dot + always-readable place-name tooltip for every grid node
Object.entries(NODE_COORDS).forEach(([node, coords]) => {
    L.circleMarker(coords, { radius: 4, color: '#94a3b8', fillOpacity: 0.8 })
        .addTo(map)
        .bindTooltip(NODE_LABELS[node], {
            permanent: true,
            direction: 'top',
            offset: [0, -6],
            className: 'node-tooltip'
        });
});

function badgeIcon(svg, className, size = 34) {
    return L.divIcon({
        html: `<div class="map-badge ${className}">${svg}</div>`,
        className: '',
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
    });
}

// place all hospitals permanently, once, on page load
const hospitalMarkerRefs = {}; // node -> marker, so we can restyle the active one

HOSPITALS.forEach(h => {
    const marker = L.marker(NODE_COORDS[h.node], {
        icon: badgeIcon(HOSPITAL_SVG, 'hospital-badge', 34)
    }).addTo(map).bindPopup(`<b>${h.name}</b>`);
    hospitalMarkerRefs[h.node] = marker;
});

function highlightActiveHospital(node) {
    Object.entries(hospitalMarkerRefs).forEach(([n, marker]) => {
        const isActive = n === node;
        marker.setIcon(badgeIcon(
            HOSPITAL_SVG,
            isActive ? 'hospital-badge active-hospital' : 'hospital-badge',
            isActive ? 42 : 34
        ));
    });
}

let currentRouteLine = null;
let ambulanceMarker = null;

function clearRoute() {
    if (currentRouteLine) map.removeLayer(currentRouteLine);
    if (ambulanceMarker) map.removeLayer(ambulanceMarker);
    currentRouteLine = null;
    ambulanceMarker = null;
}

function drawRoute(routeNodes, color = '#2563eb') {
    const latlngs = routeNodes.map(n => NODE_COORDS[n]);
    currentRouteLine = L.polyline(latlngs, {
        color, weight: 6, opacity: 0.85
    }).addTo(map);
    map.fitBounds(currentRouteLine.getBounds(), { padding: [60, 60] });
}

function placeAmbulance(node) {
    ambulanceMarker = L.marker(NODE_COORDS[node], {
        icon: badgeIcon(AMBULANCE_SVG, 'ambulance-badge', 36)
    }).addTo(map).bindPopup("Ambulance — emergency location").openPopup();
}

function setStatus(text, mode = 'idle') {
    const el = document.getElementById('status');
    el.className = `panel status-panel status-${mode}`;
    el.innerText = text;
}

function showGreenCorridor(roadIds) {
    const el = document.getElementById('greenCorridor');
    el.classList.add('visible');
    el.innerHTML = "🟢 Green Corridor active on: <b>" + roadIds.join(", ") +
        "</b> (NORMAL → PRIORITY → NORMAL)";
}

function renderResult(data, jamLabel) {
    clearRoute();
    const node = document.getElementById('emergencyNode').value;
    placeAmbulance(node);
    highlightActiveHospital(data.new_best_hospital.route.slice(-1)[0]);
    drawRoute(data.new_best_hospital.route, data.reroute_needed ? '#d97706' : '#2563eb');

    const routeStr = data.new_best_hospital.route.map(n => NODE_LABELS[n]).join(' → ');
    const mode = data.reroute_needed ? 'reroute' : 'ok';
    const prefix = data.reroute_needed
        ? `🔁 REROUTED (${jamLabel})`
        : `✅ No reroute needed (${jamLabel})`;

    setStatus(
        `${prefix} → ${data.new_best_hospital.name} | Route: ${routeStr} | ` +
        `Predicted time: ${data.new_best_hospital.predicted_travel_time} min`,
        mode
    );

    showGreenCorridor(data.green_corridor_roads);
}

document.getElementById('createEmergencyBtn').addEventListener('click', async () => {
    const node = document.getElementById('emergencyNode').value;
    const hour = parseInt(document.getElementById('hourInput').value, 10);
    const day = document.getElementById('dayInput').value;

    setStatus("⏳ Predicting travel times and selecting optimal hospital...", 'info');
    clearRoute();

    const res = await fetch('/api/emergency', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node, hour, day })
    });
    const data = await res.json();

    placeAmbulance(node);
    highlightActiveHospital(data.best_hospital.route.slice(-1)[0]);
    drawRoute(data.best_hospital.route, '#2563eb');

    const routeStr = data.best_hospital.route.map(n => NODE_LABELS[n]).join(' → ');
    setStatus(
        `🏥 Optimal hospital: ${data.best_hospital.name} | Route: ${routeStr} | ` +
        `Predicted time: ${data.best_hospital.predicted_travel_time} min`,
        'ok'
    );

    showGreenCorridor(data.green_corridor_roads);

    document.getElementById('simulateJamBtn').disabled = false;
    document.getElementById('simulateTimeBtn').disabled = false;
    document.getElementById('jamCurrentRouteBtn').disabled = false;
});

document.getElementById('simulateJamBtn').addEventListener('click', async () => {
    setStatus("⏳ Simulating traffic jam and re-checking route...", 'info');
    const jamRoad = document.getElementById('jamRoadSelect').value;

    const res = await fetch('/api/traffic/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spike_roads: [jamRoad] })
    });
    const data = await res.json();

    renderResult(data, `jam on ${jamRoad}`);
});

document.getElementById('simulateTimeBtn').addEventListener('click', async () => {
    setStatus("⏳ Simulating time change to 6 PM rush hour...", 'info');

    const res = await fetch('/api/traffic/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spike_roads: [], hour: 18 })
    });
    const data = await res.json();

    renderResult(data, "time change → 6 PM");
});

document.getElementById('jamCurrentRouteBtn').addEventListener('click', async () => {
    setStatus("⏳ Jamming every road on the current route...", 'info');

    const res = await fetch('/api/traffic/jam-current-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
    const data = await res.json();

    renderResult(data, `major jam on ${data.jammed_roads.join(', ')}`);
});

// ---- Theme toggle ----
const themeToggleBtn = document.getElementById('themeToggleBtn');

function applyTheme(isDark) {
    document.body.classList.toggle('dark-theme', isDark);
    themeToggleBtn.innerText = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
}

applyTheme(false);

themeToggleBtn.addEventListener('click', () => {
    const isDark = !document.body.classList.contains('dark-theme');
    applyTheme(isDark);
});