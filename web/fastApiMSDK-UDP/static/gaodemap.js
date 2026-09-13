window.DroneMap = (function() {
    // --- 私有变量 ---

    let map = null;
    let drones = {};
    const lngOffset = 0.0052;
    const latOffset = -0.00205
    ;
    let takeoffPoint = null;  // 存储起飞点的【真实GPS】位置
    let targetMarker = null;  // 存储目标点标记
    let infoWindow = null;    // 存储信息窗口
    let current_pos = null;

    // 地球半径（米）
    const EARTH_RADIUS = 6378137.0;

    // 平滑因子，值越小，轨迹越平滑，但会有轻微延迟。推荐范围 0.2 - 0.5
    const SMOOTHING_FACTOR = 0.3;


    /**
     * 将真实的GPS坐标转换为地图上显示的坐标
     * @param {number} lat 真实纬度
     * @param {number} lng 真实经度
     * @returns {AMap.LngLat} 用于高德地图API的LngLat对象
     */
    function toDisplayCoords(lat, lng) {
        return new AMap.LngLat(lng + lngOffset, lat + latOffset);
    }

    /**
     * 将地图上点击的显示坐标转换为真实的GPS坐标
     * @param {AMap.LngLat} displayLngLat 从高德地图获取的LngLat对象
     * @returns {{lat: number, lng: number}} 包含真实经纬度的对象
     */
    function toRealCoords(displayLngLat) {
        return {
            lat: displayLngLat.getLat() - latOffset,
            lng: displayLngLat.getLng() - lngOffset
        };
    }

    // 将经纬度差转换为米
    function calculateDistanceInMeters(lat1, lng1, lat2, lng2) {
        const dLat = (lat2 - lat1) * Math.PI / 180.0;
        const dLng = (lng2 - lng1) * Math.PI / 180.0;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180.0) * Math.cos(lat2 * Math.PI / 180.0) *
                Math.sin(dLng/2) * Math.sin(dLng/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        const distance = EARTH_RADIUS * c;
        const y = EARTH_RADIUS * dLat;
        const x = EARTH_RADIUS * dLng * Math.cos(lat1 * Math.PI / 180.0);
        return { x, y };
    }

    const droneIconSvg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
            <path d="M14,2 L26,26 L14,22 L2,26 L14,2" fill="#F57C00" stroke="#FFF" stroke-width="1"/>
        </svg>
    `;

    function clearTargetMarker() {
        if (targetMarker) {
            map.remove(targetMarker);
            targetMarker = null;
        }
        if (infoWindow) {
            infoWindow.close();
            infoWindow = null;
        }
    }

    /**
     * 初始化地图
     */
    function initMap() {
        const mapContainer = document.getElementById('map-area');
        if (!mapContainer) {
            console.error("找不到地图容器元素。");
            return;
        }

        map = new AMap.Map('map-area', {
            zoom: 18,
            viewMode: '3D',
            showBuildingBlock: true,
            showLabel: true,
            expandZoomRange: true,
            zooms: [3, 20],
            defaultCursor: 'pointer',
            features: ['bg', 'road', 'building', 'point'],
        });

        map.addControl(new AMap.Scale());
        map.addControl(new AMap.ToolBar({ position: 'RB' }));

        // 添加地图点击事件
        map.on('click', function(e) {
            if (!takeoffPoint) {
                alert('请先点击起飞按钮记录起飞点位置！');
                return;
            }

            // 1. 获取地图上点击的【显示坐标】
            const displayLngLat = e.lnglat;

            // 2. 将显示坐标转换为【真实GPS坐标】
            const realCoords = toRealCoords(displayLngLat);

            // 3. 使用【真实GPS坐标】进行距离计算
            // takeoffPoint 已经存储的是真实坐标，所以这里计算是准确的
            const relativePos = calculateDistanceInMeters(
                current_pos.latitude,
                current_pos.longitude,
                realCoords.lat, // 使用转换后的真实纬度
                realCoords.lng  // 使用转换后的真实经度
            );

            // 清除之前的标记和信息窗口
            clearTargetMarker();

            // 4. 创建新的目标点标记，标记位置使用【显示坐标】
            targetMarker = new AMap.Marker({
                position: displayLngLat, // 标记必须放在地图上点击的位置
                icon: new AMap.Icon({
                    size: new AMap.Size(20, 20),
                    image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
                        '<svg width="20" height="20" xmlns="http://www.w3.org/2000/svg">' +
                        '<circle cx="10" cy="10" r="8" fill="#FF4081" stroke="#FFF" stroke-width="2"/>' +
                        '<circle cx="10" cy="10" r="2" fill="#FFF"/>' +
                        '</svg>'
                    ),
                    imageSize: new AMap.Size(20, 20)
                }),
                offset: new AMap.Pixel(-10, -10),
                title: '目标点',
                animation: 'AMAP_ANIMATION_DROP',
                clickable: false
            });
            map.add(targetMarker);

            // 创建新的信息窗口 (位置也使用显示坐标)
            infoWindow = new AMap.InfoWindow({
                content: `<div style="padding: 10px;">
                    <h4 style="margin: 0 0 5px 0; color: #333;">目标点相对坐标</h4>
                    <p style="margin: 5px 0; color: #666;">
                        <span style="color: #FF4081;">X:</span> ${relativePos.x.toFixed(2)} 米<br>
                        <span style="color: #FF4081;">Y:</span> ${relativePos.y.toFixed(2)} 米
                    </p>
                </div>`,
                offset: new AMap.Pixel(0, -20),
                closeWhenClickMap: false
            });
            infoWindow.open(map, targetMarker.getPosition());

            //  将【真实GPS坐标】和计算出的相对坐标保存到全局变量，用于发送给无人机
            window.lastCalculatedPosition = {
                x: relativePos.x,
                y: relativePos.y,
                lat: realCoords.lat, // 存储真实纬度
                lng: realCoords.lng  // 存储真实经度
            };

            // 在控制台输出坐标信息
            console.log('目标点坐标:', {
                relative: {
                    x: relativePos.x.toFixed(2),
                    y: relativePos.y.toFixed(2)
                },
                absolute_real: { // 增加标识，表明这是真实坐标
                    lat: realCoords.lat,
                    lng: realCoords.lng
                }
            });
        });

        console.log("地图初始化完成，可以点击地图选择目标点。");
    }

    /**
     * @param {number} lat 真实的GPS纬度
     * @param {number} lng 真实的GPS经度
     */
    function setTakeoffPoint(lat, lng) {
        // 1. 存储【真实GPS坐标】
        takeoffPoint = {
            latitude: lat,
            longitude: lng
        };
        console.log('记录起飞点真实GPS位置:', takeoffPoint);

        // 清除现有的目标点标记
        clearTargetMarker();

        // 【修改】
        // 2. 将真实坐标转换为【显示坐标】以便在地图上正确定位
        const displayPosition = toDisplayCoords(lat, lng);

        // 3. 使用【显示坐标】来添加标记和设置地图中心
        const takeoffMarker = new AMap.Marker({
            position: displayPosition, // 使用转换后的显示坐标
            icon: new AMap.Icon({
                size: new AMap.Size(20, 20),
                image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
                    '<svg width="20" height="20" xmlns="http://www.w3.org/2000/svg">' +
                    '<circle cx="10" cy="10" r="8" fill="#4CAF50" stroke="#FFF" stroke-width="2"/>' +
                    '<path d="M7 10l2 2 4-4" stroke="#FFF" stroke-width="2" fill="none"/>' +
                    '</svg>'
                ),
                imageSize: new AMap.Size(20, 20)
            }),
            offset: new AMap.Pixel(-10, -10),
            title: '起飞点',
            clickable: false
        });
        map.add(takeoffMarker);
        map.setCenter(displayPosition); // 使用转换后的显示坐标
    }

    /**
     * 更新指定ID无人机的位置和轨迹
     * @param {object} positionData - 位置数据，包含 { longitude, latitude, heading }
     * @param {string} clientId - 无人机的唯一ID
     */
    function update(positionData, clientId) {
        if (!map) {
            console.warn("地图尚未初始化，无法更新。");
            return;
        }
        if (!positionData || typeof positionData.latitude !== 'number' || typeof positionData.longitude !== 'number') {
            console.warn(`无人机 [${clientId}] 数据无效，缺少经纬度信息。`, positionData);
            return;
        }
        current_pos = positionData

        // 【修改】使用辅助函数，代码更清晰
        // 1. 将无人机发来的【真实GPS坐标】转换为【显示坐标】
        const displayPosition = toDisplayCoords(positionData.latitude, positionData.longitude);

        if (drones[clientId]) {
            const drone = drones[clientId];

            // 使用指数移动平均(EMA)算法平滑位置
            const lastSmoothedPosition = drone.lastSmoothedPosition;
            const smoothedLat = lastSmoothedPosition.lat * (1 - SMOOTHING_FACTOR) + displayPosition.lat * SMOOTHING_FACTOR;
            const smoothedLng = lastSmoothedPosition.lng * (1 - SMOOTHING_FACTOR) + displayPosition.lng * SMOOTHING_FACTOR;

            const smoothedPosition = new AMap.LngLat(smoothedLng, smoothedLat);

            drone.marker.setPosition(smoothedPosition);
            drone.marker.setAngle(positionData.heading || 0);

            const path = drone.polyline.getPath();
            path.push(smoothedPosition);
            drone.polyline.setPath(path);

            drone.lastSmoothedPosition = smoothedPosition;

        } else {
            console.log(`首次检测到无人机 [${clientId}]，正在创建地图对象...`);

            const marker = new AMap.Marker({
                position: displayPosition, // 首次出现时，使用【显示坐标】
                icon: new AMap.Icon({
                    size: new AMap.Size(28, 28),
                    image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(droneIconSvg),
                    imageSize: new AMap.Size(28, 28),
                }),
                offset: new AMap.Pixel(-14, -14),
                angle: positionData.heading || 0,
                clickable: false
            });

            const polyline = new AMap.Polyline({
                path: [displayPosition], // 轨迹的第一个点也是【显示坐标】
                strokeColor: "#F57C00",
                strokeWeight: 5,
                strokeOpacity: 0.8,
                lineJoin: 'round',
                clickable: false
            });

            map.add([marker, polyline]);

            drones[clientId] = {
                marker: marker,
                polyline: polyline,
                lastSmoothedPosition: displayPosition // 初始化平滑位置为第一个【显示坐标】
            };

            if (Object.keys(drones).length === 1) {
                map.setCenter(displayPosition);
            }
        }

        // 让地图中心跟随平滑后的点
        map.setCenter(drones[clientId].lastSmoothedPosition);
    }

    /**
     * 清除地图上所有的无人机图标和轨迹
     */
    function clear() {
        if (!map) return;
        map.clearMap();
        drones = {};
        takeoffPoint = null;
        targetMarker = null;
        infoWindow = null;
        console.log("地图已清除。");
    }

    // 页面加载时执行
    document.addEventListener('DOMContentLoaded', () => {
        initMap();
        // ... (这部分代码完全不变，为节省篇幅已折叠，且这部分逻辑无需修改，因为它依赖于 window.lastCalculatedPosition，而我们已经修正了该值的来源)
        const btnSendTarget = document.getElementById('btn-send-target');
        const btnSendTargetLatLon = document.getElementById('btn-send-target-latlon');
        const btnSendOrigin = document.getElementById('btn-send-origin');
        const targetCoordsValue = document.querySelector('.coord-value');

        // 监听目标点更新
        const updateTargetCoords = () => {
            if (window.lastCalculatedPosition) {
                const pos = window.lastCalculatedPosition;
                targetCoordsValue.textContent = `X: ${pos.x.toFixed(2)}m, Y: ${pos.y.toFixed(2)}m`;
                btnSendTarget.disabled = false;
            } else {
                targetCoordsValue.textContent = '未选择';
                btnSendTarget.disabled = true;
            }
        };

        setInterval(updateTargetCoords, 500);

        btnSendTarget.addEventListener('click', () => {
            const selectedClient = document.getElementById('client-selector').value;
            if (!selectedClient) {
                alert('请先选择一个无人机！');
                return;
            }

            if (!window.lastCalculatedPosition) {
                alert('请先在地图上选择目标点！');
                return;
            }

            const pos = window.lastCalculatedPosition;
            const message = {
                client_id: selectedClient,
                payload: {
                    command: 'set_ros_target',
                    x: parseFloat(pos.y),
                    y: parseFloat(pos.x),
                    z: 0,
                }
            };

            if (controlWebSocket && controlWebSocket.readyState === WebSocket.OPEN) {
                controlWebSocket.send(JSON.stringify(message));
                logMessage(`发送目标点坐标: X=${pos.x.toFixed(2)}m, Y=${pos.y.toFixed(2)}m`);
                btnSendTarget.classList.add('success');
                setTimeout(() => btnSendTarget.classList.remove('success'), 1000);
            } else {
                alert('WebSocket连接已断开，请刷新页面重试！');
            }
        });
        btnSendTargetLatLon.addEventListener('click', () => {
            const selectedClient = document.getElementById('client-selector').value;
            if (!selectedClient) {
                alert('请先选择一个无人机！');
                return;
            }
            if (!window.lastCalculatedPosition) {
                alert('请先在地图上选择目标点！');
                return;
            }
            const pos = window.lastCalculatedPosition;
            const message = {
                client_id: selectedClient,
                payload: {
                    command: 'set_ros_target_latlon',
                    lat: parseFloat(pos.lat),
                    lon: parseFloat(pos.lng),
                    height: 0,
                }
            };
            if (controlWebSocket && controlWebSocket.readyState === WebSocket.OPEN) {
                controlWebSocket.send(JSON.stringify(message));
                btnSendTargetLatLon.classList.add('success');
                setTimeout(() => btnSendTargetLatLon.classList.remove('success'), 1000);
            } else {
                alert('WebSocket连接已断开，请刷新页面重试！');
            }
        });
        btnSendOrigin.addEventListener('click', () => {
            // 检查是否在地图上选择了位置 (此逻辑保留)
            if (!window.lastCalculatedPosition || typeof window.lastCalculatedPosition.lat !== 'number' || typeof window.lastCalculatedPosition.lng !== 'number') {
                alert('请先在地图上点击选择一个原点位置！');
                return;
            }

            const pos = window.lastCalculatedPosition;

            // 2. 构造广播消息
            const message = {
                client_id: 'all',
                payload: {
                    command: 'set_ros_origin',
                    lat: parseFloat(pos.lat),
                    lon: parseFloat(pos.lng)
                }
            };

            if (controlWebSocket && controlWebSocket.readyState === WebSocket.OPEN) {
                controlWebSocket.send(JSON.stringify(message));
                // 3. 更新日志和UI反馈信息
                logMessage(`向所有无人机发送原点经纬度: Lat=${pos.lat.toFixed(6)}, Lng=${pos.lng.toFixed(6)}`);
                btnSendOrigin.classList.add('success');
                setTimeout(() => btnSendOrigin.classList.remove('success'), 1000);
            } else {
                alert('WebSocket连接已断开，请刷新页面重试！');
            }
        });
    });

    return {
        update: update,
        clear: clear,
        setTakeoffPoint: setTakeoffPoint,
        _getMapInstance: function() { return map; },
        _getDrones: function() { return drones; },
        _getTakeoffPoint: function() { return takeoffPoint; }
    };

})();