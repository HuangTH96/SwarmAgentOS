<template>
  <q-card class="llm-control-card" flat bordered>
    <q-card-section>
      <div class="text-h6">自然语言指令 (AI)</div>
    </q-card-section>

    <q-card-section class="q-pt-none">
      <q-input
        v-model="llmPrompt"
        filled
        type="textarea"
        rows="3"
        placeholder="例如：向前飞10米，或点击右侧麦克风说话"
        @keydown.enter.prevent="sendLlmCommand"
      >
        <!-- 新增：语音输入按钮 -->
        <template v-slot:append>
          <q-btn
            round
            dense
            flat
            :icon="isListening ? 'mic_off' : 'mic'"
            :color="isListening ? 'negative' : 'grey'"
            :loading="isListening"
            :disable="isProcessing"
            @click="toggleVoiceInput"
            aria-label="语音输入"
          >
            <q-tooltip>
              {{ isListening ? '停止录音' : '开始语音输入' }}
            </q-tooltip>
          </q-btn>
        </template>
      </q-input>
    </q-card-section>

    <q-card-actions align="between" class="q-px-md q-pb-md">
      <div class="llm-status row items-center">
        <span>解析结果: </span>
        <code class="q-ml-sm">{{ llmOutput }}</code>
      </div>
      <q-btn
        label="发送指令"
        color="primary"
        unelevated
        :loading="isProcessing"
        :disable="isProcessing || !llmPrompt"
        @click="sendLlmCommand"
      >
        <template v-slot:loading>
          <q-spinner-dots />
        </template>
      </q-btn>
    </q-card-actions>
  </q-card>
</template>

<script setup>
import { ref, onUnmounted, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { useDroneStore } from 'stores/drone';

// --- Quasar and Pinia Setup ---
const $q = useQuasar();
const droneStore = useDroneStore();
const { sendPosition, sendJoystickData } = droneStore;

// --- Component State ---
const llmPrompt = ref('');
const llmOutput = ref('等待输入...');
const isProcessing = ref(false);

// 语音识别相关的状态
const isListening = ref(false);
const speechRecognitionSupported = ref(false);
let recognition = null;

// 用于存储速度指令的定时器ID
let velocityInterval = null;

// --- 语音识别逻辑 (Web Speech API) ---

/**
 * 设置并初始化语音识别
 */
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    speechRecognitionSupported.value = true;
    recognition = new SpeechRecognition();
    recognition.lang = 'zh-CN';
    recognition.continuous = false;
    recognition.interimResults = true;

    // 当有识别结果时触发
    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      llmPrompt.value = transcript; // 实时更新输入框内容

      // 修改点 1: 当这是最终结果时，不再自动发送指令
      if (event.results[0].isFinal) {
        isListening.value = false;
        llmOutput.value = '等待发送...'; // 更新状态提示
        $q.notify({
          type: 'info',
          icon: 'check_circle_outline',
          message: '语音识别完成，请确认后发送。'
        });
      }
    };

    // 当识别结束时触发
    recognition.onend = () => {
      // 确保即使没有最终结果，监听状态也能被重置
      if (isListening.value) {
        isListening.value = false;
        // 如果输入框为空，说明可能没识别到内容
        if (!llmPrompt.value.trim()) {
            llmOutput.value = '等待输入...';
        }
      }
    };

    // 处理错误
    recognition.onerror = (event) => {
      let errorMessage = '语音识别发生错误';
      if (event.error === 'no-speech') {
        errorMessage = '未检测到语音，请重试。';
      } else if (event.error === 'not-allowed') {
        errorMessage = '麦克风权限被拒绝，请在浏览器设置中允许访问。';
      }
      $q.notify({ type: 'negative', message: errorMessage });
      isListening.value = false;
      llmOutput.value = '等待输入...';
    };
  } else {
    speechRecognitionSupported.value = false;
    $q.notify({ type: 'warning', message: '您的浏览器不支持语音识别功能。' });
  }
}

/**
 * 切换语音输入的开始/停止状态
 */
function toggleVoiceInput() {
  if (!speechRecognitionSupported.value) {
    $q.notify({ type: 'negative', message: '抱歉，语音识别功能不可用。' });
    return;
  }
  if (isListening.value) {
    recognition.stop();
    isListening.value = false;
  } else {
    llmPrompt.value = ''; // 开始前清空输入框
    llmOutput.value = '聆听中...';
    recognition.start();
    isListening.value = true;
  }
}

// --- Core Logic (与之前相同) ---

/**
 * 执行从LLM解析出的无人机指令
 * (此函数无任何改动)
 */
function executeDroneCommand(commandString) {
  // ... (此部分代码保持原样)
  if (velocityInterval) {
    clearInterval(velocityInterval);
    velocityInterval = null;
    sendJoystickData({ left_stick_x: 0, left_stick_y: 0, right_stick_x: 0, right_stick_y: 0 });
    $q.notify({ type: 'info', message: '已停止之前的速度指令。' });
  }

  const parts = commandString.trim().split(/\s+/);
  if (parts.length !== 6) {
    const errorMsg = `AI返回的指令格式不正确: "${commandString}"`;
    $q.notify({ type: 'negative', message: errorMsg });
    console.error(errorMsg);
    return;
  }

  const [type, xStr, yStr, zStr, yawStr, timeStr] = parts;
  const x = parseFloat(xStr);
  const y = parseFloat(yStr);
  const z = parseFloat(zStr);
  const yaw = parseFloat(yawStr);
  const time = parseFloat(timeStr);

  if (type === 'p') {
    $q.notify({
      type: 'positive',
      icon: 'flight_takeoff',
      message: `执行位置指令: X=${x}m, Y=${y}m, Z=${z}m, Yaw=${yaw}°`
    });
    sendPosition({ x, y, z, yaw });
  } else if (type === 'v') {
    const duration = time * 1000;
    if (isNaN(duration) || duration <= 0) {
      const errorMsg = `AI返回的速度指令持续时间无效: ${time}s`;
      $q.notify({ type: 'negative', message: errorMsg });
      console.error(errorMsg);
      return;
    }

    $q.notify({
      type: 'positive',
      icon: 'fast_forward',
      message: `执行速度指令: Vx=${x}, Vy=${y}, Vz=${z}, Vw=${yaw}，持续 ${time} 秒`
    });

    const joystickPayload = {
      left_stick_x: y,
      left_stick_y: x,
      right_stick_x: yaw,
      right_stick_y: z
    };

    velocityInterval = setInterval(() => {
      sendJoystickData(joystickPayload);
    }, 100);

    setTimeout(() => {
      if (velocityInterval) {
        clearInterval(velocityInterval);
        velocityInterval = null;
        sendJoystickData({ left_stick_x: 0, left_stick_y: 0, right_stick_x: 0, right_stick_y: 0 });
        $q.notify({
          type: 'info',
          icon: 'check_circle',
          message: `AI速度指令执行完毕 (${time}秒)。`
        });
      }
    }, duration);
  } else {
    const errorMsg = `未知的AI指令类型: "${type}"`;
    $q.notify({ type: 'negative', message: errorMsg });
    console.error(errorMsg);
  }
}

/**
 * 发送自然语言指令到后端API
 * (修改点 2: 简化了此处的逻辑)
 */
async function sendLlmCommand() {
  const prompt = llmPrompt.value.trim();
  if (!prompt) {
    $q.notify({ type: 'warning', message: '请输入或说出指令！' });
    return;
  }

  isProcessing.value = true;
  llmOutput.value = '处理中...';

  try {
    const response = await fetch('/api/process-llm-command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error ${response.status}`);
    }

    const result = await response.json();
    const command = result.command;

    llmOutput.value = command;
    $q.notify({ type: 'info', message: `AI解析成功: ${command}` });
    executeDroneCommand(command);

  } catch (error) {
    console.error('LLM command failed:', error);
    llmOutput.value = '错误！';
    $q.notify({ type: 'negative', message: `AI指令处理失败: ${error.message}` });
  } finally {
    isProcessing.value = false;
  }
}

// --- Lifecycle Hooks ---
// (此部分无任何改动)
onMounted(() => {
  setupSpeechRecognition();
});

onUnmounted(() => {
  if (velocityInterval) {
    clearInterval(velocityInterval);
    velocityInterval = null;
    sendJoystickData({ left_stick_x: 0, left_stick_y: 0, right_stick_x: 0, right_stick_y: 0 });
    console.log('LLM control component unmounted, velocity interval cleared.');
  }
  if (recognition && isListening.value) {
    recognition.abort();
    console.log('LLM control component unmounted, speech recognition aborted.');
  }
});
</script>

<style scoped>
.llm-control-card {
  max-width: 500px;
  margin: auto;
}

.llm-status {
  color: #666;
  font-size: 0.9em;
}

.llm-status code {
  background-color: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
  color: #333;
  font-weight: bold;
}
</style>
