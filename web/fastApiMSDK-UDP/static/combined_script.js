// 获取DOM元素
const clientSelector = document.getElementById('client-selector');
const activeClientsDisplay = document.getElementById('active-clients-display'); // 已连接无人机列表区域
const droneInfoDisplay = document.getElementById('drone-info-display'); // 用于显示遥测和电池信息的新区域
const btnTakeoff = document.getElementById('btn-takeoff');
const btnLand = document.getElementById('btn-land');
const btnGoHome = document.getElementById('btn-go-home');
const btnCancelGoHome = document.getElementById('btn-cancel-go-home');
const btnConfirmLand = document.getElementById('btn-confirm-land');
const btnEnableVstick = document.getElementById('btn-enable-vstick');
const btnDisableVstick = document.getElementById('btn-disable-vstick');
const btnEnableVstickAdvanced = document.getElementById('btn-enable-vstick-advanced');
const btnDisableVstickAdvanced = document.getElementById('btn-disable-vstick-advanced');
const btnStartLive = document.getElementById('btn-start-live');
const btnStopLive = document.getElementById('btn-stop-live');
const btnEnableRosControl = document.getElementById('btn-enable-ros-control');
const btnDisableRosControl = document.getElementById('btn-disable-ros-control');


const statusLog = document.getElementById('status-log');
const mapArea = document.getElementById('map-area'); // 地图区域


const UavState = {
    UNKNOWN: 'UNKNOWN',
    GROUNDED: 'GROUNDED',
    FLYING: 'FLYING',
    WAITING_FOR_LAND_CONFIRM: 'WAITING_FOR_LAND_CONFIRM'
};
let currentUavState = UavState.UNKNOWN; // 当前无人机的状态

// 定义一个阈值高度，用于判断是否真的在飞
const FLYING_HEIGHT_THRESHOLD = 0.7; // 单位：米。当高度 > 0.8m 时，我们认为它在飞。
// =============================================

let controlWebSocket = null;
// 使用 Map 存储客户端信息 { clientId: { id, ip, name, telemetry, battery_info } }
const connectedClients = new Map();

// 添加日志的辅助函数
function logMessage(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${message}\n`;
    // 限制日志条数，避免内存过多
    const maxLogEntries = 50;
    const currentLog = statusLog.innerHTML;
    const lines = currentLog.split('\n');
    if (lines.length >= maxLogEntries) {
        lines.splice(maxLogEntries - 1); // 移除最旧的日志
    }
    statusLog.innerHTML = logEntry + lines.join('\n');
    statusLog.scrollTop = statusLog.scrollHeight; // 自动滚动到底部
    console.log(message);
}

// 从后端API获取已连接的客户端列表并更新UI (主要作为初始化或 WebSocket 备用)
async function fetchClients() {
    //logMessage("正在通过 HTTP 获取客户端列表...");
    try {
        const response = await fetch('/api/clients');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // 直接使用从 HTTP 获取的数据更新 Map 和 UI
        updateClientsDataAndUI(data.clients || []);

    } catch (error) {
        logMessage(`错误: 无法获取客户端列表. ${error}`);
        // 清空列表和选择框，显示错误状态
        activeClientsDisplay.innerHTML = '<p style="color:red;">无法连接到服务器获取客户端列表。</p>';
        clientSelector.innerHTML = '<option value="">-- 获取列表失败 --</option>';
         // 清空内部存储和信息面板
        connectedClients.clear();
        displayDroneInfo(null);
    }
}

// 向后端API发送指令
async function sendCommand(command) {
    const selectedClientId = clientSelector.value;
    console.log("takeoff")
    if (!selectedClientId) {
        logMessage("错误: 请先选择一个无人机！");
        alert("请先选择一个无人机！");
        return;
    }
    logMessage(`正在向 ${selectedClientId} 发送 '${command}' 指令...`);
    try {
        const response = await fetch('/api/send-command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                client_id: selectedClientId,
                command: command
            })
        });
        const result = await response.json();
        if (response.ok) {
            logMessage(`成功: ${result.message}`);
        } else {
            logMessage(`失败 (${response.status}): ${result.message}`);
        }
    } catch (error) {
        logMessage(`错误: 发送指令失败. ${error}`);
    }
}

// 建立前端到后端的 WebSocket 连接，用于接收实时数据和状态更新
function connectControlWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/control`;

    if (controlWebSocket) {
        controlWebSocket.close(); // 关闭现有连接
    }

    controlWebSocket = new WebSocket(wsUrl);

    controlWebSocket.onopen = function(event) {
        logMessage("控制面板 WebSocket 连接成功.");
    };

    controlWebSocket.onmessage = function(event) {
        try {
            const message = JSON.parse(event.data);
            const clientId = message.client_id;

            // ================== 修改 开始 (处理多种消息类型) ==================
            if (message.type === "telemetry_update") {
                if (connectedClients.has(clientId)) {
                    const clientData = connectedClients.get(clientId);
                    clientData.telemetry = message.telemetry;
                    // 如果当前选中的是此客户端，则更新显示
                    if (clientSelector.value === clientId) {
                        displayDroneInfo(clientData);
                    }
                } else {
                    logMessage(`收到未知客户端 ${clientId} 的遥测，触发列表刷新.`);
                    fetchClients();
                }

            } else if (message.type === "battery_update") {
                logMessage(`收到来自 ${clientId} 的电池信息更新。`);
                if (connectedClients.has(clientId)) {
                    const clientData = connectedClients.get(clientId);
                    clientData.battery_info = message.battery_info;
                    // 如果当前选中的是此客户端，则更新显示
                    if (clientSelector.value === clientId) {
                        displayDroneInfo(clientData);
                    }
                } else {
                    logMessage(`收到未知客户端 ${clientId} 的电池信息，触发列表刷新.`);
                    fetchClients();
                }

            } else if (message.type === "client_update") {
                logMessage("收到客户端列表更新通知，正在刷新...");
                fetchClients();
            }
            // ================== 修改 结束 ==================

        } catch (error) {
            logMessage("错误: 解析 WebSocket 消息失败: " + error);
            console.error("Error parsing WebSocket message:", error);
        }
    };

    controlWebSocket.onerror = function(event) {
        logMessage("控制面板 WebSocket 发生错误.");
        console.error("WebSocket error:", event);
    };

    controlWebSocket.onclose = function(event) {
        if (event.wasClean) {
            logMessage(`控制面板 WebSocket 连接关闭，代码=${event.code} 原因=${event.reason}`);
        } else {
            logMessage('控制面板 WebSocket 连接意外中断！');
        }
        controlWebSocket = null;
    };
}

// 更新内部存储的客户端数据和UI显示
function updateClientsDataAndUI(clients) {
    const currentSelected = clientSelector.value;
    const newClientsMap = new Map();

    // 保留旧数据(如遥测、电池)，并添加新客户端
    clients.forEach(client => {
        const existingData = connectedClients.get(client.id) || {};
        newClientsMap.set(client.id, { ...existingData, ...client });
    });

    // 清空并重新填充 Map
    connectedClients.clear();
    newClientsMap.forEach((value, key) => connectedClients.set(key, value));


    clientSelector.innerHTML = '';
    if (connectedClients.size === 0) {
        clientSelector.innerHTML = '<option value="">-- 等待无人机连接 --</option>';
    } else {
        connectedClients.forEach(client => {
            const option = document.createElement('option');
            option.value = client.id;
            option.textContent = `${client.name || client.id} (${client.ip})`;
            clientSelector.appendChild(option);
        });

        // ================== 修改 开始 (传递整个 client 对象) ==================
        if (connectedClients.has(currentSelected)) {
            clientSelector.value = currentSelected;
            displayDroneInfo(connectedClients.get(currentSelected));
        } else {
            if (connectedClients.size > 0) {
                const firstClient = connectedClients.values().next().value;
                clientSelector.value = firstClient.id;
                displayDroneInfo(firstClient);
            } else {
                clientSelector.value = "";
                displayDroneInfo(null);
            }
        }
        // ================== 修改 结束 ==================
    }

    // 更新左侧已连接列表
    if (connectedClients.size === 0) {
        activeClientsDisplay.innerHTML = '<p>当前没有无人机连接。</p>';
    } else {
        let clientListHtml = '';
        connectedClients.forEach(client => {
             clientListHtml += `<li><strong>${client.name || client.id}</strong> from ${client.ip}</li>`;
        });
        activeClientsDisplay.innerHTML = `<ul>${clientListHtml}</ul>`;
    }
}


/**
 * 显示无人机遥测和电池信息到指定区域
 * @param {object | null} clientData - 包含遥测和电池信息的完整客户端对象
 */
function displayDroneInfo(clientData) {
    droneInfoDisplay.innerHTML = '';

    // 如果没有客户端数据或没有遥测数据，显示提示信息并重置状态
    if (!clientData || !clientData.telemetry) {
        droneInfoDisplay.innerHTML = '<p>请在左侧选择一个无人机以查看信息，或等待无人机连接并发送数据。</p>';
        if (window.DroneMap) {
            window.DroneMap.clear();
        }
        updateButtonVisibility(UavState.UNKNOWN);
        btnEnableVstick.style.display = 'inline-block';
        btnDisableVstick.style.display = 'none';
        btnGoHome.style.display = 'inline-block';
        btnCancelGoHome.style.display = 'none';

        // ================== 新增代码 开始 ==================
        // 当没有数据时，重置ROS按钮为默认状态
        btnEnableRosControl.style.display = 'inline-block';
        btnDisableRosControl.style.display = 'none';
        // ================== 新增代码 结束 ==================
        return;
    }

    const telemetry = clientData.telemetry;
    const batteryInfo = clientData.battery_info; // 可能会是 undefined
    const selectedClientId = clientSelector.value || 'N/A';

    // --- 1. 渲染遥测信息 ---
    let telemetryHtml = `<h3>遥测数据</h3>`;
    telemetryHtml += `<p><strong>ID:</strong> ${selectedClientId}</p>`;
    telemetryHtml += `<p><strong>经度 (Lng):</strong> ${telemetry.longtitude?.toFixed(12) || 'N/A'}</p>`;
    telemetryHtml += `<p><strong>纬度 (Lat):</strong> ${telemetry.latitude?.toFixed(12) || 'N/A'}</p>`;
    telemetryHtml += `<p><strong>高度 (Alt):</strong> ${telemetry.height?.toFixed(5) || 'N/A'} m</p>`;
    telemetryHtml += `<p><strong>速度 (Speed):</strong> ${telemetry.speed?.toFixed(5) || 'N/A'} m/s</p>`;
    telemetryHtml += `<p><strong>航向 (Head):</strong> ${telemetry.head?.toFixed(5) || 'N/A'} °</p>`;
    if (telemetry.origin_location && typeof telemetry.origin_location === 'object') {
         telemetryHtml += `<p><strong>原点:</strong> Lat=${telemetry.origin_location.latitude?.toFixed(6) || 'N/A'}, Lng=${telemetry.origin_location.longitude?.toFixed(6) || 'N/A'}</p>`;
    } else {
         telemetryHtml += `<p><strong>原点:</strong> N/A</p>`;
    }
    // Home点（保持原有逻辑）
    if (telemetry.homeLocation && typeof telemetry.homeLocation === 'object') {
        telemetryHtml += `<p><strong>Home点:</strong> Lat=${telemetry.homeLocation.latitude?.toFixed(6) || 'N/A'}, Lng=${telemetry.homeLocation.longitude?.toFixed(6) || 'N/A'}</p>`;
    } else {
        telemetryHtml += `<p><strong>Home点:</strong> N/A</p>`;
    }

    // 新增：渲染四元数 (Quaternion)
    if (telemetry.quaternion && typeof telemetry.quaternion === 'object') {
        telemetryHtml += `<p><strong>四元数 (Quaternion):</strong> ` +
                         `W=${telemetry.quaternion.w?.toFixed(6) || 'N/A'}, ` +
                         `X=${telemetry.quaternion.x?.toFixed(6) || 'N/A'}, ` +
                         `Y=${telemetry.quaternion.y?.toFixed(6) || 'N/A'}, ` +
                         `Z=${telemetry.quaternion.z?.toFixed(6) || 'N/A'}</p>`;
    } else {
        telemetryHtml += `<p><strong>四元数 (Quaternion):</strong> N/A</p>`;
    }

    // 新增：渲染速度分量 (Velocity)
    if (telemetry.velocity && typeof telemetry.velocity === 'object') {
        telemetryHtml += `<p><strong>速度分量 (Velocity):</strong> ` +
                         `X=${telemetry.velocity.x?.toFixed(5) || 'N/A'}, ` +
                         `Y=${telemetry.velocity.y?.toFixed(5) || 'N/A'}, ` +
                         `Z=${telemetry.velocity.z?.toFixed(5) || 'N/A'} m/s</p>`;
    } else {
        telemetryHtml += `<p><strong>速度分量 (Velocity):</strong> N/A</p>`;
    }
    if (telemetry.ros_xyz && typeof telemetry.velocity === 'object') {
        telemetryHtml += `<p><strong>Ros_XYZ</strong> ` +
                         `X=${telemetry.ros_xyz.x?.toFixed(5) || 'N/A'}, ` +
                         `Y=${telemetry.ros_xyz.y?.toFixed(5) || 'N/A'}, ` +
                         `Z=${telemetry.ros_xyz.z?.toFixed(5) || 'N/A'} m/s</p>`;
    } else {
        telemetryHtml += `<p><strong>ROS XYZ</strong> N/A</p>`;
    }

    if (telemetry.position_vo && typeof telemetry.position_vo === 'object') {
        telemetryHtml += `<p><strong>World XYZ (Velocity):</strong> ` +
                         `X=${telemetry.position_vo.x?.toFixed(5) || 'N/A'}, ` +
                         `Y=${telemetry.position_vo.y?.toFixed(5) || 'N/A'}, ` +
                         `Z=${telemetry.position_vo.z?.toFixed(5) || 'N/A'} m/s</p>`;
    } else {
        telemetryHtml += `<p><strong>World XYZ (Velocity):</strong> N/A</p>`;
    }

    if (telemetry.angular_velocity && typeof telemetry.angular_velocity === 'object') {
    telemetryHtml += `<p><strong>角速度分量 (Velocity):</strong> ` +
                     `X=${telemetry.angular_velocity.x?.toFixed(5) || 'N/A'}, ` +
                     `Y=${telemetry.angular_velocity.y?.toFixed(5) || 'N/A'}, ` +
                     `Z=${telemetry.angular_velocity.z?.toFixed(5) || 'N/A'} m/s</p>`;
    } else {
        telemetryHtml += `<p><strong>角速度分量 (Velocity):</strong> N/A</p>`;
    }


    // 新增：渲染加速度 (Acceleration)
    if (telemetry.acceleration && typeof telemetry.acceleration === 'object') {
        telemetryHtml += `<p><strong>加速度 (Acceleration):</strong> ` +
                         `X=${telemetry.acceleration.x?.toFixed(5) || 'N/A'}, ` +
                         `Y=${telemetry.acceleration.y?.toFixed(5) || 'N/A'}, ` +
                         `Z=${telemetry.acceleration.z?.toFixed(5) || 'N/A'} m/s<sup>2</sup></p>`;
    } else {
        telemetryHtml += `<p><strong>加速度 (Acceleration):</strong> N/A</p>`;
    }

    if (telemetry.position_latlon && typeof telemetry.position_latlon === 'object') {
        telemetryHtml += `<p><strong>Position_latlon_XYZ</strong> ` +
                         `X=${telemetry.position_latlon.x?.toFixed(5) || 'N/A'}, ` +
                         `Y=${telemetry.position_latlon.y?.toFixed(5) || 'N/A'}, ` +
                         `Z=${telemetry.position_latlon.z?.toFixed(5) || 'N/A'} m/s</p>`;
    } else {
        telemetryHtml += `<p><strong>Position_latlon_XYZ</strong> N/A</p>`;
    }
    //console.log(telemetry)
    telemetryHtml += `<p><strong>Fly state</strong> ` + `${telemetry.flystate}, `
    // 添加视觉定位位置信息
    if (telemetry.position_vo && typeof telemetry.position_vo === 'object') {
        telemetryHtml += `<div class="vo-position-section">
            <h4>视觉定位位置</h4>
            <div class="vo-position-grid">
                <div class="vo-position-item">
                    <div class="vo-position-label">X 坐标</div>
                    <div class="vo-position-value">${telemetry.position_vo.x?.toFixed(3) || 'N/A'} m</div>
                </div>
                <div class="vo-position-item">
                    <div class="vo-position-label">Y 坐标</div>
                    <div class="vo-position-value">${telemetry.position_vo.y?.toFixed(3) || 'N/A'} m</div>
                </div>
                <div class="vo-position-item">
                    <div class="vo-position-label">Z 坐标</div>
                    <div class="vo-position-value">${telemetry.position_vo.z?.toFixed(3) || 'N/A'} m</div>
                </div>
            </div>
        </div>`;
    }

    //console.log(telemetry)

    // --- 2. 渲染电池信息 (如果存在) ---
    let batteryHtml = '<h3>电池信息</h3>';
    if (batteryInfo && batteryInfo.batteries && Array.isArray(batteryInfo.batteries) && batteryInfo.batteries.length > 0) {
        batteryHtml += '<div class="battery-container">';
        batteryInfo.batteries.forEach((battery, index) => {
            // 注意: 这里的 'voltage', 'percentage', 'status' 字段名需要与你后端 BatteryData 模型中的字段名完全一致
            batteryHtml += `<div class="battery-item" style="margin-top: 10px;">`;
            batteryHtml += `<p><strong>电池:</strong></p>`;
            batteryHtml += `<ul style="margin: 0; padding-left: 20px;">`;
            batteryHtml += `<li><strong>电压:</strong> ${battery.voltage ?? 'N/A'} V</li>`;
            batteryHtml += `<li><strong>电量:</strong> ${battery.percent ?? 'N/A'} %</li>`;
            batteryHtml += `<li><strong>状态:</strong> ${battery.connected ?? 'N/A'}</li>`;
            batteryHtml += `</ul>`;
            batteryHtml += `</div>`;
        });
        batteryHtml += '</div>';
    } else {
        batteryHtml += '<p>暂无电池数据。</p>';
    }

    // --- 3. 组合并更新到DOM ---
    droneInfoDisplay.innerHTML = telemetryHtml + '<hr>' + batteryHtml;

    // --- 4. 更新地图和飞行状态按钮 ---
    if (window.DroneMap && typeof telemetry.longtitude !== 'undefined' && typeof telemetry.latitude !== 'undefined') {
        const positionData = { longitude: telemetry.longtitude, latitude: telemetry.latitude, heading: telemetry.head || 0 };

        window.DroneMap.update(positionData, selectedClientId);
    }

    if (typeof telemetry.height === 'undefined') {
        updateButtonVisibility(UavState.UNKNOWN);
    } else if (telemetry.height > 0.2 && telemetry.height <= FLYING_HEIGHT_THRESHOLD) {
        updateButtonVisibility(UavState.WAITING_FOR_LAND_CONFIRM);
    } else if (telemetry.height > FLYING_HEIGHT_THRESHOLD) {
        updateButtonVisibility(UavState.FLYING);
    } else {
        updateButtonVisibility(UavState.GROUNDED);
    }

    // ================== 新增代码 开始 ==================
    // --- 5. 根据遥测数据更新ROS控制按钮的可见性 ---
    if (telemetry.ros_enabled) {
        // 如果 ros_enabled 为 true，显示“禁用”按钮，隐藏“启用”按钮
        btnEnableRosControl.style.display = 'none';
        btnDisableRosControl.style.display = 'inline-block';
    } else {
        // 如果 ros_enabled 为 false 或不存在，显示“启用”按钮，隐藏“禁用”按钮
        btnEnableRosControl.style.display = 'inline-block';
        btnDisableRosControl.style.display = 'none';
    }
    // ================== 新增代码 结束 ==================
}


/**
 * 根据当前的无人机状态更新控制按钮的可见性
 * @param {string} newState - UavState 中的一个值
 */
function updateButtonVisibility(newState) {
    if (newState === currentUavState) {
        return;
    }

    logMessage(`无人机状态更新: 从 ${currentUavState} -> ${newState}`);
    currentUavState = newState;

    btnTakeoff.style.display = 'none';
    btnLand.style.display = 'none';
    btnConfirmLand.style.display = 'none';
    btnTakeoff.style.display = 'inline-block';
    btnLand.style.display = 'inline-block';
    btnConfirmLand.style.display = 'inline-block';
}
function sendPositionCommand(clientId, x, y, z, yaw) {
    if (!clientId) {
        alert('错误：未选择无人机！');
        logMessage('错误：尝试发送位置指令但未选择无人机。');
        return;
    }

    const positionData = {
        client_id: clientId,
        payload: {
            type: 'position_control',
            x: parseFloat(x),
            y: parseFloat(y),
            z: parseFloat(z),
            yaw: parseFloat(yaw)
        }
    };

    if (controlWebSocket && controlWebSocket.readyState === WebSocket.OPEN) {
        controlWebSocket.send(JSON.stringify(positionData));
        logMessage(`发送位置指令: X=${x}m, Y=${y}m, Z=${z}m, Yaw=${yaw}°`);
    } else {
        alert('WebSocket 连接已断开，无法发送指令！');
    }
}

// 绑定按钮点击事件
btnTakeoff.addEventListener('click', async () => {
    const selectedClientId = clientSelector.value;
    if (!selectedClientId) {
        alert('请先选择一个无人机！');
        return;
    }
    //console.log("take off")
    // 获取当前无人机的遥测数据
    const clientData = connectedClients.get(selectedClientId);
    if (clientData && clientData.telemetry) {
        const telemetry = clientData.telemetry;
        // 记录起飞点位置
        if (typeof telemetry.latitude === 'number' && typeof telemetry.longtitude === 'number') {
            window.DroneMap.setTakeoffPoint(telemetry.latitude, telemetry.longtitude);
            logMessage(`记录起飞点位置: 纬度=${telemetry.latitude}, 经度=${telemetry.longtitude}`);
        }
    }

    // 发送起飞指令
    await sendCommand('takeoff');
});
btnLand.addEventListener('click', () => sendCommand('land'));
btnConfirmLand.addEventListener('click', () => sendCommand('confirm_land'));
// btnStartLive.addEventListener('click', () => sendCommand('start_rtsp_live'));
// btnStopLive.addEventListener('click', () => sendCommand('stop_rtsp_live'));
btnStartLive.addEventListener('click', () => sendCommand('start_rtmp_live'));
btnStopLive.addEventListener('click', () => sendCommand('stop_rtmp_live'));

btnEnableVstick.addEventListener('click', () => {
    sendCommand('enable_vstick');
    btnEnableVstick.style.display = 'none';
    btnDisableVstick.style.display = 'inline-block';
});

btnDisableVstick.addEventListener('click', () => {
    sendCommand('disable_vstick');
    btnDisableVstick.style.display = 'none';
    btnEnableVstick.style.display = 'inline-block';
});
btnEnableRosControl.addEventListener('click', () => {
    sendCommand('enable_ros_control');
    // 注意：点击后，按钮状态会由下一次遥测更新来改变，而不是立即改变
    // btnEnableRosControl.style.display = 'none';
    // btnDisableRosControl.style.display = 'inline-block';
});

btnDisableRosControl.addEventListener('click', () => {
    sendCommand('disable_ros_control');
    // 注意：点击后，按钮状态会由下一次遥测更新来改变，而不是立即改变
    // btnDisableRosControl.style.display = 'none';
    // btnEnableRosControl.style.display = 'inline-block';
});
btnEnableVstickAdvanced.addEventListener('click', () => {
    sendCommand('enable_vstick_advanced_mode');
    btnEnableVstickAdvanced.style.display = 'none';
    btnDisableVstickAdvanced.style.display = 'inline-block';
});

btnDisableVstickAdvanced.addEventListener('click', () => {
    sendCommand('disable_vstick_advanced_mode');
    btnDisableVstickAdvanced.style.display = 'none';
    btnEnableVstickAdvanced.style.display = 'inline-block';
});
// 为“返航”按钮添加点击事件监听器
btnGoHome.addEventListener('click', () => {
    sendCommand('go_home'); // 发送启动返航的命令
    btnGoHome.style.display = 'none'; // 隐藏“返航”按钮
    btnCancelGoHome.style.display = 'inline-block'; // 显示“取消返航”按钮
});

// 为“取消返航”按钮添加点击事件监听器
btnCancelGoHome.addEventListener('click', () => {
    sendCommand('cancel_go_home'); // 发送取消返航的命令
    btnCancelGoHome.style.display = 'none'; // 隐藏“取消返航”按钮
    btnGoHome.style.display = 'inline-block'; // 显示“返航”按钮
});

// 绑定客户端选择下拉菜单的 change 事件
clientSelector.addEventListener('change', () => {
    const selectedClientId = clientSelector.value;
    if (selectedClientId) {
        logMessage(`已选择无人机: ${selectedClientId}`);

        // ================== 修改 开始 (传递整个 client 对象) ==================
        const clientData = connectedClients.get(selectedClientId);
        displayDroneInfo(clientData);
        // ================== 修改 结束 ==================

        // 每次切换都重置V-stick按钮状态，确保UI是干净的初始状态
        btnEnableVstick.style.display = 'inline-block';
        btnDisableVstick.style.display = 'none';
    } else {
        logMessage("已取消选择无人机.");
        displayDroneInfo(null); // 这会调用内部的重置逻辑
    }
});

// 位置控制相关代码
document.addEventListener('DOMContentLoaded', function() {
    // 获取所有输入组件
    const positionInputs = {
        x: document.getElementById('pos-x'),
        y: document.getElementById('pos-y'),
        z: document.getElementById('pos-z'),
        yaw: document.getElementById('pos-yaw')
    };

    // 为每个输入组添加增减按钮事件
    Object.keys(positionInputs).forEach(key => {
        const input = positionInputs[key];
        const container = input.parentElement;
        const decBtn = container.querySelector('.decrement');
        const incBtn = container.querySelector('.increment');
        const step = parseFloat(input.getAttribute('step')) || 0.5;

        // 增加按钮事件
        incBtn.addEventListener('click', () => {
            input.value = (parseFloat(input.value) + step).toFixed(1);
            input.classList.add('value-update');
            setTimeout(() => input.classList.remove('value-update'), 300);
        });

        // 减少按钮事件
        decBtn.addEventListener('click', () => {
            input.value = (parseFloat(input.value) - step).toFixed(1);
            input.classList.add('value-update');
            setTimeout(() => input.classList.remove('value-update'), 300);
        });

        // 输入验证
        input.addEventListener('change', () => {
            let value = parseFloat(input.value);
            if (isNaN(value)) {
                value = 0;
            }
            input.value = value.toFixed(1);
        });
    });

    // 发送位置指令
    // 发送位置指令
    const sendPositionBtn = document.getElementById('btn-send-position');
    sendPositionBtn.addEventListener('click', () => {
        const selectedClient = document.getElementById('client-selector').value;
        const positionInputs = {
            x: document.getElementById('pos-x'),
            y: document.getElementById('pos-y'),
            z: document.getElementById('pos-z'),
            yaw: document.getElementById('pos-yaw')
        };

        // 调用新的可复用函数
        sendPositionCommand(
            selectedClient,
            positionInputs.x.value,
            positionInputs.y.value,
            positionInputs.z.value,
            positionInputs.yaw.value
        );

        // 动画效果保留在按钮点击事件中
        sendPositionBtn.classList.add('sending');
        setTimeout(() => sendPositionBtn.classList.remove('sending'), 1000);
    });
});


// 页面加载时执行
document.addEventListener('DOMContentLoaded', () => {
    logMessage("控制中心已启动。");

    btnEnableVstick.style.display = 'inline-block';
    btnDisableVstick.style.display = 'none';

    connectControlWebSocket();
    fetchClients(); // 初始加载一次
    setInterval(fetchClients, 5000); // 降低轮询频率，主要依赖 WebSocket
});

// 在页面关闭或刷新前尝试关闭 WebSocket 连接
window.addEventListener('beforeunload', () => {
    if (controlWebSocket) {
        controlWebSocket.close(1000, "Page unloading");
    }
});