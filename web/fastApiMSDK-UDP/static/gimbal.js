// static/js/gimbal.js (修正版)

(function() {
    document.addEventListener('DOMContentLoaded', () => {
        // --- 配置 ---
        const SEND_INTERVAL = 100; // 每100ms检查一次摇杆状态 (10Hz)
        const THROTTLE_LIMIT = 1000; // 发送旋转命令的最小间隔 (ms) - 修正为1秒
        const GIMBAL_JOYSTICK_ID = 'joystick-gimbal';

        // --- 获取DOM元素 ---
        const gimbalJoystickElement = document.getElementById(GIMBAL_JOYSTICK_ID);
        const btnReset = document.getElementById('gimbal-reset');
        const btnModeFree = document.getElementById('gimbal-mode-free');
        const btnModeFollow = document.getElementById('gimbal-mode-follow');
        const clientSelector = document.getElementById('client-selector'); // 明确获取客户端选择器

        // 假定 logMessage 函数存在于全局作用域或已导入
        // 如果没有，可以提供一个简单的回退，例如：
        const logMessage = typeof window.logMessage === 'function' ? window.logMessage : console.log;

        if (!gimbalJoystickElement || !btnReset || !btnModeFree || !btnModeFollow || !clientSelector) {
            console.log("Gimbal control elements not found. Gimbal functionality disabled.");
            return;
        }

        function createJoystick(stickElement) {
            const baseElement = stickElement.parentElement;
            let isDragging = false;
            const joystickValues = { x: 0, y: 0 };
            let maxRadius = 0; // 初始化为0，等待实际尺寸可用

            // 确保在元素可见后计算尺寸，并在窗口大小改变时更新
            const updateMaxRadius = () => {
                const rect = baseElement.getBoundingClientRect();
                if (rect.width > 0) { // 只有当元素有实际宽度时才计算
                    maxRadius = rect.width / 2;
                }
            };

            // 初始计算一次
            updateMaxRadius();
            // 监听窗口大小改变，重新计算
            window.addEventListener('resize', updateMaxRadius);

            function updateStickPosition(dx, dy) {
                stickElement.style.transform = `translate(${dx}px, ${dy}px)`;
            }

            function updateJoystickValues(dx, dy) {
                // 避免除以零
                joystickValues.x = maxRadius === 0 ? 0 : parseFloat((dx / maxRadius).toFixed(4));
                joystickValues.y = maxRadius === 0 ? 0 : parseFloat(((dy / maxRadius) * -1).toFixed(4));
            }

            const onStart = (event) => {
                isDragging = true;
                baseElement.classList.add('active');
                event.preventDefault();
                updateMaxRadius(); // 在拖动开始时再次更新maxRadius，以防首次计算不准确
            };

            const onMove = (event) => {
                if (!isDragging || maxRadius === 0) return; // 如果maxRadius为0，则无法计算，提前返回
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
            };
        }

        // --- 共享的辅助函数 ---
        function getSelectedClientId() {
            // clientSelector 已在上方获取
            return clientSelector.value;
        }

        function throttle(func, limit) {
            let inThrottle;
            let lastArgs;
            let lastThis;

            return function(...args) {
                lastArgs = args;
                lastThis = this;
                if (!inThrottle) {
                    func.apply(lastThis, lastArgs);
                    inThrottle = true;
                    setTimeout(() => {
                        inThrottle = false;
                        // 如果在节流期间有新的调用，可以在这里立即执行最后一次调用
                        // 但对于持续控制（如摇杆），通常不需要，因为新的周期会发送最新状态
                    }, limit);
                }
            }
        }

        // 向后端API发送指令
        async function sendGimbalCommand(command) {
            const selectedClientId = getSelectedClientId();
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

        const throttledSendGimbalCommand = throttle(sendGimbalCommand, THROTTLE_LIMIT);

        // --- 事件绑定 ---
        btnReset.addEventListener('click', () => sendGimbalCommand('psdk_gimbal_reset'));
        btnModeFree.addEventListener('click', () => sendGimbalCommand('psdk_gimbal_mode:free'));
        btnModeFollow.addEventListener('click', () => sendGimbalCommand('psdk_gimbal_mode:yaw_follow'));

        // *** 修改：现在调用的是本文件内的 createJoystick 函数 ***
        const gimbalJoystick = createJoystick(gimbalJoystickElement);

        // --- 云台旋转控制逻辑 ---
        let lastPitch = 0;
        let lastYaw = 0;

        setInterval(() => {
            // 如果摇杆没有被拖动
            if (!gimbalJoystick.isDragging()) {
                // 只有当云台之前可能在运动时，才发送停止命令
                if (lastPitch !== 0 || lastYaw !== 0) {
                    throttledSendGimbalCommand(`psdk_gimbal_rotate:0,0`); // 发送停止命令
                    lastPitch = 0; // 重置记录的值
                    lastYaw = 0;
                }
                return; // 摇杆未拖动时，不进行后续处理
            }

            const { x: yawValue, y: pitchValue } = gimbalJoystick.getValues();

            const nonLinearMap = (value, maxAngle) => Math.sign(value) * maxAngle * (value * value);
            const pitchAngle = nonLinearMap(pitchValue, 15);
            const yawAngle = nonLinearMap(yawValue, 15);

            const deadZone = 0.15; // 死区，低于此值视为0
            const smoothing = 0.6; // 平滑因子
            const minChange = 0.3; // 最小变化量，低于此变化不发送命令

            const applySmoothing = (current, last) => {
                if (Math.abs(current) < deadZone) return 0; // 在死区内，直接返回0
                return last + (current - last) * smoothing;
            };

            const finalPitch = applySmoothing(pitchAngle, lastPitch);
            const finalYaw = applySmoothing(yawAngle, lastYaw);

            // 检查最终计算出的值是否与上次发送的值有足够的变化
            const pitchChanged = Math.abs(finalPitch - lastPitch) >= minChange;
            const yawChanged = Math.abs(finalYaw - lastYaw) >= minChange;

            if ((pitchChanged || yawChanged) && !isNaN(finalPitch) && !isNaN(finalYaw)) {
                const command = `psdk_gimbal_rotate:${finalPitch.toFixed(2)},${finalYaw.toFixed(2)}`;
                throttledSendGimbalCommand(command);

                lastPitch = finalPitch;
                lastYaw = finalYaw;
            }
        }, SEND_INTERVAL);

        console.log("Gimbal controls initialized.");
    });
})();