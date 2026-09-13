// static/js/joysticks.js (加固 + 键盘控制 + 调试日志版)


document.addEventListener('DOMContentLoaded', () => {
    // --- 全局配置 ---
    const SEND_INTERVAL = 100;

    function getSelectedClientId() {
        const selector = document.getElementById('client-selector');
        return selector ? selector.value : null;
    }

    const leftJoystickElement = document.getElementById('joystick-left');
    const rightJoystickElement = document.getElementById('joystick-right');

    if (!leftJoystickElement || !rightJoystickElement) {
        console.log("Joystick elements not found. Joystick functionality disabled.");
        return;
    }
// 一个可复用的函数来发送速度指令
window.sendVelocityCommand = function(clientId, leftX, leftY, rightX, rightY) {
    if (!clientId || typeof controlSocket === 'undefined' || controlSocket.readyState !== WebSocket.OPEN) {
        console.error("无法发送速度指令：WebSocket 未连接或未选择客户端。");
        // 不在这里 alert，因为会被高频调用
        return;
    }

    const message = {
        client_id: clientId,
        payload: {
            command: "vstick_advance_v",
            data: {
                left_stick_x: leftX,
                left_stick_y: leftY,
                right_stick_x: rightX,
                right_stick_y: rightY,
            }
        }
    };

    controlSocket.send(JSON.stringify(message));
    // console.log("Sent velocity command:", JSON.stringify(message)); // 减少日志刷屏
}
 // 处理高级虚拟摇杆指令
const btnSendAdvancedV = document.getElementById('btn-send-advanced-v');
if (btnSendAdvancedV) {
    btnSendAdvancedV.addEventListener('click', () => {
        const currentClientId = getSelectedClientId();
        if (!currentClientId) {
            alert("请先选择一个客户端！");
            return;
        }

        const leftX = parseFloat(document.getElementById('adv-left-x').value) || 0.0;
        const leftY = parseFloat(document.getElementById('adv-left-y').value) || 0.0;
        const rightX = parseFloat(document.getElementById('adv-right-x').value) || 0.0;
        const rightY = parseFloat(document.getElementById('adv-right-y').value) || 0.0;

        // 调用新的可复用函数
        sendVelocityCommand(currentClientId, leftX, leftY, rightX, rightY);
        logMessage(`发送单次速度指令: LX=${leftX}, LY=${leftY}, RX=${rightX}, RY=${rightY}`);
    });
}
const btnSendAdvancedP = document.getElementById('btn-send-advanced-p');
if (btnSendAdvancedP) {
    btnSendAdvancedP.addEventListener('click', () => {
        const currentClientId = getSelectedClientId();
        if (!currentClientId || typeof controlSocket === 'undefined' || controlSocket.readyState !== WebSocket.OPEN) {
            console.error("无法发送高级指令：WebSocket 未连接或未选择客户端。");
            alert("请先连接并选择一个客户端！");
            return;
        }

        // 从输入框读取值，并转换为浮点数
        const leftX = parseFloat(document.getElementById('adv-left-x').value) || 0.0;
        const leftY = parseFloat(document.getElementById('adv-left-y').value) || 0.0;
        const rightX = parseFloat(document.getElementById('adv-right-x').value) || 0.0;
        const rightY = parseFloat(document.getElementById('adv-right-y').value) || 0.0;

        // 构建与 Kotlin 后端 vstick_advance 逻辑匹配的消息
        const message = {
            client_id: currentClientId,
            payload: {
                command: "vstick_advance_p",
                data: {
                    // 注意：这里的键名必须与您 Kotlin 代码中 fromJson 解析的键名完全一致
                    left_stick_x: leftX,
                    left_stick_y: leftY,
                    right_stick_x: rightX,
                    right_stick_y: rightY,
                }
            }
        };

        const messageString = JSON.stringify(message);
        controlSocket.send(messageString);
        console.log("Sent advanced command:", messageString);
    });
}
    const sendJoystickData = () => {
        const currentClientId = getSelectedClientId();
        if (!currentClientId || typeof controlSocket === 'undefined' || controlSocket.readyState !== WebSocket.OPEN) {
            return;
        }

        const leftVals = leftJoystick.getValues();
        const rightVals = rightJoystick.getValues();

        const message = {
            client_id: currentClientId,
            payload: {
                command: "vstick",
                data: {
                    left_stick_x: rightVals.x,
                    left_stick_y: rightVals.y,
                    right_stick_x: leftVals.x,
                    right_stick_y: leftVals.y,
                }
            }
        };

        controlSocket.send(JSON.stringify(message));
        // console.log("Sent:", JSON.stringify(message.payload.data));
    };

    const leftJoystick = createJoystick(leftJoystickElement, sendJoystickData);
    const rightJoystick = createJoystick(rightJoystickElement, sendJoystickData);

    setInterval(() => {
        const isAnyJoystickActive = leftJoystick.isDragging() || rightJoystick.isDragging() ||
                                    leftJoystick.isKeyboardControlled() || rightJoystick.isKeyboardControlled();

        if (isAnyJoystickActive) {
            sendJoystickData();
        }
    }, SEND_INTERVAL);

    setupKeyboardControls(leftJoystick, rightJoystick, sendJoystickData);

    console.log("Joysticks and keyboard controls initialized. Click on the page to activate keyboard input.");
});

// 发送位置指令
const sendPositionBtn = document.getElementById('btn-send-position');
sendPositionBtn.addEventListener('click', () => {
    const selectedClient = document.getElementById('client-selector').value;
    if (!selectedClient) {
        alert('请先选择一个无人机！');
        return;
    }

    const positionData = {
        client_id: selectedClient,
        payload: {
            type: 'position_control',
            x: parseFloat(positionInputs.x.value),
            y: parseFloat(positionInputs.y.value),
            z: parseFloat(positionInputs.z.value),
            yaw: parseFloat(positionInputs.yaw.value)
        }
    };

    // 添加发送动画效果
    sendPositionBtn.classList.add('sending');
    setTimeout(() => sendPositionBtn.classList.remove('sending'), 1000);

    // 发送数据到服务器
    controlWebSocket.send(JSON.stringify(positionData));

    // 在状态日志中显示
    const logDisplay = document.getElementById('status-log');
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] 发送位置指令: X=${positionData.payload.x}m, Y=${positionData.payload.y}m, Z=${positionData.payload.z}m, Yaw=${positionData.payload.yaw}°\n`;
    logDisplay.textContent = logMessage + logDisplay.textContent;
});

function createJoystick(stickElement, onStateChange) {
    const baseElement = stickElement.parentElement;
    let isDragging = false;
    let isKeyboardControlled = false;
    const joystickValues = { x: 0, y: 0 };
    const maxRadius = baseElement.getBoundingClientRect().width / 2;

    function updateStickPosition(dx, dy) {
        stickElement.style.transform = `translate(${dx}px, ${dy}px)`;
    }

    function updateJoystickValues(dx, dy) {
         joystickValues.x = parseFloat((dx / maxRadius).toFixed(4));
         joystickValues.y = parseFloat(((dy / maxRadius) * -1).toFixed(4));
    }

    const onStart = (event) => {
        if (isKeyboardControlled) return;
        isDragging = true;
        baseElement.classList.add('active');
        event.preventDefault();
    };

    const onMove = (event) => {
        if (!isDragging) return;
        event.preventDefault();
        const touch = event.touches ? event.touches[0] : null;
        const clientX = touch ? touch.clientX : event.clientX;
        const clientY = touch ? touch.clientY : event.clientY;
        const baseRect = baseElement.getBoundingClientRect();
        const baseCenterX = baseRect.left + baseRect.width / 2;
        const baseCenterY = baseRect.top + baseRect.height / 2;
        let dx = clientX - baseCenterX;
        let dy = clientY - baseCenterY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance > maxRadius) {
            dx = (dx / distance) * maxRadius;
            dy = (dy / distance) * maxRadius;
        }
        updateStickPosition(dx, dy);
        updateJoystickValues(dx, dy);
    };

    const onEnd = (event) => {
        if (!isDragging) return;
        isDragging = false;
        baseElement.classList.remove('active');
        event.preventDefault();
        updateStickPosition(0, 0);
        updateJoystickValues(0, 0);
        if (typeof onStateChange === 'function') {
            onStateChange();
        }
    };

    stickElement.addEventListener('mousedown', onStart);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onEnd);
    document.addEventListener('mouseleave', onEnd);
    stickElement.addEventListener('touchstart', onStart, { passive: false });
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('touchend', onEnd);
    document.addEventListener('touchcancel', onEnd);

    return {
        getValues: () => joystickValues,
        isDragging: () => isDragging,
        isKeyboardControlled: () => isKeyboardControlled,
        setValues: (x, y) => {
            if(isDragging) return;
            const normalizedX = Math.max(-1, Math.min(1, x));
            const normalizedY = Math.max(-1, Math.min(1, y));
            isKeyboardControlled = (normalizedX !== 0 || normalizedY !== 0);
            if(isKeyboardControlled) {
                baseElement.classList.add('active');
            } else {
                baseElement.classList.remove('active');
            }
            const dx = normalizedX * maxRadius;
            const dy = normalizedY * -1 * maxRadius;
            updateStickPosition(dx, dy);
            updateJoystickValues(dx, dy);
        }
    };
}

/**
 * --- 增强版：设置键盘控制的函数 ---
 */
function setupKeyboardControls(leftStick, rightStick, sendDataCallback) {
    const keyState = new Set();
    // --- 修正：keyMap的值现在更具描述性，将在逻辑中直接使用 ---
    const keyMap = {
        'w': 'left_y_up', 's': 'left_y_down', 'a': 'left_x_left', 'd': 'left_x_right',
        'W': 'left_y_up', 'S': 'left_y_down', 'A': 'left_x_left', 'D': 'left_x_right', // 兼容大写
        'ArrowUp': 'right_y_up', 'ArrowDown': 'right_y_down', 'ArrowLeft': 'right_x_left', 'ArrowRight': 'right_x_right'
    };

    // --- 优化：使用 keyMap 的声明式处理逻辑 ---
    function handleKeyChange() {
        let leftX = 0, leftY = 0;
        let rightX = 0, rightY = 0;

        for (const key of keyState) {
            const action = keyMap[key];
            switch (action) {
                case 'left_y_up':    leftY += 1; break;
                case 'left_y_down':  leftY -= 1; break;
                case 'left_x_left':  leftX -= 1; break;
                case 'left_x_right': leftX += 1; break;
                case 'right_y_up':   rightY += 1; break;
                case 'right_y_down': rightY -= 1; break;
                case 'right_x_left': rightX -= 1; break;
                case 'right_x_right':rightX += 1; break;
            }
        }

        const leftMagnitude = Math.sqrt(leftX * leftX + leftY * leftY);
        if (leftMagnitude > 1) { // 如果大于1才需要归一化
            leftX /= leftMagnitude;
            leftY /= leftMagnitude;
        }

        const rightMagnitude = Math.sqrt(rightX * rightX + rightY * rightY);
        if (rightMagnitude > 1) {
            rightX /= rightMagnitude;
            rightY /= rightMagnitude;
        }

        leftStick.setValues(leftX, leftY);
        rightStick.setValues(rightX, rightY);
        // console.log(`Keyboard state: L(${leftX.toFixed(2)}, ${leftY.toFixed(2)}) R(${rightX.toFixed(2)}, ${rightY.toFixed(2)})`);
    }

    document.addEventListener('keydown', (e) => {
        // --- 调试日志 ---
        // console.log(`Keydown event fired. Key: "${e.key}"`);

        if (!keyMap[e.key] || keyState.has(e.key)) return;

        // --- 调试日志 ---
        console.log(`Control key pressed: "${e.key}"`);

        e.preventDefault();
        keyState.add(e.key);
        handleKeyChange();
    });

    document.addEventListener('keyup', (e) => {
        if (!keyMap[e.key]) return;

        // --- 调试日志 ---
        console.log(`Control key released: "${e.key}"`);

        e.preventDefault();
        keyState.delete(e.key);
        handleKeyChange();

        // 立即发送归位数据
        sendDataCallback();
    });

    window.addEventListener('blur', () => {
        if(keyState.size > 0) {
            console.log("Window lost focus. Resetting all keys.");
            keyState.clear();
            handleKeyChange();
            sendDataCallback();
        }
    });
}

