function initMap(lat, lng, borrow, ret) {
  const map = L.map('map').setView([lat, lng], 14);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const userIcon = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/149/149071.png',
    iconSize: [30, 30]
  });

  L.marker([lat, lng], { icon: userIcon }).addTo(map).bindPopup("你的位置").openPopup();

  if (borrow) {
    L.marker([borrow.latitude, borrow.longitude])
      .addTo(map)
      .bindPopup(`🚴 借車站：${borrow.station_name}`);
  }

  if (ret) {
    L.marker([ret.latitude, ret.longitude])
      .addTo(map)
      .bindPopup(`📍 還車站：${ret.station_name}`);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      document.getElementById("lat").value = pos.coords.latitude;
      document.getElementById("lng").value = pos.coords.longitude;
    });
  }

  const lat = parseFloat(document.getElementById("lat").value);
  const lng = parseFloat(document.getElementById("lng").value);

  const borrow = window.borrowData;
  const ret = window.retData;

  if (!isNaN(lat) && !isNaN(lng)) {
    initMap(lat, lng, borrow, ret);
  }
});
