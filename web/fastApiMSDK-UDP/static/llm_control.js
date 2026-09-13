// /static/llm_control.js

document.addEventListener('DOMContentLoaded', () => {
    const llmInput = document.getElementById('llm-prompt-input');
    const llmSendBtn = document.getElementById('btn-send-llm-prompt');
    const llmOutput = document.getElementById('llm-command-output');
    console.log(llmSendBtn)
    let velocityInterval = null; // 用于存储速度指令的定时器

    // 获取当前选择的无人机ID
    function getSelectedClientId() {
        const selector = document.getElementById('client-selector');
        return selector ? selector.value : null;
    }

    // 执行从LLM解析出的指令
    function executeDroneCommand(commandString) {
        const clientId = getSelectedClientId();
        if (!clientId) {
            alert('请先选择一个无人机！');
            logMessage('错误：尝试执行AI指令但未选择无人机。');
            return;
        }

        const parts = commandString.trim().split(/\s+/);
        if (parts.length !== 6) {
            logMessage(`错误：AI返回的指令格式不正确: "${commandString}"`);
            return;
        }

        const [type, x, y, z, yaw, time] = parts;

        if (type === 'p') {
            // 执行位置指令
            logMessage(`AI指令(位置): X=${x}m, Y=${y}m, Z=${z}m, Yaw=${yaw}°`);
            // 调用在 combined_script.js 中定义的全局函数
            sendPositionCommand(clientId, x, y, z, yaw);

        } else if (type === 'v') {
            // 执行速度指令
            const duration = parseFloat(time) * 1000; // 转换为毫秒
            if (isNaN(duration) || duration <= 0) {
                logMessage(`错误：AI返回的速度指令持续时间无效: ${time}s`);
                return;
            }

            logMessage(`AI指令(速度): X=${x}, Y=${y}, Z=${z}, Yaw=${yaw}，持续 ${time} 秒`);

            // 如果已有速度指令在执行，先停止它
            if (velocityInterval) {
                clearInterval(velocityInterval);
            }

            // MSDK中，速度控制是通过虚拟摇杆实现的
            const left_stick_x = parseFloat(x);
            const left_stick_y = parseFloat(y);
            const right_stick_y = parseFloat(z); // 高度
            const right_stick_x = parseFloat(yaw); // 旋转

            // 每 100ms 发送一次速度指令
            velocityInterval = setInterval(() => {
                // 调用在 joysticks.js 中定义的全局函数
                sendVelocityCommand(clientId, left_stick_x, left_stick_y, right_stick_x, right_stick_y);
            }, 100);

            // 在指定时间后停止
            setTimeout(() => {
                clearInterval(velocityInterval);
                velocityInterval = null;
                // 发送零速指令以确保无人机停止
                sendVelocityCommand(clientId, 0, 0, 0, 0);
                logMessage(`AI速度指令执行完毕 (${time}秒)。`);
            }, duration);

        } else {
            logMessage(`错误：未知的AI指令类型: "${type}"`);
        }
    }


    llmSendBtn.addEventListener('click', async () => {
        const prompt = llmInput.value.trim();
        if (!prompt) {
            alert('请输入指令！');
            return;
        }
        console.log(prompt)
        // UI反馈
        llmSendBtn.disabled = true;
        llmSendBtn.textContent = '处理中...';
        llmOutput.textContent = '...';
        logMessage(`正在向AI发送指令: "${prompt}"`);

        try {
            const response = await fetch('/api/process-llm-command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: prompt })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error ${response.status}`);
            }

            const result = await response.json();
            const command = result.command;

            llmOutput.textContent = command;
            logMessage(`AI解析结果: ${command}`);

            // 执行指令
            executeDroneCommand(command);

        } catch (error) {
            console.error('LLM command failed:', error);
            logMessage(`AI指令处理失败: ${error.message}`);
            llmOutput.textContent = '错误！';
        } finally {
            llmSendBtn.disabled = false;
            llmSendBtn.textContent = '发送指令';
        }
    });

    // 允许按 Enter 键发送
    llmInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // 防止换行
            llmSendBtn.click();
        }
    });
});