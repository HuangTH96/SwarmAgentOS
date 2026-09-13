// /static/cluster_map.js (V3 - 恢复美术风格 & 优化选点逻辑)

window.ClusterMap = (function() {
    // --- 私有变量 ---
    let map = null;
    let drones = {};

    const lngOffset = 0.0052;
    const latOffset = -0.00205;

    let referenceOrigin = null; // 存储参考原点的【真实GPS】位置
    let targetMarker = null;
    let infoWindow = null;
    let originMarker = null; // 单独存储原点标记
    let droneInfoWindow = null;
    const EARTH_RADIUS = 6378137.0;
    const SMOOTHING_FACTOR = 0.3;

    // --- 恢复与单机版一致的美术风格 ---
    const droneIconSvg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
            <path d="M14,2 L26,26 L14,22 L2,26 L14,2" fill="#F57C00" stroke="#FFF" stroke-width="1"/>
        </svg>
    `;

    const targetIcon = new AMap.Icon({
        size: new AMap.Size(20, 20),
        image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
            '<svg width="20" height="20" xmlns="http://www.w3.org/2000/svg">' +
            '<circle cx="10" cy="10" r="8" fill="#FF4081" stroke="#FFF" stroke-width="2"/>' +
            '<circle cx="10" cy="10" r="2" fill="#FFF"/>' +
            '</svg>'
        ),
        imageSize: new AMap.Size(20, 20)
    });

    const originIcon = new AMap.Icon({
        size: new AMap.Size(20, 20),
        image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
            '<svg width="20" height="20" xmlns="http://www.w3.org/2000/svg">' +
            '<circle cx="10" cy="10" r="8" fill="#4CAF50" stroke="#FFF" stroke-width="2"/>' +
            '<path d="M7 10l2 2 4-4" stroke="#FFF" stroke-width="2" fill="none"/>' +
            '</svg>'
        ),
        imageSize: new AMap.Size(20, 20)
    });


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
        const y = EARTH_RADIUS * dLat;
        const x = EARTH_RADIUS * dLng * Math.cos(lat1 * Math.PI / 180.0);
        return { x, y };
    }

    function clearTargetMarker() {
        if (targetMarker) map.remove(targetMarker);
        if (infoWindow) infoWindow.close();
        targetMarker = null;
        infoWindow = null;
        window.lastCalculatedPosition = null;
    }

    function init() {
        const mapContainer = document.getElementById('cluster-map-area');
        if (!mapContainer) {
            console.error("【地图错误】: 找不到ID为 'cluster-map-area' 的HTML元素！");
            return;
        }

        map = new AMap.Map('cluster-map-area', {
            zoom: 18,
            center: [116.397428, 39.90923],
            viewMode: '3D',
            showBuildingBlock: true,
            expandZoomRange: true,
            zooms: [3, 20],
            defaultCursor: 'pointer',
        });

        map.addControl(new AMap.Scale());
        map.addControl(new AMap.ToolBar({ position: 'RB' }));

        // --- 修改开始: 3. 重写地图点击事件以处理坐标转换 ---
        map.on('click', function(e) {
            // 新增：点击地图空白处时，关闭无人机的信息窗体
            if (droneInfoWindow) {
                droneInfoWindow.close();
            }
             // 清除之前的标记和信息窗口
            clearTargetMarker();

            // 1. 获取地图上点击的【显示坐标】
            const displayLngLat = e.lnglat;

            // 2. 将显示坐标转换为【真实GPS坐标】
            const realCoords = toRealCoords(displayLngLat);

            let relativePos = null;
            let infoContent = `<div style="padding: 10px; color: #333;">
                                <h4 style="margin: 0 0 5px 0;">目标点信息</h4>
                                绝对坐标 (真实):<br>
                                Lat: ${realCoords.lat.toFixed(6)}<br>
                                Lng: ${realCoords.lng.toFixed(6)}
                                <hr style="margin: 5px 0; border: 0; border-top: 1px solid #eee;">`;

            // 3. 如果已设置参考原点，则使用【真实GPS坐标】进行距离计算
            if (referenceOrigin) {
                // referenceOrigin 存储的是真实坐标, realCoords 也是真实坐标
                relativePos = calculateDistanceInMeters(
                    referenceOrigin.latitude,
                    referenceOrigin.longitude,
                    realCoords.lat,
                    realCoords.lng
                );
                infoContent += `<h4 style="margin: 5px 0; color: #333;">相对坐标</h4>
                                <p style="margin: 5px 0; color: #666;">
                                    <span style="color: #FF4081;">X:</span> ${relativePos.x.toFixed(2)} 米<br>
                                    <span style="color: #FF4081;">Y:</span> ${relativePos.y.toFixed(2)} 米
                                </p>`;
            } else {
                // infoContent += `<p style="margin: 5px 0; color: #999;">请先点击地图设置参考原点</p>`;
            }
            infoContent += '</div>';

            // 4. 创建新的目标点标记，标记位置使用【显示坐标】
            targetMarker = new AMap.Marker({
                position: displayLngLat, // 标记必须放在地图上点击的位置
                icon: targetIcon,
                offset: new AMap.Pixel(-10, -10),
                title: '目标点',
                animation: 'AMAP_ANIMATION_DROP',
            });
            map.add(targetMarker);

            // 创建新的信息窗口 (位置也使用显示坐标)
            infoWindow = new AMap.InfoWindow({
                content: infoContent,
                offset: new AMap.Pixel(0, -20),
                closeWhenClickMap: true
            });
            infoWindow.open(map, targetMarker.getPosition());

            // 5. 将【真实GPS坐标】和计算出的相对坐标保存到全局变量，用于发送给无人机
            window.lastCalculatedPosition = {
                x: relativePos ? relativePos.x : null,
                y: relativePos ? relativePos.y : null,
                lat: realCoords.lat, // 存储真实纬度
                lng: realCoords.lng  // 存储真实经度
            };
        });
        // --- 修改结束 ---

        setupMapButtons();
        console.log("集群地图模块已初始化 (V4 - 已集成坐标转换)。");
    }

    /**
     * 绑定地图控制按钮的事件
     */
    function setupMapButtons() {
        const btnSendTargetLatLon = document.getElementById('btn-send-target-latlon');
        const btnSendOrigin = document.getElementById('btn-send-origin');
        const targetCoordsValue = document.querySelector('.coord-value');

        // 定时更新UI上的坐标显示
        setInterval(() => {
            if (window.lastCalculatedPosition) {
                const pos = window.lastCalculatedPosition;
                // 显示真实坐标
                targetCoordsValue.textContent = `Lat: ${pos.lat.toFixed(5)}, Lng: ${pos.lng.toFixed(5)}`;
            } else {
                targetCoordsValue.textContent = '未选择';
            }
        }, 500);

        // “发送目标点经纬度”按钮逻辑 (此部分逻辑不变, 因为它依赖的 lastCalculatedPosition 已经是真实坐标)
        btnSendTargetLatLon.addEventListener('click', () => {
            if (!window.lastCalculatedPosition) {
                alert('请先在地图上点击选择一个目标点！');
                return;
            }
            if (window.getSelectedClusterClients && window.getSelectedClusterClients().length === 0) {
                 alert('请先在左侧列表中勾选至少一台无人机！');
                 return;
            }

            const pos = window.lastCalculatedPosition;
            const payload = {
                command: 'set_ros_target_latlon',
                lat: parseFloat(pos.lat),
                lon: parseFloat(pos.lng),
                height: 0,
            };

            if (window.sendClusterCommand) {
                window.sendClusterCommand(payload);
                window.logClusterStatus(`已向选中无人机发送目标点: ${pos.lat.toFixed(5)}, ${pos.lng.toFixed(5)}`);
                btnSendTargetLatLon.classList.add('success');
                setTimeout(() => btnSendTargetLatLon.classList.remove('success'), 1000);
            }
        });

        // “设置原点坐标”按钮逻辑 (此部分逻辑不变, 因为它依赖的 lastCalculatedPosition 已经是真实坐标)
        btnSendOrigin.addEventListener('click', () => {
            console.log(1111111111)
            if (!window.lastCalculatedPosition) {
                alert('请先在地图上点击选择一个位置作为原点！');
                return;
            }

            const pos = window.lastCalculatedPosition;

            // 1. 在地图上设置参考点，并发送指令
            //setReferenceOrigin(pos.lat, pos.lng); // 传递的是真实坐标
            console.log(pos)
            if (window.getSelectedClusterClients && window.getSelectedClusterClients().length > 0) {
                 const payload = {
                    command: 'set_ros_origin',
                    lat: parseFloat(pos.lat),
                    lon: parseFloat(pos.lng)
                };
                if (window.sendClusterCommand) {
                    window.sendClusterCommand(payload);
                    window.logClusterStatus(`已向选中无人机发送ROS原点。`);
                }
            } else {
                window.logClusterStatus(`注意：地图参考原点已设置，但未选择无人机，未发送指令。`);
            }

            btnSendOrigin.classList.add('success');
            setTimeout(() => btnSendOrigin.classList.remove('success'), 1000);
        });
    }

    // 设置参考原点，绘制绿色标记
    function setReferenceOrigin(lat, lng) {
        // 1. 存储【真实GPS坐标】
        referenceOrigin = { latitude: lat, longitude: lng };

        if (originMarker) map.remove(originMarker); // 移除旧的原点标记

        // 2. 将真实坐标转换为【显示坐标】
        const displayPosition = toDisplayCoords(lat, lng);

        // 3. 使用【显示坐标】来添加标记和设置地图中心
        originMarker = new AMap.Marker({
            position: displayPosition, // 使用转换后的显示坐标
            icon: originIcon,
            offset: new AMap.Pixel(-10, -10),
            title: '参考原点',
        });
        map.add(originMarker);
        map.setCenter(displayPosition); // 使用转换后的显示坐标
        window.logClusterStatus(`地图参考原点已更新: ${lat.toFixed(5)}, ${lng.toFixed(5)}`);

        // 如果当前有目标点，重新计算其相对坐标并更新信息窗体
        if (targetMarker) {
             const targetDisplayPos = targetMarker.getPosition();
             // 模拟一次点击事件来刷新信息，确保逻辑一致
             map.emit('click', { lnglat: targetDisplayPos });
        }
    }


    function update(positionData, clientId) {
        if (!map) return;
        if (!positionData || typeof positionData.latitude !== 'number' || typeof positionData.longitude !== 'number') return;

        // 1. 将无人机发来的【真实GPS坐标】转换为【显示坐标】
        const displayPosition = toDisplayCoords(positionData.latitude, positionData.longitude);

        if (drones[clientId]) {
            const drone = drones[clientId];
            const lastPos = drone.lastSmoothedPosition;

            // 平滑算法作用于【显示坐标】
            const smoothedLat = lastPos.lat * (1 - SMOOTHING_FACTOR) + displayPosition.lat * SMOOTHING_FACTOR;
            const smoothedLng = lastPos.lng * (1 - SMOOTHING_FACTOR) + displayPosition.lng * SMOOTHING_FACTOR;
            const smoothedPosition = new AMap.LngLat(smoothedLng, smoothedLat);

            drone.marker.setPosition(smoothedPosition);
            drone.marker.setAngle(positionData.heading || 0);

            // 保存最新的【真实位置数据】到无人机对象上
            drone.latestPositionData = positionData;

            const path = drone.polyline.getPath();
            path.push(smoothedPosition); // 轨迹点使用平滑后的【显示坐标】
            drone.polyline.setPath(path);
            drone.lastSmoothedPosition = smoothedPosition;

        } else {
            // 创建标记时不再添加 label
            const marker = new AMap.Marker({
                position: displayPosition, // 首次出现时，使用【显示坐标】
                icon: new AMap.Icon({
                    size: new AMap.Size(28, 28),
                    image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(droneIconSvg),
                    imageSize: new AMap.Size(28, 28),
                }),
                offset: new AMap.Pixel(-14, -14),
                angle: positionData.heading || 0,
                title: `无人机ID: ${clientId}`
            });

            // 点击无人机显示信息窗体的逻辑 (这部分不变，因为它读取的是 drone.latestPositionData 中的真实数据)
            marker.on('click', function() {
                if (droneInfoWindow) {
                    droneInfoWindow.close();
                }

                const currentDroneData = drones[clientId].latestPositionData;
                const infoContent = `
                    <div style="padding: 5px; color: #333; font-size: 12px; line-height: 1.4;">
                        <strong>ID: ${clientId}</strong><br>
                        纬度: ${currentDroneData.latitude.toFixed(6)}<br>
                        经度: ${currentDroneData.longitude.toFixed(6)}<br>
                        x: ${currentDroneData.position_latlon.x.toFixed(6)}<br>
                        y: ${currentDroneData.position_latlon.y.toFixed(6)}
                    </div>
                `;

                droneInfoWindow = new AMap.InfoWindow({
                    isCustom: false,
                    content: infoContent,
                    offset: new AMap.Pixel(0, -30)
                });

                droneInfoWindow.open(map, this.getPosition());
            });

            const polyline = new AMap.Polyline({
                path: [displayPosition], // 轨迹的第一个点也是【显示坐标】
                strokeColor: "#F57C00",
                strokeWeight: 5,
                strokeOpacity: 0.8,
            });
            map.add([marker, polyline]);

            drones[clientId] = {
                marker,
                polyline,
                lastSmoothedPosition: displayPosition, // 初始化平滑位置为第一个【显示坐标】
                latestPositionData: positionData // 存储【真实位置数据】
            };

            if (Object.keys(drones).length === 1) {
                map.setCenter(displayPosition);
            }
        }
    }


    // 同步无人机列表，移除断连的无人机 (此函数无需修改)
    function syncDroneList(clients) {
        if (!map) return;
        const clientIds = clients.map(c => c.id);
        Object.keys(drones).forEach(id => {
            if (!clientIds.includes(id)) {
                if (drones[id].marker) map.remove(drones[id].marker);
                if (drones[id].polyline) map.remove(drones[id].polyline);
                delete drones[id];
            }
        });
    }

    return {
        init: init,
        update: update,
        syncDroneList: syncDroneList,
    };
})();