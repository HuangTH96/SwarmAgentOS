// /static/cluster_script.js

const clusterSocket = new WebSocket(`ws://${window.location.host}/ws/control`);

let clusterClients = [];

// 将核心函数暴露给其他脚本（如 cluster_map.js）
window.getSelectedClusterClients = () => {
    return Array.from(document.querySelectorAll('.cluster-client-checkbox:checked')).map(cb => cb.value);
};

window.logClusterStatus = (msg) => {
    const logDiv = document.getElementById('cluster-status-log');
    const p = document.createElement('div');
    p.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    logDiv.prepend(p);
};

// 此函数现在可以被 cluster_map.js 调用
window.sendClusterCommand = (payload) => {
    const selected = getSelectedClusterClients();
    console.log(selected);
    if (selected.length === 0) {
        logClusterStatus('错误：请先在列表中选择至少一台无人机');
        return;
    }
    selected.forEach(client_id => {
        const commandData = { client_id, payload };
        clusterSocket.send(JSON.stringify(commandData));
        logClusterStatus(`已向 ${client_id} 发送指令: ${JSON.stringify(payload)}`);
    });
};


clusterSocket.onopen = function() {
    logClusterStatus('WebSocket 连接已建立');
};

clusterSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);

    if (data.type === 'client_list' && data.clients) {
        clusterClients = data.clients;
        renderClusterClientList();
        // 调用新地图模块同步无人机列表
        if (window.ClusterMap) {
            window.ClusterMap.syncDroneList(clusterClients);
        }
    } else if (data.type === 'client_update') {
        clusterSocket.send(JSON.stringify({action: 'get_clients'}));
    } else if (data.type === 'telemetry_update') {
        updateClusterClientTelemetry(data.client_id, data.telemetry);
        // 调用新地图模块更新无人机位置
        if (window.ClusterMap && data.telemetry) {
            const positionData = {
                latitude: data.telemetry.latitude,
                longitude: data.telemetry.longtitude, // 注意这里的拼写
                heading: data.telemetry.head,
                position_latlon:data.telemetry.position_latlon
            };
            window.ClusterMap.update(positionData, data.client_id);
        }
    } else if (data.type === 'battery_update') {
        updateClusterClientBatteryInfo(data.client_id, data.battery_info);
    }
};

clusterSocket.onclose = function() {
    logClusterStatus('WebSocket 连接已关闭');
};

clusterSocket.onerror = function(error) {
    logClusterStatus('WebSocket 错误: ' + error);
};

function renderClusterClientList() {
    const selectedIds = getSelectedClusterClients();
    const display = document.getElementById('cluster-active-clients-display');
    display.innerHTML = '';

    if (clusterClients.length === 0) {
        display.innerHTML = '<div class="data-item">暂无无人机连接</div>';
        return;
    }

    clusterClients.forEach(client => {
        const tel = client.telemetry || {};
        const bar = client.battery_info || {};
        
        let batteryPercent = '--';
        if (bar && bar.batteries && Array.isArray(bar.batteries) && bar.batteries.length > 0) {
            batteryPercent = bar.batteries[0].percent || '--';
        } else if (tel && tel.battery !== undefined) {
            batteryPercent = tel.battery;
        }
        
        const div = document.createElement('div');
        div.className = 'data-item';
        div.innerHTML = `
            <label>
                <input type="checkbox" class="cluster-client-checkbox" value="${client.id}">
                <span class="status-indicator online">在线</span>
                <span class="data-label">ID: ${client.id}</span>
                <span class="data-value">${tel ? '高度:' + (tel.height || '--') : '--'}m</span>
                <span class="data-value">电量: ${batteryPercent}%</span>
            </label>
        `;
        display.appendChild(div);
    });

    selectedIds.forEach(id => {
        const checkbox = document.querySelector(`.cluster-client-checkbox[value="${id}"]`);
        if (checkbox) checkbox.checked = true;
    });
}

// 向后端API发送指令的函数（用于简单的字符串指令）
async function sendCommand(selectedClientId, command) {
    try {
        await fetch('/api/send-command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ client_id: selectedClientId, command: command })
        });
    } catch (error) {
        console.error('发送指令失败:', error);
    }
}

function sendClusterCommandStr(command) {
    const selected = getSelectedClusterClients();
    if (selected.length === 0) {
        logClusterStatus('请先选择至少一台无人机');
        return;
    }
    selected.forEach(client_id => {
        sendCommand(client_id, command);
        logClusterStatus(`已向 ${client_id} 发送指令: ${command}`);
    });
}

function setupClusterControlButtons() {
    document.getElementById('cluster-btn-takeoff').onclick = () => sendClusterCommandStr('takeoff');
    document.getElementById('cluster-btn-land').onclick = () => sendClusterCommandStr('land');
    document.getElementById('cluster-btn-confirm-land').onclick = () => sendClusterCommandStr('confirm_land');
    document.getElementById('cluster-btn-go-home').onclick = () => sendClusterCommandStr('go_home');
    document.getElementById('cluster-btn-cancel-go-home').onclick = () => sendClusterCommandStr('cancel_go_home');
    document.getElementById('cluster-btn-enable-vstick').onclick = () => sendClusterCommandStr('enable_vstick');
    document.getElementById('cluster-btn-disable-vstick').onclick = () => sendClusterCommandStr('disable_vstick');
    document.getElementById('cluster-btn-enable-vstick-advanced').onclick = () => sendClusterCommandStr('enable_vstick_advanced');
    document.getElementById('cluster-btn-disable-vstick-advanced').onclick = () => sendClusterCommandStr('disable_vstick_advanced');
    document.getElementById('cluster-btn-enable-ros-control').onclick = () => sendClusterCommandStr('enable_ros_control');
    document.getElementById('cluster-btn-disable-ros-control').onclick = () => sendClusterCommandStr( 'disable_ros_control');
}

document.addEventListener('DOMContentLoaded', () => {
    setupClusterControlButtons();
    // 初始化新的地图模块
    if (window.ClusterMap) {
        window.ClusterMap.init();
    } else {
        console.error("错误：cluster_map.js未能正确加载。");
    }
});

function updateClusterClientTelemetry(client_id, telemetry) {
    const idx = clusterClients.findIndex(c => c.id === client_id);
    if (idx !== -1) {
        clusterClients[idx].telemetry = telemetry;
        renderClusterClientList(); // 仅刷新左侧列表信息
    }
}

function updateClusterClientBatteryInfo(client_id, battery_info) {
    const idx = clusterClients.findIndex(c => c.id === client_id);
    if (idx !== -1) {
        clusterClients[idx].battery_info = battery_info;
        renderClusterClientList(); // 电池信息变化也刷新列表
    }
}

// ========== 集群虚拟摇杆功能 ==========
(function() {
    const SEND_INTERVAL = 100;
    const leftStick = document.getElementById('joystick-left');
    const rightStick = document.getElementById('joystick-right');
    if (!leftStick || !rightStick) return;

    function createSimpleJoystick(stickElement) {
        let isDragging = false;
        const joystickValues = { x: 0, y: 0 };
        const baseElement = stickElement.parentElement;
        const maxRadius = baseElement.getBoundingClientRect().width / 2;

        const onStart = (e) => { isDragging = true; e.preventDefault(); };
        const onEnd = (e) => {
            if (!isDragging) return;
            isDragging = false;
            stickElement.style.transform = `translate(0px, 0px)`;
            joystickValues.x = 0; joystickValues.y = 0;
            e.preventDefault();
        };
        const onMove = (e) => {
            if (!isDragging) return;
            e.preventDefault();
            const touch = e.touches ? e.touches[0] : null;
            const clientX = touch ? touch.clientX : e.clientX;
            const clientY = touch ? touch.clientY : e.clientY;
            const baseRect = baseElement.getBoundingClientRect();
            let dx = clientX - (baseRect.left + baseRect.width / 2);
            let dy = clientY - (baseRect.top + baseRect.height / 2);
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance > maxRadius) {
                dx = (dx / distance) * maxRadius;
                dy = (dy / distance) * maxRadius;
            }
            stickElement.style.transform = `translate(${dx}px, ${dy}px)`;
            joystickValues.x = parseFloat((dx / maxRadius).toFixed(4));
            joystickValues.y = parseFloat(((dy / maxRadius) * -1).toFixed(4));
        };
        
        stickElement.addEventListener('mousedown', onStart);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onEnd);
        document.addEventListener('mouseleave', onEnd); // 鼠标移出窗口也算结束
        stickElement.addEventListener('touchstart', onStart, { passive: false });
        document.addEventListener('touchmove', onMove, { passive: false });
        document.addEventListener('touchend', onEnd);
    
        return { getValues: () => joystickValues, isDragging: () => isDragging };
    }

    const leftJoystick = createSimpleJoystick(leftStick);
    const rightJoystick = createSimpleJoystick(rightStick);

    setInterval(() => {
        if (leftJoystick.isDragging() || rightJoystick.isDragging()) {
            const leftVals = leftJoystick.getValues();
            const rightVals = rightJoystick.getValues();
            const payload = {
                command: "vstick",
                data: {
                    left_stick_x: rightVals.x,
                    left_stick_y: rightVals.y,
                    right_stick_x: leftVals.x,
                    right_stick_y: leftVals.y,
                }
            };
            sendClusterCommand(payload);
        }
    }, SEND_INTERVAL);
})();


// ========== 集群位置控制模块逻辑 ==========
(function() {
    const xInput = document.getElementById('cluster-pos-x');
    const yInput = document.getElementById('cluster-pos-y');
    const zInput = document.getElementById('cluster-pos-z');
    const yawInput = document.getElementById('cluster-pos-yaw');
    if (!xInput) return;

    document.querySelectorAll('.position-control-section .decrement').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.nextElementSibling;
            input.value = (parseFloat(input.value) - parseFloat(input.step || 1)).toFixed(2);
        });
    });
    document.querySelectorAll('.position-control-section .increment').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.previousElementSibling;
            input.value = (parseFloat(input.value) + parseFloat(input.step || 1)).toFixed(2);
        });
    });

    document.getElementById('cluster-btn-send-position').onclick = function() {
        const payload = {
            command: 'position_control',
            x: parseFloat(xInput.value),
            y: parseFloat(yInput.value),
            z: parseFloat(zInput.value),
            yaw: parseFloat(yawInput.value)
        };
        sendClusterCommand(payload);
    };
})();