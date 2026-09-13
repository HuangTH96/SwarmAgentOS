<template>
  <div>
    <!-- 自定义图层切换控件 -->
    <div class="custom-maptype">
      <div class="base-type">
        <label :class="{ active: baseType === 'normal' }" @click="setBaseType('normal')">标准图层</label>
        <label :class="{ active: baseType === 'satellite' }" @click="setBaseType('satellite')">卫星图</label>
      </div>
      <div class="overlay-type">
        <label>
          <input type="checkbox" v-model="showRoadNet" @change="toggleRoadNet" />
          路网
        </label>
      </div>
    </div>
    <div id="container" class="tech-map"></div>

    <!-- 清除按钮组 -->
    <div class="clear-buttons">
      <q-btn
        @click="clearDronePath"
        label="清除轨迹"
        icon="timeline"
        size="sm"
        flat
        dense
        no-caps
        class="clear-btn"
      />
      <q-btn
        @click="clearAllDrones"
        label="清除所有"
        icon="clear_all"
        size="sm"
        flat
        dense
        no-caps
        class="clear-btn"
      />
    </div>

    <!-- 【修改】路径规划控制按钮组 -->
    <div class="path-planning-buttons">

      <!-- 初始状态 -->
      <q-btn
        v-if="planningPhase === 'idle'"
        @click="startPathPlanning"
        label="开始规划"
        icon="edit_location_alt"
        color="primary"
        size="sm"
        dense
        no-caps
        class="path-btn"
      />
      <!-- 规划中状态 -->
      <template v-if="planningPhase === 'planning'">
        <q-btn
          @click="finishPathPlanning"
          label="完成规划"
          icon="check_circle"
          color="positive"
          size="sm"
          dense
          no-caps
          class="path-btn"
        />
        <q-btn
          @click="cancelPathPlanning"
          label="取消规划"
          icon="cancel"
          color="negative"
          size="sm"
          flat
          dense
          no-caps
          class="path-btn"
        />
      </template>
      <!-- 【新增】预览/发送状态 -->
      <template v-if="planningPhase === 'reviewing'">
         <q-btn
          @click="sendPath"
          label="发送航线"
          icon="send"
          color="primary"
          size="sm"
          dense
          no-caps
          class="path-btn"
        />
        <q-btn
          @click="clearPreviousPath"
          label="清除规划"
          icon="delete_sweep"
          color="grey-7"
          size="sm"
          flat
          dense
          no-caps
          class="path-btn"
        />
        <q-btn
          @click="cancelPathPlanning"
          label="重新规划"
          icon="edit"
          color="orange"
          size="sm"
          flat
          dense
          no-caps
          class="path-btn"
        />
      </template>
    </div>

    <!-- 航点参数设置对话框 (保持不变) -->
    <q-dialog v-model="showWaypointDialog" persistent>
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">设置航点参数</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input
            dense
            v-model.number="waypointHeight"
            type="number"
            label="飞行高度 (米)"
            autofocus
            @keyup.enter="handleConfirmWaypoint"
          >
            <template v-slot:append>
              <q-icon name="height" />
            </template>
          </q-input>
          <q-input
            dense
            v-model.number="waypointHeading"
            type="number"
            label="期望航向 (度)"
            class="q-mt-md"
            @keyup.enter="handleConfirmWaypoint"
          >
            <template v-slot:append>
              <q-icon name="explore" />
            </template>
          </q-input>
        </q-card-section>
        <q-card-actions align="right" class="text-primary">
          <q-btn flat label="取消" v-close-popup />
          <q-btn flat label="确定" @click="handleConfirmWaypoint" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";
import { useDroneStore } from "stores/drone";

let map = null;
let satelliteLayer = null;
let roadNetLayer = null;

const baseType = ref("normal");
const showRoadNet = ref(false);

const droneStore = useDroneStore();
let drones = {}; // 存储所有无人机的标记和轨迹

const { lastCalculatedPosition, originPosition } = droneStore;
let customMarker = null; // 目标点标记
let originMarker = null; // 原点标记

const SMOOTHING_FACTOR = 0.3;
const lngOffset = 0.0052;
const latOffset = -0.00208;

function toDisplayCoords(lat, lng) {
    if (window.AMap && window.AMap.LngLat) {
        return new window.AMap.LngLat(lng + lngOffset, lat + latOffset);
    }
    console.error("AMap.LngLat is not available.");
    return null;
}

function toRealCoords(displayLngLat) {
    return {
        lat: displayLngLat.getLat() - latOffset,
        lng: displayLngLat.getLng() - lngOffset
    };
}

// --- 路径规划状态管理 ---
// 【新增】用于存储上一次发送的路径元素，以便清除
let sentPathVisuals = { markers: [], polyline: null };

// 当前正在规划的路径元素
let pathMarkers = [];
let pathPolyline = null;
const clickPlacementState = ref('idle'); // 'idle' or 'defining_heading'
let draftWaypointVisuals = null;
// 【新增】更精细的规划阶段控制
const planningPhase = ref('idle'); // 'idle', 'planning', 'reviewing'

function makeWaypointIconSvg(color = "#4a90e2", opacity = 1) {
  return `
  <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
    <g opacity="${opacity}">
      <path d="M15 3 L25 27 L15 22 L5 27 Z" fill="${color}" stroke="#FFFFFF" stroke-width="1.5" />
    </g>
  </svg>`;
}
function calculateAngle(startLngLat, endLngLat) {
    if (!map) return 0;
    const startPixel = map.lngLatToContainer(startLngLat);
    const endPixel = map.lngLatToContainer(endLngLat);
    const dx = endPixel.x - startPixel.x;
    const dy = endPixel.y - startPixel.y;
    const radians = Math.atan2(-dy, dx);
    let degrees = radians * (180 / Math.PI);
    degrees = (450 - degrees) % 360;
    return degrees;
}
function clearDraftVisuals() {
    if (draftWaypointVisuals) {
        map.remove([draftWaypointVisuals.marker, draftWaypointVisuals.polyline]);
        draftWaypointVisuals = null;
    }
}

function startPathPlanning() {
  if (customMarker) {
    map.remove(customMarker);
    customMarker = null;
  }

  // 【核心修改】在开始新规划之前，先清空上一次规划的数据。
  // 这会触发 watch 监听器，从而自动清除地图上残留的、已发送的路径元素。
  droneStore.cancelPathPlanning(); // 假设此函数会将 plannedPath 置为空数组 []

  // 然后再正常开始新的规划流程
  droneStore.startPathPlanning();
  planningPhase.value = 'planning';
  clickPlacementState.value = 'idle';
  map.getContainer().style.cursor = 'crosshair';
}

// 【修改】完成规划，现在只进入预览模式
function finishPathPlanning() {
  if (clickPlacementState.value === 'defining_heading') {
    finalizeCurrentWaypoint();
  }
  planningPhase.value = 'reviewing';
  map.getContainer().style.cursor = 'grab';
}

// 【修改】发送航线命令
async function sendPath() {
  // 调用修改后的 finalizePath，它会返回发送的路径数据或 null
  const finalPathData = await droneStore.finalizePath();

  // 只有在发送成功时才执行后续操作
  if (finalPathData) {
    console.log("发送最终路径点数据:", JSON.stringify(finalPathData, null, 2));

    // 提高透明度，使其不那么显眼
    pathMarkers.forEach(group => {
      group.marker.setOpacity(0.6);
      group.text.setOpacity(0.6);
      // 【优化】发送后禁止再编辑
      group.marker.off('click');
      group.text.off('click');
      group.marker.setClickable(false);
    });
    if (pathPolyline) {
      pathPolyline.setOptions({ strokeOpacity: 0.4 });
    }

    // 将当前路径元素转移到“已发送”存储中，以便“清除”按钮可以找到它们
    sentPathVisuals.markers = pathMarkers;
    sentPathVisuals.polyline = pathPolyline;

    // 清空当前规划的元素引用，为下一次规划做准备
    pathMarkers = [];
    pathPolyline = null;

    // 重置UI状态到初始界面
    planningPhase.value = 'idle';

    // 【重要】不再需要调用 resetAfterSend() 或任何清空 store 的操作
    // store 中的 plannedPath 数据被有意保留
  }
}

// 【修改】清除上一次发送的路径
function clearPreviousPath() {
  // 1. 从地图上移除视觉元素
  if (sentPathVisuals.polyline) {
    map.remove(sentPathVisuals.polyline);
  }
  sentPathVisuals.markers.forEach(group => map.remove([group.marker, group.text]));
  sentPathVisuals.markers = [];
  sentPathVisuals.polyline = null;

  // 2. 调用 store action 清除路径数据，这将触发 watch 并清理任何残留的显示逻辑
  droneStore.clearPlannedPath();

  // 如果是在 review 阶段点击清除，则需要同时重置UI状态
  if (planningPhase.value === 'reviewing') {
      planningPhase.value = 'idle';
  }
}

function cancelPathPlanning() {
  clearDraftVisuals();
  droneStore.cancelPathPlanning();
  planningPhase.value = 'idle';
  clickPlacementState.value = 'idle';
  map.getContainer().style.cursor = 'grab';
}
function finalizeCurrentWaypoint() {
    if (!draftWaypointVisuals) return;
    const realCoords = toRealCoords(draftWaypointVisuals.position);
    const newWaypoint = {
        lat: realCoords.lat,
        lng: realCoords.lng,
        // 【修改】默认高度为 10
        height: 10,
        heading: draftWaypointVisuals.marker.getAngle() || 0,
    };
    droneStore.addWaypoint(newWaypoint);
    clearDraftVisuals();
    clickPlacementState.value = 'idle';
}

watch(
  () => droneStore.plannedPath,
  (newPath) => {
    if (!map) return;
    // 清理旧的 marker 和 polyline
    pathMarkers.forEach(group => map.remove([group.marker, group.text]));
    if (pathPolyline) {
      map.remove(pathPolyline);
    }
    pathMarkers = [];
    pathPolyline = null;
    if (newPath.length === 0) return;

    const displayPathCoords = newPath.map(waypoint => toDisplayCoords(waypoint.lat, waypoint.lng));

    newPath.forEach((waypoint, index) => {
        const displayPos = displayPathCoords[index];
        const marker = new window.AMap.Marker({
            position: displayPos,
            icon: new window.AMap.Icon({
                size: new window.AMap.Size(30, 30),
                image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(makeWaypointIconSvg()),
                imageSize: new window.AMap.Size(30, 30),
            }),
            offset: new window.AMap.Pixel(-15, -15),
            angle: waypoint.heading,
            title: `航点 ${index + 1}\n点击修改航向`,
            extData: { index },
            // 【新增】允许 marker 被点击
            clickable: true,
        });

        // 【新增】为 marker 添加点击事件以修改航向
        marker.on('click', (e) => {
            // 仅在规划或预览阶段可编辑
            if (planningPhase.value === 'planning' || planningPhase.value === 'reviewing') {
                const currentIndex = marker.getExtData().index;
                const currentWaypoint = droneStore.plannedPath[currentIndex];
                const newHeading = prompt(`为航点 ${currentIndex + 1} 输入新的航向 (0-360):`, currentWaypoint.heading);
                if (newHeading !== null && !isNaN(Number(newHeading))) {
                    const headingValue = (Number(newHeading) % 360 + 360) % 360; // 确保在 0-360 范围内
                    droneStore.updateWaypoint(currentIndex, { heading: headingValue });
                }
            }
            // 阻止事件冒泡，防止触发地图的点击事件
            e.stopPropagation();
        });

        const heightText = new window.AMap.Text({
            text: `高度: ${waypoint.height}m`,
            position: displayPos,
            offset: new window.AMap.Pixel(0, -40),
            style: {
                'background-color': 'rgba(255, 255, 255, 0.8)',
                'border': '1px solid #ccc',
                'padding': '2px 5px',
                'border-radius': '3px',
                'font-size': '12px',
            },
            className: 'editable-height-text',
            extData: { index }
        });

        heightText.on('click', (e) => {
             if (planningPhase.value === 'planning' || planningPhase.value === 'reviewing') {
                const currentIndex = heightText.getExtData().index;
                const currentWaypoint = droneStore.plannedPath[currentIndex];
                const newHeight = prompt("请输入新的飞行高度 (米):", currentWaypoint.height);
                if (newHeight !== null && !isNaN(Number(newHeight))) {
                    droneStore.updateWaypoint(currentIndex, { height: Number(newHeight) });
                }
             }
             e.stopPropagation();
        });

        pathMarkers.push({ marker, text: heightText });
    });

    map.add(pathMarkers.flatMap(group => [group.marker, group.text]));

    if (displayPathCoords.length > 1) {
      pathPolyline = new window.AMap.Polyline({
          path: displayPathCoords,
          strokeColor: "#4a90e2",
          strokeWeight: 4,
          strokeOpacity: 0.8,
      });
      map.add(pathPolyline);
    }
  },
  { deep: true }
);

// ... (无人机显示、颜色管理、清除函数等都保持不变)
const COLOR_PALETTE = ['#F44336','#FFEB3B','#2196F3','#4CAF50','#FF9800','#9C27B0',];
const clientIdToColor = {};
function hashToIndex(str) {let hash = 0;for (let i = 0; i < str.length; i++) {hash = ((hash << 5) - hash) + str.charCodeAt(i);hash |= 0;}return Math.abs(hash) % COLOR_PALETTE.length;}
function getColorForClient(clientId) {if (!clientIdToColor[clientId]) {clientIdToColor[clientId] = COLOR_PALETTE[hashToIndex(clientId)];}return clientIdToColor[clientId];}
function lightenColor(hex, ratio = 0.7) {const clean = hex.replace('#', '');const bigint = parseInt(clean.length === 3? clean.split('').map(c => c + c).join(''): clean, 16);const r = (bigint >> 16) & 255;const g = (bigint >> 8) & 255;const b = bigint & 255;const mix = (c) => Math.round(c + (255 - c) * ratio);const rr = mix(r).toString(16).padStart(2, '0');const gg = mix(g).toString(16).padStart(2, '0');const bb = mix(b).toString(16).padStart(2, '0');return `#${rr}${gg}${bb}`;}
function makeDroneIconSvg(color) {return `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><defs><filter id="drop-shadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000000" flood-opacity="0.6"/></filter></defs><g filter="url(#drop-shadow)"><path d="M16,4 L28,28 L16,24 L4,28 Z" fill="${color}" stroke="#FFFFFF" stroke-width="1.5"/></g></svg>`;}
function clearDronePath() {if (!map) return;Object.values(drones).forEach(drone => {if (drone.polyline) {drone.polyline.setPath([]);}});console.log("所有轨迹线已清除");}
function clearAllDrones() {if (!map) return;Object.keys(drones).forEach(clientId => {resetDroneDisplay(clientId);});console.log("所有无人机显示已清除");}
function clearSpecificDronePath(clientId) {if (!map || !drones[clientId]) return;const drone = drones[clientId];if (drone.polyline) {drone.polyline.setPath([]);console.log(`无人机 ${clientId} 的轨迹已清除`);}}
function resetDroneDisplay(clientId) {if (!map || !drones[clientId]) return;const drone = drones[clientId];if (drone.marker) {map.remove(drone.marker);}if (drone.polyline) {map.remove(drone.polyline);}delete drones[clientId];console.log(`无人机 ${clientId} 的显示已重置`);}
function updateDroneOnMap(status, clientId, shouldRecenter = false) {if (!map || !status || !status.isConnected) {if (drones[clientId]) {resetDroneDisplay(clientId);}return;}const realLongitude = status.longitude || status.longtitude || 0;const realLatitude = status.latitude || 0;if (!realLongitude || !realLatitude) {console.warn(`无人机 ${clientId} 无效的坐标数据:`, { realLongitude, realLatitude });return;}const displayPosition = toDisplayCoords(realLatitude, realLongitude);if (!displayPosition) return;const heading = status.heading || status.head || 0;if (drones[clientId]) {const drone = drones[clientId];const lastSmoothedPosition = drone.lastSmoothedPosition;const smoothedLat = lastSmoothedPosition.lat * (1 - SMOOTHING_FACTOR) + displayPosition.lat * SMOOTHING_FACTOR;const smoothedLng = lastSmoothedPosition.lng * (1 - SMOOTHING_FACTOR) + displayPosition.lng * SMOOTHING_FACTOR;const smoothedPosition = new window.AMap.LngLat(smoothedLng, smoothedLat);drone.marker.setPosition(smoothedPosition);drone.marker.setAngle(heading);const path = drone.polyline.getPath();path.push(smoothedPosition);drone.polyline.setPath(path);drone.lastSmoothedPosition = smoothedPosition;if (shouldRecenter) {map.setZoomAndCenter(17, smoothedPosition, false, 500);}} else {console.log(`首次检测到无人机 ${clientId}，正在创建地图对象...`);const baseColor = getColorForClient(clientId);const color = lightenColor(baseColor, 0.65);const marker = new window.AMap.Marker({position: displayPosition,icon: new window.AMap.Icon({size: new window.AMap.Size(32, 32),image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(makeDroneIconSvg(color)),imageSize: new window.AMap.Size(32, 32),}),offset: new window.AMap.Pixel(-16, -16),angle: heading,clickable: false});const polyline = new window.AMap.Polyline({path: [displayPosition],strokeColor: color,strokeWeight: 5,strokeOpacity: 0.65,lineJoin: 'round',clickable: false});map.add([marker, polyline]);drones[clientId] = {marker: marker,polyline: polyline,lastSmoothedPosition: displayPosition,color: color};
// 【修改/确认】当第一架无人机出现时，自动移动地图中心
if (Object.keys(drones).length === 1) {
    console.log("地图自动聚焦到第一架无人机位置。");
    map.setZoomAndCenter(17, displayPosition);
}}}
watch(() => droneStore.rawTelemetry,(telemetryMap) => {if (!telemetryMap) return;const mapped = {};Object.entries(telemetryMap).forEach(([clientId, t]) => {if (!t) return;mapped[clientId] = {isConnected: true,latitude: t.latitude || 0,longitude: t.longtitude || 0,longtitude: t.longtitude || 0,head: t.head || 0,heading: t.head || 0,height: t.height || 0,speed: t.speed || 0};});updateMultipleDrones(mapped);const activeIds = new Set(Object.keys(mapped));Object.keys(drones).forEach((id) => {if (!activeIds.has(id)) {resetDroneDisplay(id);}});},{ deep: true });
function updateMultipleDrones(dronesData) {if (!map || !dronesData) return;Object.entries(dronesData).forEach(([clientId, droneData]) => {updateDroneOnMap(droneData, clientId, false);});}
defineExpose({updateMultipleDrones,clearDronePath,clearAllDrones,clearSpecificDronePath});
function setBaseType(type) {if (!map) return;baseType.value = type;if (type === "normal") {map.setLayers([new window.AMap.TileLayer()]);if (showRoadNet.value && roadNetLayer) map.add(roadNetLayer);} else if (type === "satellite") {map.setLayers([satelliteLayer]);if (showRoadNet.value && roadNetLayer) map.add(roadNetLayer);}}
function toggleRoadNet() {if (!map) return;if (showRoadNet.value) {map.add(roadNetLayer);} else {map.remove(roadNetLayer);}}
// ... (对话框相关代码保持不变, 只修改默认值)
const showWaypointDialog = ref(false);
// 【修改】默认高度为 10
const waypointHeight = ref(10);
const waypointHeading = ref(0);
const pendingWaypointCoords = ref(null);
function handleConfirmWaypoint() {if (!pendingWaypointCoords.value) return;const newWaypoint = {lat: pendingWaypointCoords.value.lat,lng: pendingWaypointCoords.value.lng,height: Number(waypointHeight.value),heading: Number(waypointHeading.value)};droneStore.addWaypoint(newWaypoint);showWaypointDialog.value = false;pendingWaypointCoords.value = null;}

onMounted(() => {
  window._AMapSecurityConfig = {
    securityJsCode: "0bb2d9d601a8aa958498a59a62125596"
  };
  AMapLoader.load({
    key: "ecc03cb91886825cd841398653f02848",
    version: "2.0",
    plugins: ["AMap.Scale", "AMap.Terrain", "AMap.Polyline", "AMap.TileLayer", "AMap.Text"]
  })
    .then((AMap) => {
      map = new AMap.Map("container", {
        zoom: 15,
        viewMode: '3D',
        pitch: 45,
      });

      satelliteLayer = new AMap.TileLayer.Satellite();
      roadNetLayer = new AMap.TileLayer.RoadNet();

      const handleMapMouseMove = (e) => {
          if (planningPhase.value === 'planning' && clickPlacementState.value === 'defining_heading' && draftWaypointVisuals) {
            draftWaypointVisuals.polyline.setPath([
                draftWaypointVisuals.position,
                e.lnglat
            ]);
            const angle = calculateAngle(draftWaypointVisuals.position, e.lnglat);
            draftWaypointVisuals.marker.setAngle(angle);
          }
      };
      map.on('mousemove', handleMapMouseMove);

      map.on("click", (e) => {
        // 如果当前是路径规划模式
        if (droneStore.isPathPlanning && planningPhase.value === 'planning') {
            if (clickPlacementState.value === 'idle') {
                const tempMarker = new AMap.Marker({
                    position: e.lnglat,
                    icon: new AMap.Icon({
                        size: new AMap.Size(30, 30),
                        image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(makeWaypointIconSvg('#f44336')),
                        imageSize: new AMap.Size(30, 30),
                    }),
                    offset: new AMap.Pixel(-15, -15),
                });
                const tempPolyline = new AMap.Polyline({
                    path: [e.lnglat, e.lnglat],
                    strokeColor: "#f44336",
                    strokeWeight: 2,
                    strokeStyle: 'dashed',
                });
                map.add([tempMarker, tempPolyline]);
                draftWaypointVisuals = {
                    marker: tempMarker,
                    polyline: tempPolyline,
                    position: e.lnglat
                };
                clickPlacementState.value = 'defining_heading';
            } else if (clickPlacementState.value === 'defining_heading') {
                finalizeCurrentWaypoint();
            }
        } else if (!droneStore.isPathPlanning) {
            // 设置目标点模式
            const displayLngLat = e.lnglat;
            const realCoords = toRealCoords(displayLngLat);

            lastCalculatedPosition.lng = realCoords.lng;
            lastCalculatedPosition.lat = realCoords.lat;

            const relativePos = calculateDistanceInMeters(
              originPosition.lat,
              originPosition.lng,
              realCoords.lat,
              realCoords.lng
            );

            lastCalculatedPosition.x = relativePos.x;
            lastCalculatedPosition.y = relativePos.y;

            if (customMarker) {
              map.remove(customMarker);
            }
            customMarker = new window.AMap.Marker({
              position: displayLngLat,
              icon: new window.AMap.Icon({
                  size: new window.AMap.Size(22, 22),
                  image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent('<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="#f44336" d="M512 0C229.2 0 0 229.2 0 512s229.2 512 512 512 512-229.2 512-512S794.8 0 512 0zm0 928C282.3 928 96 741.7 96 512S282.3 96 512 96s416 186.3 416 416-186.3 416-416 416z"/><path fill="#f44336" d="M512 384a128 128 0 1 0 0 256 128 128 0 0 0 0-256z"/></svg>'),
                  imageSize: new window.AMap.Size(22, 22)
              }),
              offset: new window.AMap.Pixel(-11, -11),
              title: "目标点",
              clickable: false
            });
            map.add(customMarker);

            console.log('设置目标点:', {
                relative: { x: relativePos.x.toFixed(2), y: relativePos.y.toFixed(2) },
                absolute_real: { lat: realCoords.lat, lng: realCoords.lng }
            });
        }
      });

      map.on('rightclick', (e) => {
        if (droneStore.isPathPlanning) {
            alert("请先完成或取消路径规划，再设置坐标原点。");
            return;
        }

        const displayLngLat = e.lnglat;
        const realCoords = toRealCoords(displayLngLat);

        originPosition.lat = realCoords.lat;
        originPosition.lng = realCoords.lng;

        if (originMarker) {
            map.remove(originMarker);
        }

        originMarker = new window.AMap.Marker({
            position: displayLngLat,
            icon: new window.AMap.Icon({
                size: new window.AMap.Size(28, 28),
                image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent('<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="#4CAF50" d="M512 960c-247.4 0-448-200.6-448-448S264.6 64 512 64s448 200.6 448 448-200.6 896-448 896zm0-832c-212.1 0-384 171.9-384 384s171.9 384 384 384 384-171.9 384-384-171.9-384-384-384z"/><path fill="#4CAF50" d="M544 704h-64V320h64v384z"/><path fill="#4CAF50" d="M320 544v-64h384v64H320z"/></svg>'),
                imageSize: new window.AMap.Size(28, 28)
            }),
            offset: new window.AMap.Pixel(-14, -14),
            title: "坐标原点",
            clickable: false
        });
        map.add(originMarker);

        console.log('设置坐标原点 (真实GPS):', { lat: realCoords.lat, lng: realCoords.lng });
        alert(`坐标原点已设置！\n纬度: ${realCoords.lat.toFixed(6)}\n经度: ${realCoords.lng.toFixed(6)}`);
      });

    })
    .catch((e) => {
      console.log(e);
    });
});


onUnmounted(() => {
  map?.destroy();
});

// 将经纬度差转换为米
function calculateDistanceInMeters(lat1, lng1, lat2, lng2) {
  if (!lat1 || !lng1) {
    return { x: 0, y: 0 };
  }
  const degToRad = Math.PI / 180.0;
  const EARTH_RADIUS = 6378137.0;

  const dLat = (lat2 - lat1) * degToRad;
  const dLng = (lng2 - lng1) * degToRad;

  const meanLat = (lat1 + lat2) / 2.0 * degToRad;

  const x = EARTH_RADIUS * dLng * Math.cos(meanLat);
  const y = EARTH_RADIUS * dLat;

  return { x, y };
}
</script>

<style scoped>
/* 保持原有样式不变 */
.custom-maptype {
  position: absolute;
  left: 32px;
  bottom: 48px;
  z-index: 20;
  background: rgba(9, 19, 25, .94);
  border: 1px solid rgba(116,169,190,.34);
  border-left: 2px solid #33d6e8;
  border-radius: 2px;
  box-shadow: 0 8px 24px rgba(0,0,0,.42);
  padding: 9px 12px;
  font-family: inherit;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 110px;
  font-size: 10px;
  align-items: flex-start;
}
.custom-maptype .base-type,
.custom-maptype .overlay-type {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.custom-maptype label {
  margin: 0;
  cursor: pointer;
  font-weight: bold;
  color: #c5dfe2;
  font-size: 10px;
  padding: 4px 7px;
  border-radius: 2px;
  transition: background 0.2s, color 0.2s;
  width: 100%;
  box-sizing: border-box;
}
.custom-maptype .base-type label.active {
  background: rgba(51,214,232,.18);
  color: #33d6e8;
}
.custom-maptype input[type="checkbox"] {
  accent-color: #33d6e8;
  margin-right: 4px;
}
#container {
  width: 100%;
  height: 92.5vh;
  border: 1px solid rgba(116,169,190,.28);
  border-radius: 2px;
  box-shadow: 0 8px 32px rgba(0,0,0,.34), inset 0 1px 0 rgba(170,230,235,.08);
  position: relative;
  overflow: hidden;
}
.tech-map {
  position: relative;
}

.clear-buttons {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.clear-btn {
  background: rgba(9, 19, 25, .94) !important;
  border: 1px solid rgba(116,169,190,.34) !important;
  color: #c5dfe2 !important;
}

.clear-btn:hover {
  background: rgba(51,214,232,.12) !important;
  border-color: #33d6e8 !important;
  color: #33d6e8 !important;
}

/* 【新增】路径规划按钮组样式 */
.path-planning-buttons {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 1000;
  display: flex;
  gap: 8px;
  background-color: rgba(9, 19, 25, .94);
  padding: 8px;
  border-radius: 2px;
  border: 1px solid rgba(116,169,190,.28);
  box-shadow: 0 8px 24px rgba(0,0,0,.4);
}

.path-btn {
  /* 可以根据需要添加通用样式 */
}


.editable-height-text:hover {
  cursor: pointer;
  text-decoration: underline;
  font-weight: bold;
}
</style>
