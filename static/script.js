// ✅ script.js：地圖路線繪製視圖優化
let map;
let userLatLng;
let routeLayers = [];
let routeGroup = L.layerGroup();
let markerGroup;
let mapInitialized = false;

function initMap() {
  if (mapInitialized) return;
  mapInitialized = true;

  map = L.map("map").setView([24.147736, 120.673648], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18 }).addTo(map);
  markerGroup = L.layerGroup().addTo(map);

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      userLatLng = [pos.coords.latitude, pos.coords.longitude];
      L.marker(userLatLng).addTo(map).bindPopup("您目前的位置").openPopup();
      map.setView(userLatLng, 15);
      const startInput = document.getElementById("start");
      if (startInput) startInput.value = "我的位置";
    }, () => {
      alert("無法取得您的位置，請手動輸入地址");
    });
  }
}

async function drawRoute(start, end, color, label) {
  console.log("嘗試繪製路線：", label, "from", start, "to", end);
  const res = await fetch("https://api.openrouteservice.org/v2/directions/foot-walking", {
    method: "POST",
    headers: {
      "Authorization": "5b3ce3597851110001cf62485955782916f3457e8356700f40cc7beb",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      coordinates: [[start[1], start[0]], [end[1], end[0]]],
      radiuses: [1000, 1000],
      instructions: true
    })
  });

  // 先檢查 HTTP 狀態
  if (!res.ok) {
    const text = await res.text();
    console.error("ORS HTTP錯誤：", res.status, text);
    throw new Error(`ORS API HTTP錯誤：${res.status}\n${text}`);
  }

  const json = await res.json();
  console.log("OpenRouteService 回應：", json);

  // routes 格式（新版 API）
  if (json.routes && json.routes[0] && json.routes[0].geometry) {
    const coords = decodePolyline(json.routes[0].geometry);
    const polyline = L.polyline(coords, { color, weight: 5 }).bindPopup(label);
    polyline.addTo(routeGroup);
    routeLayers.push(polyline);
    return;
  }

  // features 格式（舊版/GeoJSON）
  if (json.features && json.features[0]) {
    const coords = json.features[0].geometry.coordinates.map(c => [c[1], c[0]]);
    const polyline = L.polyline(coords, { color, weight: 5 }).bindPopup(label);
    polyline.addTo(routeGroup);
    routeLayers.push(polyline);
    return;
  }

  // 其他錯誤
  let msg = "無法取得路線，請確認地點是否正確。";
  if (json.error && json.error.message) {
    msg += `\nAPI 錯誤：${json.error.message}`;
  }
  throw new Error(msg);
}

function clearMap() {
  routeLayers.forEach(l => routeGroup.removeLayer(l));
  routeLayers = [];
  if (markerGroup) markerGroup.clearLayers();
  if (routeGroup) routeGroup.clearLayers();
}

document.addEventListener("DOMContentLoaded", () => {
  // 頁籤切換功能
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.dataset.target;
      tabContents.forEach(tab => {
        tab.style.display = tab.id === targetId ? "block" : "none";
      });
      if (targetId === "tab-route") {
        setTimeout(() => {
          initMap();
          map.invalidateSize(); // 強制刷新地圖尺寸，避免初始化時容器為 hidden
        }, 100);
      }
    });
  });
  const planBtn = document.getElementById("plan-route-btn");
  const citySelect = document.getElementById("citySelect");
  if (planBtn) {
    planBtn.addEventListener("click", async () => {
      const startInput = document.getElementById("start").value.trim();
      const endInput = document.getElementById("end").value.trim();
      if (!startInput || !endInput) {
        alert("請輸入起點與終點！");
        return;
      }
      const city = citySelect ? citySelect.value : "臺中市";
      try {
        const startCoords = await getCoords(startInput);
        const endCoords = await getCoords(endInput);
        const borrowRes = await fetch(`/nearest_station?lat=${startCoords[0]}&lng=${startCoords[1]}&type=borrow&city=${encodeURIComponent(city)}`);
        const returnRes = await fetch(`/nearest_station?lat=${endCoords[0]}&lng=${endCoords[1]}&type=return&city=${encodeURIComponent(city)}`);
        const borrowStation = await borrowRes.json();
        const returnStation = await returnRes.json();

        clearMap();

        await drawRoute(startCoords, [borrowStation.lat, borrowStation.lng], "blue", "步行至借車站（" + borrowStation.station_name + "）");
        await drawRoute([borrowStation.lat, borrowStation.lng], [returnStation.lat, returnStation.lng], "green", "騎乘 YouBike（" + borrowStation.station_name + " ➜ " + returnStation.station_name + "）");
        await drawRoute([returnStation.lat, returnStation.lng], endCoords, "orange", "步行至目的地（" + returnStation.station_name + "）");

        const borrowMarker = L.marker([borrowStation.lat, borrowStation.lng]).bindPopup("🚲 借車站：「" + borrowStation.station_name + "」");
        const returnMarker = L.marker([returnStation.lat, returnStation.lng]).bindPopup("📍 還車站：「" + returnStation.station_name + "」");
        markerGroup.addLayer(borrowMarker);
        markerGroup.addLayer(returnMarker);

        // 自動縮放到全路線
        const bounds = L.latLngBounds([startCoords, endCoords, [borrowStation.lat, borrowStation.lng], [returnStation.lat, returnStation.lng]]);
        routeGroup.addTo(map);
const allItems = [...routeLayers, borrowMarker, returnMarker];
const group = L.featureGroup(allItems);
map.fitBounds(group.getBounds().pad(0.2));
setTimeout(() => {
  routeLayers[0]?.openPopup?.();
}, 300);
map.invalidateSize();
      } catch (err) {
        console.error(err);
        alert("路線規劃失敗：" + err.message);
      }
    });
  }

  document.querySelectorAll(".district-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      // 這裡可以自動送出表單
      document.getElementById("searchForm").submit();
    });
  });
});

async function getCoords(input) {
  if (input === "我的位置") {
    if (!userLatLng) throw new Error("尚未取得您的目前位置");
    return userLatLng;
  } else {
    const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(input)}&format=json`);
    const data = await res.json();
    if (data.length === 0) throw new Error("找不到地址：" + input);
    return [parseFloat(data[0].lat), parseFloat(data[0].lon)];
  }
}

function decodePolyline(encoded) {
  let points = [];
  let index = 0, len = encoded.length;
  let lat = 0, lng = 0;

  while (index < len) {
    let b, shift = 0, result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    let dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lat += dlat;

    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    let dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lng += dlng;

    points.push([lat / 1e5, lng / 1e5]);
  }
  return points;
}
