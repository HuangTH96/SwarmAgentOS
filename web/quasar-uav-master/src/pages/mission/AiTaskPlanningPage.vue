<template>
  <q-page class="ai-task-planning-page">
    <div class="page-container">
      <!-- 左侧：对话区域 -->
      <div class="chat-section">
        <div class="chat-header">
          <div class="header-title">
            <q-icon name="smart_toy" size="28px" class="q-mr-sm" />
            <div>
              <div class="title-text">AI 任务规划助手</div>
              <div class="subtitle-text">通过对话方式规划无人机任务</div>
            </div>
          </div>
          <div class="header-actions">
            <q-btn
              flat
              round
              icon="add"
              @click="newConversation"
              size="sm"
              class="action-btn"
            >
              <q-tooltip>新建对话</q-tooltip>
            </q-btn>
            <q-btn
              flat
              round
              icon="list"
              @click="openMissionList"
              size="sm"
              class="action-btn"
            >
              <q-tooltip>任务列表</q-tooltip>
            </q-btn>
            <q-btn
              flat
              round
              icon="refresh"
              @click="clearChat"
              size="sm"
              class="action-btn"
            >
              <q-tooltip>清空对话</q-tooltip>
            </q-btn>
          </div>
        </div>

        <!-- 消息列表 -->
        <div class="messages-container" ref="messagesContainer">
          <div v-if="messages.length === 0" class="empty-state">
            <q-icon name="chat_bubble_outline" size="64px" color="grey-5" />
            <p class="empty-text">开始对话，规划您的无人机任务</p>
            <div class="example-prompts">
              <div class="example-title">示例提示：</div>
              <q-chip
                v-for="(example, idx) in examplePrompts"
                :key="idx"
                clickable
                @click="sendMessage(example)"
                color="primary"
                text-color="white"
                class="example-chip"
              >
                {{ example }}
              </q-chip>
            </div>
          </div>

          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message', msg.role]"
          >
            <div class="message-avatar">
              <q-icon
                :name="msg.role === 'user' ? 'person' : 'smart_toy'"
                size="24px"
              />
            </div>
            <div class="message-content">
              <div class="message-text">{{ msg.content }}</div>
              <div v-if="msg.taskPlan" class="task-plan-card">
                <div class="plan-header">
                  <q-icon name="task_alt" class="q-mr-xs" />
                  任务规划
                </div>
                <div class="plan-content">
                  <div v-for="(value, key) in msg.taskPlan" :key="key" class="plan-item">
                    <span class="plan-label">{{ formatFieldName(key) }}：</span>
                    <span class="plan-value">{{ formatFieldValue(value) }}</span>
                  </div>
                </div>
                <div class="plan-actions">
                  <q-btn
                    flat
                    dense
                    icon="map"
                    label="场景设置"
                    color="primary"
                    size="sm"
                    @click="goToSceneSetup(msg.taskPlan)"
                  />
                  <q-btn
                    flat
                    dense
                    icon="check_circle"
                    label="确认执行"
                    color="positive"
                    size="sm"
                    @click="confirmTask(msg.taskPlan)"
                  />
                  <q-btn
                    flat
                    dense
                    icon="edit"
                    label="修改"
                    color="primary"
                    size="sm"
                    @click="modifyTask(msg.taskPlan)"
                  />
                </div>
              </div>
              <div class="message-time">{{ msg.timestamp }}</div>
            </div>
          </div>

          <div v-if="isLoading" class="message assistant">
            <div class="message-avatar">
              <q-icon name="smart_toy" size="24px" />
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-section">
          <q-input
            v-model="userInput"
            placeholder="描述您的任务需求，例如：5架无人机从机场起飞，巡逻森林区域..."
            outlined
            dense
            autogrow
            :max-height="100"
            @keyup.enter.exact="handleSend"
            class="message-input"
          >
            <template v-slot:append>
              <q-btn
                round
                dense
                flat
                icon="send"
                @click="handleSend"
                :disable="!userInput.trim() || isLoading"
                color="primary"
              />
            </template>
          </q-input>
          <div class="input-hint">
            按 Enter 发送，Shift + Enter 换行
          </div>
        </div>
      </div>

      <!-- 右侧：任务预览 -->
      <div class="preview-section">
        <div class="preview-header">
          <q-icon name="preview" size="24px" class="q-mr-sm" />
          <span>当前任务预览</span>
        </div>
        <div class="preview-content">
          <div v-if="currentTask" class="current-task">
            <div class="task-summary">
              <div class="summary-item">
                <q-icon name="flight_takeoff" color="primary" />
                <div class="summary-text">
                  <div class="summary-label">任务类型</div>
                  <div class="summary-value">{{ currentTask.taskName || currentTask.taskType || '未命名任务' }}</div>
                </div>
              </div>
              <div class="summary-item">
                <q-icon name="precision_manufacturing" color="orange" />
                <div class="summary-text">
                  <div class="summary-label">无人机数量</div>
                  <div class="summary-value">{{ currentTask.droneCount || 1 }} 架</div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-md" />

            <div class="task-details">
              <div class="detail-title">任务详情</div>
              <div class="detail-list">
                <div v-for="(value, key) in currentTask" :key="key" class="detail-item-flex">
                  <span class="detail-label">{{ formatFieldName(key) }}</span>
                  <span class="detail-value">{{ formatFieldValue(value) }}</span>
                </div>
              </div>
            </div>

            <div class="task-json">
              <div class="json-header">
                <span>JSON 格式</span>
                <q-btn
                  flat
                  dense
                  size="sm"
                  icon="content_copy"
                  @click="copyJson"
                >
                  <q-tooltip>复制 JSON</q-tooltip>
                </q-btn>
              </div>
              <pre class="json-content">{{ JSON.stringify(currentTask, null, 2) }}</pre>
            </div>

            <div class="task-actions">
              <q-btn
                unelevated
                color="secondary"
                icon="map"
                label="场景设置"
                @click="goToSceneSetup(currentTask)"
                :disable="!currentTask"
                class="full-width q-mb-sm"
              />
              <q-btn
                unelevated
                color="primary"
                icon="save"
                label="保存任务"
                @click="saveMission"
                :disable="!currentTask || savingMission"
                :loading="savingMission"
                class="full-width"
              />
            </div>
          </div>

          <div v-else class="no-task">
            <q-icon name="assignment" size="80px" color="grey-4" />
            <p>暂无任务规划</p>
            <p class="hint-text">通过左侧对话创建任务</p>
          </div>
        </div>
      </div>
    </div>


    <!-- 任务列表对话框 -->
    <MissionListDialog
      v-model:show="showMissionList"
      :missions="missionStore.missionList"
      @select="loadMission"
      @edit="editMission"
      @delete="deleteMission"
    />
  </q-page>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useMissionStore } from 'src/stores/mission'
import MissionListDialog from 'src/components/mission/MissionListDialog.vue'

const $q = useQuasar()
const router = useRouter()
const missionStore = useMissionStore()

// 消息列表
const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const messagesContainer = ref(null)

// 当前任务
const currentTask = ref(null)

// 任务列表对话框
const showMissionList = ref(false)

// 保存任务状态
const savingMission = ref(false)

// 系统提示词 - 固定格式的 JSON 输出
const SYSTEM_PROMPT = `你是一个专业的无人机任务规划助手。你的职责是理解用户的任务需求，并生成标准格式的任务规划 JSON。

## 🔴 重要规则：每次回复都必须输出完整的 JSON
- **无论用户是新建任务还是修改任务，你都必须输出完整的 JSON 任务规划**
- 如果用户说"两架无人机"、"改成3架"、"增加一个途经点"等修改请求，你需要基于之前的任务，修改相应字段后，输出完整的新 JSON
- 如果用户只修改了部分参数（如无人机数量），其他参数保持不变，但仍需输出完整 JSON
- **绝对不能只回复文字而不输出 JSON**
- 每次回复格式：简短文字说明（1-2句话）+ 完整 JSON 代码块

## 南航将军路校区地点数据库
以下是校园内所有可用地点及其精确GPS坐标。当用户提到这些地点时，你必须使用这里的精确坐标：

1. 北门 - {"name": "北门", "lat": 31.942446, "lng": 118.787111}
2. 东门 - {"name": "东门", "lat": 31.938671, "lng": 118.798427}
3. 西门 - {"name": "西门", "lat": 31.936464, "lng": 118.787529}
4. 小西门 - {"name": "小西门", "lat": 31.940071, "lng": 118.785666}
5. D3教学楼 - {"name": "D3教学楼", "lat": 31.940205, "lng": 118.795526}
6. 图书馆 - {"name": "图书馆", "lat": 31.938286, "lng": 118.795804}
7. 艺术中心 - {"name": "艺术中心", "lat": 31.940198, "lng": 118.788242}
8. 西区4号楼 - {"name": "西区4号楼", "lat": 31.938507, "lng": 118.788696}
9. 长空学院 - {"name": "长空学院", "lat": 31.938559, "lng": 118.790231}
10. 民航学院 - {"name": "民航学院", "lat": 31.938228, "lng": 118.791379}
11. 1食堂 - {"name": "1食堂", "lat": 31.94149, "lng": 118.789772}
12. 3食堂 - {"name": "3食堂", "lat": 31.941553, "lng": 118.787709}
13. 西操场北 - {"name": "西操场北", "lat": 31.939528, "lng": 118.787028}
14. 西操场南 - {"name": "西操场南", "lat": 31.938571, "lng": 118.787312}
15. 东操场北 - {"name": "东操场北", "lat": 31.937075, "lng": 118.795035}
16. 东操场南 - {"name": "东操场南", "lat": 31.936084, "lng": 118.795119}
17. 足球场 - {"name": "足球场", "lat": 31.939285, "lng": 118.791511}
18. 国旗广场 - {"name": "国旗广场", "lat": 31.936995, "lng": 118.788825}
19. 砚湖 - {"name": "砚湖", "lat": 31.935931, "lng": 118.790298}
20. 御风园 - {"name": "御风园", "lat": 31.936193, "lng": 118.79247}

**地点匹配规则**：
- 用户说"北门"、"南航北门"、"将军路北门"都匹配"北门"
- 用户说"D3"、"D3教学楼"、"南航D3"都匹配"D3教学楼"
- 用户说"东门"、"南航东门"都匹配"东门"
- 支持模糊匹配，提取关键词后匹配上述地点

## 核心规则
1. 你必须始终以 JSON 格式输出任务规划
2. 在 JSON 之前，用自然语言简短回复用户（1-2句话）
3. JSON 必须包含在 \`\`\`json 和 \`\`\` 代码块中
4. **必需字段**: taskType（任务类型）、droneCount（无人机数量）、startPoint（起点对象）、destination（终点对象）
5. **可选字段**: waypoints（途经点对象数组）
6. **地点格式**: 如果地点在上述数据库中，必须输出 {"name": "地点名", "lat": 纬度, "lng": 经度}
7. **地点格式**: 如果地点不在数据库中，只输出 {"name": "地点名"}，不要编造坐标

## 标准 JSON 格式（必须严格遵守）
\`\`\`json
{
  "taskType": "任务类型（中文）",
  "droneCount": 数字,
  "startPoint": {"name": "起点名", "lat": 纬度, "lng": 经度},
  "waypoints": [{"name": "途经点1", "lat": 纬度, "lng": 经度}],  // 可选
  "destination": {"name": "终点名", "lat": 纬度, "lng": 经度}
}
\`\`\`

**重要说明**：
- startPoint 和 destination 是必需的，必须是对象格式
- waypoints 是可选的，如果有途经点才添加，必须是对象数组
- 如果地点在数据库中，必须包含精确的 lat 和 lng
- 如果地点不在数据库中，只包含 name 字段
- 绝对不要编造或估算坐标

## 任务类型示例

### 1. 校园巡逻任务
\`\`\`json
{
  "taskType": "巡逻任务",
  "droneCount": 1,
  "startPoint": {"name": "北门", "lat": 31.942446, "lng": 118.787111},
  "waypoints": [{"name": "D3教学楼", "lat": 31.940205, "lng": 118.795526}],
  "destination": {"name": "东门", "lat": 31.938671, "lng": 118.798427}
}
\`\`\`

### 2. 多点巡逻
\`\`\`json
{
  "taskType": "巡逻任务",
  "droneCount": 2,
  "startPoint": {"name": "西门", "lat": 31.936464, "lng": 118.787529},
  "waypoints": [
    {"name": "图书馆", "lat": 31.938286, "lng": 118.795804},
    {"name": "足球场", "lat": 31.939285, "lng": 118.791511}
  ],
  "destination": {"name": "西门", "lat": 31.936464, "lng": 118.787529}
}
\`\`\`

### 3. 配送任务
\`\`\`json
{
  "taskType": "配送任务",
  "droneCount": 1,
  "startPoint": {"name": "1食堂", "lat": 31.94149, "lng": 118.789772},
  "destination": {"name": "图书馆", "lat": 31.938286, "lng": 118.795804}
}
\`\`\`

## 对话示例

用户: "从南航北门到南航东门，执行巡逻任务，一架无人机，中间需要经过南航D3教学楼"
助手: 已为您规划好南航校园巡逻任务，无人机将按北门→D3教学楼→东门的路线执行巡逻。

\`\`\`json
{
  "taskType": "巡逻任务",
  "droneCount": 1,
  "startPoint": {"name": "北门", "lat": 31.942446, "lng": 118.787111},
  "waypoints": [{"name": "D3教学楼", "lat": 31.940205, "lng": 118.795526}],
  "destination": {"name": "东门", "lat": 31.938671, "lng": 118.798427}
}
\`\`\`

用户: "1架无人机从图书馆到西门"
助手: 好的，我为您规划了从图书馆到西门的任务。

\`\`\`json
{
  "taskType": "巡逻任务",
  "droneCount": 1,
  "startPoint": {"name": "图书馆", "lat": 31.938286, "lng": 118.795804},
  "destination": {"name": "西门", "lat": 31.936464, "lng": 118.787529}
}
\`\`\`

## 重要提醒
- taskType 必须是中文（如"巡逻任务"、"侦察任务"、"配送任务"、"搜索救援任务"等）
- 必须使用数据库中的精确坐标，不要修改或估算
- waypoints 是可选的，如果用户没有提到途经点就不要添加
- 保持 JSON 格式正确，可被 JSON.parse() 解析
- startPoint、waypoints、destination 必须是对象格式，不能是字符串`

// 示例提示
const examplePrompts = [
  '5架无人机巡逻森林',
  '从机场到目标点',
  '3架无人机协同搜索'
]

onMounted(() => {
  // 加载 AI API 配置
  loadAiApiConfig()
  
  // 从 store 加载当前任务
  missionStore.loadFromLocalStorage()
  if (missionStore.currentMission) {
    currentTask.value = missionStore.currentMission
  }
  
  // 加载对话历史
  if (missionStore.currentMission?.mission_id) {
    // 如果有任务 ID，加载该任务的对话历史
    loadMissionConversations(missionStore.currentMission.mission_id)
  } else {
    // 否则加载通用对话历史
    loadConversationHistory()
  }
})

// 加载 AI API 配置
async function loadAiApiConfig() {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      $q.notify({
        type: 'warning',
        message: '请先登录后配置 AI API',
        position: 'top'
      })
      return
    }
    
    const response = await fetch('/api/ai-config', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      
      // 保存到 localStorage 作为缓存
      if (data.ai_api_provider) {
        localStorage.setItem('ai_api_provider', data.ai_api_provider)
      }
      if (data.ai_api_key) {
        localStorage.setItem('ai_api_key', data.ai_api_key)
      }
      if (data.ai_api_endpoint) {
        localStorage.setItem('ai_api_endpoint', data.ai_api_endpoint)
      }
      
      // 检查是否已配置
      if (!data.ai_api_key) {
        $q.notify({
          type: 'warning',
          message: '请先在设置页面配置 AI API',
          position: 'top',
          actions: [
            {
              label: '去设置',
              color: 'white',
              handler: () => {
                window.location.href = '/#/settings'
              }
            }
          ]
        })
      }
    }
  } catch (error) {
    console.error('加载 AI 配置失败:', error)
  }
}

// 加载对话历史记录
async function loadConversationHistory() {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) return
    
    const response = await fetch('/api/ai-task-conversations', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      messages.value = data.messages || []
      missionStore.setCurrentConversations(messages.value)
      
      // 恢复最后一个任务规划
      const lastAssistantMessage = messages.value
        .filter(msg => msg.role === 'assistant' && msg.taskPlan)
        .pop()
      
      if (lastAssistantMessage) {
        currentTask.value = lastAssistantMessage.taskPlan
      }
      
      scrollToBottom()
    }
  } catch (error) {
    console.error('加载对话历史失败:', error)
  }
}

// 加载任务的对话历史
async function loadMissionConversations(missionId) {
  try {
    const conversations = await missionStore.loadMissionConversations(missionId)
    messages.value = conversations
    
    // 恢复最后一个任务规划
    const lastAssistantMessage = messages.value
      .filter(msg => msg.role === 'assistant' && msg.taskPlan)
      .pop()
    
    if (lastAssistantMessage) {
      currentTask.value = lastAssistantMessage.taskPlan
    }
    
    scrollToBottom()
  } catch (error) {
    console.error('加载任务对话历史失败:', error)
  }
}

// 保存消息到数据库
async function saveMessageToDb(message) {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) return
    
    // 如果当前有任务 ID，关联到消息
    const messageData = {
      ...message,
      mission_id: missionStore.currentMission?.mission_id
    }
    
    const response = await fetch('/api/ai-task-conversations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(messageData)
    })
    
    if (response.ok) {
      const data = await response.json()
      // 更新消息 ID
      message.id = data.id
      // 添加到 store
      missionStore.addConversation(message)
    }
  } catch (error) {
    console.error('保存消息失败:', error)
  }
}

// 发送消息
async function handleSend() {
  if (!userInput.value.trim() || isLoading.value) return
  
  const message = userInput.value.trim()
  userInput.value = ''
  
  await sendMessage(message)
}

async function sendMessage(message) {
  // 添加用户消息
  const userMessage = {
    role: 'user',
    content: message,
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  messages.value.push(userMessage)
  
  // 保存用户消息到数据库
  await saveMessageToDb(userMessage)
  
  scrollToBottom()
  isLoading.value = true
  
  try {
    // 调用 AI API
    const response = await callAiApi(message)
    
    // 添加 AI 回复
    const assistantMessage = {
      role: 'assistant',
      content: response.text,
      taskPlan: response.taskPlan,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    messages.value.push(assistantMessage)
    
    // 保存 AI 回复到数据库
    await saveMessageToDb(assistantMessage)
    
    // 更新当前任务
    if (response.taskPlan) {
      currentTask.value = response.taskPlan
    }
    
    scrollToBottom()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: '调用 AI API 失败: ' + error.message,
      position: 'top'
    })
  } finally {
    isLoading.value = false
  }
}

// 调用 AI API
async function callAiApi(message) {
  // 从 localStorage 读取 API 配置
  const apiKey = localStorage.getItem('ai_api_key')
  const apiProvider = localStorage.getItem('ai_api_provider') || 'OpenAI'
  const apiEndpoint = localStorage.getItem('ai_api_endpoint')
  
  if (!apiKey) {
    throw new Error('请先在设置页面配置 AI API Key')
  }
  
  // 构建对话历史
  const conversationHistory = messages.value.map(msg => ({
    role: msg.role,
    content: msg.content
  }))
  
  // 在用户消息后添加隐藏的强制JSON输出后缀
  const messageWithSuffix = message + '\n\n[重要提醒：请务必按照系统提示的格式输出完整的JSON任务规划，包含在```json代码块中]'
  
  // 添加当前消息（带后缀）
  conversationHistory.push({
    role: 'user',
    content: messageWithSuffix
  })
  
  // 调用 AI API
  try {
    const endpoint = getApiEndpoint(apiProvider, apiEndpoint)
    const requestBody = buildRequestBody(apiProvider, conversationHistory)
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify(requestBody)
    })
    
    if (!response.ok) {
      throw new Error(`API 调用失败: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    const aiResponse = extractResponse(apiProvider, data)
    
    // 解析 AI 响应，提取 JSON
    let { text, taskPlan } = parseAiResponse(aiResponse)
    
    // 如果有任务规划，调用后端增强坐标
    if (taskPlan) {
      taskPlan = await enhanceTaskPlanCoordinates(taskPlan, conversationHistory)
    }
    
    return { text, taskPlan }
  } catch (error) {
    console.error('AI API 调用错误:', error)
    throw error
  }
}

// 获取 API 端点
function getApiEndpoint(provider, customEndpoint) {
  if (customEndpoint) return customEndpoint
  
  const endpoints = {
    'OpenAI': 'https://api.openai.com/v1/chat/completions',
    'Azure OpenAI': customEndpoint, // Azure 必须提供自定义端点
    '通义千问': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
    '文心一言': 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions',
    '智谱AI': 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
  }
  
  return endpoints[provider] || endpoints['OpenAI']
}

// 构建请求体
function buildRequestBody(provider, conversationHistory) {
  const baseRequest = {
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      ...conversationHistory
    ],
    temperature: 0.7
  }
  
  // 不同提供商的模型名称
  const models = {
    'OpenAI': 'gpt-3.5-turbo',
    '通义千问': 'qwen-turbo',
    '文心一言': 'ERNIE-Bot-turbo',
    '智谱AI': 'glm-3-turbo'
  }
  
  return {
    ...baseRequest,
    model: models[provider] || 'gpt-3.5-turbo'
  }
}

// 提取响应内容
function extractResponse(provider, data) {
  if (provider === '通义千问') {
    return data.output?.text || ''
  } else if (provider === '文心一言') {
    return data.result || ''
  } else {
    return data.choices?.[0]?.message?.content || ''
  }
}

// 解析 AI 响应，提取文本和 JSON
function parseAiResponse(aiResponse) {
  // 提取 JSON 代码块
  const jsonMatch = aiResponse.match(/```json\s*([\s\S]*?)\s*```/)
  
  let taskPlan = null
  let text = aiResponse
  
  if (jsonMatch) {
    try {
      taskPlan = JSON.parse(jsonMatch[1])
      // 移除 JSON 部分，只保留文本
      text = aiResponse.replace(/```json[\s\S]*?```/, '').trim()
      
      // 验证并规范化地点格式
      if (taskPlan) {
        // 确保 startPoint 是对象格式
        if (typeof taskPlan.startPoint === 'string') {
          taskPlan.startPoint = { name: taskPlan.startPoint }
        }
        
        // 确保 destination 是对象格式
        if (typeof taskPlan.destination === 'string') {
          taskPlan.destination = { name: taskPlan.destination }
        }
        
        // 确保 waypoints 是对象数组格式
        if (taskPlan.waypoints && Array.isArray(taskPlan.waypoints)) {
          taskPlan.waypoints = taskPlan.waypoints.map(wp => {
            if (typeof wp === 'string') {
              return { name: wp }
            }
            return wp
          })
        }
        
        // 保存到 store
        missionStore.setCurrentMission(taskPlan)
      }
    } catch (error) {
      console.error('JSON 解析失败:', error)
    }
  }
  
  return { text, taskPlan }
}

// 增强任务规划坐标（仅处理没有坐标的地点）
async function enhanceTaskPlanCoordinates(taskPlan, conversationHistory) {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      console.warn('No auth token, skipping coordinate enhancement')
      return taskPlan
    }
    
    // 检查是否有需要增强的地点（没有坐标的地点）
    let needsEnhancement = false
    
    if (taskPlan.startPoint && !taskPlan.startPoint.lat) {
      needsEnhancement = true
    }
    if (taskPlan.destination && !taskPlan.destination.lat) {
      needsEnhancement = true
    }
    if (taskPlan.waypoints && Array.isArray(taskPlan.waypoints)) {
      for (const wp of taskPlan.waypoints) {
        if (wp && !wp.lat) {
          needsEnhancement = true
          break
        }
      }
    }
    
    // 如果所有地点都有坐标，直接返回
    if (!needsEnhancement) {
      console.log('All locations have coordinates, skipping enhancement')
      return taskPlan
    }
    
    // 构建对话上下文
    const context = conversationHistory
      .map(msg => msg.content)
      .join('\n')
    
    console.log('Enhancing task plan coordinates for locations without coordinates...')
    
    const response = await fetch('/api/enhance-task-plan-coordinates', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        task_plan: taskPlan,
        conversation_context: context
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        console.log('Task plan coordinates enhanced successfully')
        return data.task_plan
      } else {
        console.warn('Coordinate enhancement failed:', data.error)
      }
    }
    
    // 失败时返回原始任务规划
    return taskPlan
  } catch (error) {
    console.error('增强任务规划坐标失败:', error)
    return taskPlan
  }
}


// 确认任务
function confirmTask(task) {
  $q.dialog({
    title: '确认执行任务',
    message: `确定要执行此任务吗？\n无人机数量：${task.droneCount}架\n任务：${task.description}`,
    cancel: true,
    persistent: true
  }).onOk(() => {
    $q.notify({
      type: 'positive',
      message: '任务已下发，无人机准备执行',
      position: 'top'
    })
  })
}

// 进入场景设置
function goToSceneSetup(task) {
  // 确保任务数据在 store 中
  missionStore.setCurrentMission(task)
  
  // 跳转到场景设置页面
  router.push('/mission/scene')
  
  $q.notify({
    type: 'info',
    message: '正在进入场景设置页面...',
    position: 'top'
  })
}

// 提取起点
function extractStartPoint(task) {
  // 优先使用 startPoint 字段（新格式）
  if (task.startPoint) {
    // 如果是对象格式（包含坐标）
    if (typeof task.startPoint === 'object' && task.startPoint.name) {
      return {
        lat: task.startPoint.lat,
        lng: task.startPoint.lng,
        name: task.startPoint.name
      }
    }
    // 如果是字符串格式（只有名称）
    if (typeof task.startPoint === 'string') {
      return { name: task.startPoint }
    }
  }
  
  // 兼容旧格式
  if (task.route?.from) {
    return { name: task.route.from }
  }
  if (task.route?.startPoint) {
    return { name: task.route.startPoint }
  }
  
  return null
}

// 提取终点
function extractEndPoint(task) {
  // 优先使用 destination 字段（新格式）
  if (task.destination) {
    // 如果是对象格式（包含坐标）
    if (typeof task.destination === 'object' && task.destination.name) {
      return {
        lat: task.destination.lat,
        lng: task.destination.lng,
        name: task.destination.name
      }
    }
    // 如果是字符串格式（只有名称）
    if (typeof task.destination === 'string') {
      return { name: task.destination }
    }
  }
  
  // 兼容旧格式
  if (task.targetPoint) {
    return { name: task.targetPoint }
  }
  if (task.route?.to) {
    return { name: task.route.to }
  }
  if (task.route?.destination) {
    return { name: task.route.destination }
  }
  
  return null
}

// 转换任务类型
function getMissionType(taskType) {
  const typeMap = {
    '巡逻任务': 'patrol',
    '侦察任务': 'patrol',
    '运输任务': 'delivery',
    '配送任务': 'delivery',
    '搜索救援任务': 'inspection',
    '巡检任务': 'inspection',
    '编队表演任务': 'patrol'
  }
  return typeMap[taskType] || 'patrol'
}

// 修改任务
function modifyTask(task) {
  userInput.value = `修改任务：${task.description}，`
}

// 清空对话
function clearChat() {
  $q.dialog({
    title: '确认清空',
    message: '确定要清空当前对话并开始新任务吗？',
    cancel: true
  }).onOk(async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const currentMissionId = missionStore.currentMission?.mission_id
      
      if (token && currentMissionId) {
        // 如果有当前任务，只删除该任务的对话记录
        await fetch(`/api/ai-task-conversations/mission/${currentMissionId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      } else if (token) {
        // 如果没有任务ID，清空所有对话记录（兼容旧逻辑）
        await fetch('/api/ai-task-conversations', {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      }
      
      // 清空界面状态
      messages.value = []
      currentTask.value = null
      
      // 清空当前任务和对话
      missionStore.clearCurrentMission()
      
      $q.notify({
        type: 'positive',
        message: '对话已清空，可以开始新任务',
        position: 'top'
      })
    } catch (error) {
      console.error('清空对话记录失败:', error)
      $q.notify({
        type: 'negative',
        message: '清空对话记录失败',
        position: 'top'
      })
    }
  })
}

// 新建对话
function newConversation() {
  if (messages.value.length > 0) {
    $q.dialog({
      title: '新建对话',
      message: '当前对话将被保存，确定要开始新对话吗？',
      cancel: true
    }).onOk(() => {
      // 清空界面状态，开始新对话
      messages.value = []
      currentTask.value = null
      
      // 清空当前任务
      missionStore.clearCurrentMission()
      
      $q.notify({
        type: 'positive',
        message: '已开始新对话',
        position: 'top'
      })
    })
  } else {
    // 如果当前没有对话，直接清空状态
    messages.value = []
    currentTask.value = null
    missionStore.clearCurrentMission()
    
    $q.notify({
      type: 'info',
      message: '已准备好新对话',
      position: 'top'
    })
  }
}

// 打开任务列表
async function openMissionList() {
  try {
    await missionStore.loadMissionList()
    showMissionList.value = true
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: '加载任务列表失败: ' + error.message
    })
  }
}

// 加载任务
async function loadMission(missionId) {
  try {
    // 加载任务详情和对话历史
    const mission = await missionStore.loadMissionDetail(missionId)
    currentTask.value = mission
    
    // 切换对话历史
    messages.value = missionStore.currentConversations
    
    showMissionList.value = false
    
    scrollToBottom()
    
    $q.notify({
      type: 'positive',
      message: '任务已加载'
    })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: '加载任务失败: ' + error.message
    })
  }
}

// 编辑任务
function editMission(missionId) {
  showMissionList.value = false
  router.push({
    name: 'scene-setup',
    query: { missionId: missionId }
  })
}

// 删除任务
async function deleteMission(missionId) {
  try {
    await missionStore.deleteMission(missionId)
    $q.notify({
      type: 'positive',
      message: '任务已删除'
    })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: '删除任务失败: ' + error.message
    })
  }
}

// 复制 JSON
function copyJson() {
  if (!currentTask.value) return
  
  navigator.clipboard.writeText(JSON.stringify(currentTask.value, null, 2))
  $q.notify({
    type: 'positive',
    message: 'JSON 已复制到剪贴板',
    position: 'top'
  })
}

// 保存任务
async function saveMission() {
  if (!currentTask.value) {
    $q.notify({
      type: 'warning',
      message: '没有可保存的任务'
    })
    return
  }

  savingMission.value = true

  try {
    // 构建保存数据
    const missionData = {
      name: currentTask.value.taskName || currentTask.value.taskType || '未命名任务',
      num_uavs: currentTask.value.droneCount || 1,
      mission_type: getMissionType(currentTask.value.taskType),
      start_point: extractStartPoint(currentTask.value),
      end_point: extractEndPoint(currentTask.value),
      task_data: currentTask.value
    }

    // 保存到数据库
    const result = await missionStore.saveMissionToDatabase(missionData)
    
    // 关联对话历史到任务
    if (result.mission_id && messages.value.length > 0) {
      try {
        await missionStore.associateConversationsWithMission(result.mission_id)
      } catch (error) {
        console.error('关联对话历史失败:', error)
        // 不影响主流程，只记录错误
      }
    }

    $q.notify({
      type: 'positive',
      message: '任务保存成功',
      actions: [
        {
          label: '场景设置',
          color: 'white',
          handler: () => {
            goToSceneSetup(currentTask.value)
          }
        }
      ]
    })
  } catch (error) {
    console.error('保存任务失败:', error)
    $q.notify({
      type: 'negative',
      message: '保存任务失败: ' + (error.message || '未知错误')
    })
  } finally {
    savingMission.value = false
  }
}



// 滚动到底部
async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 格式化字段名称（驼峰转中文）
function formatFieldName(key) {
  const fieldNames = {
    taskType: '任务类型',
    taskName: '任务名称',
    droneCount: '无人机数量',
    startPoint: '起始点',
    destination: '目的地',
    waypoints: '途经点',
    targetPoint: '目标点',
    patrolArea: '巡逻区域',
    searchArea: '搜索区域',
    flightParams: '飞行参数',
    altitude: '飞行高度',
    speed: '飞行速度',
    duration: '持续时间',
    formation: '编队方式',
    route: '路线',
    cargo: '货物',
    priority: '优先级',
    estimatedTime: '预计时间',
    searchPattern: '搜索模式',
    equipment: '设备',
    teamDivision: '团队分工',
    target: '目标',
    sensors: '传感器',
    flightMode: '飞行模式',
    reportInterval: '报告间隔',
    venue: '场地',
    performanceTime: '表演时间',
    lightColors: '灯光颜色',
    music: '音乐',
    nightVision: '夜视',
    from: '起点',
    to: '终点',
    distance: '距离',
    type: '类型',
    weight: '重量',
    name: '名称',
    radius: '半径',
    center: '中心',
    size: '大小',
    coordinates: '坐标',
    location: '位置',
    length: '长度'
  }
  return fieldNames[key] || key
}

// 格式化字段值
function formatFieldValue(value) {
  if (value === null || value === undefined) {
    return '未设置'
  }
  if (typeof value === 'object') {
    if (Array.isArray(value)) {
      // 如果是地点对象数组，格式化显示
      if (value.length > 0 && value[0].name) {
        return value.map(item => {
          if (item.lat && item.lng) {
            return `${item.name} (${item.lat.toFixed(6)}, ${item.lng.toFixed(6)})`
          }
          return item.name
        }).join(', ')
      }
      return value.join(', ')
    }
    // 如果是地点对象，格式化显示
    if (value.name) {
      if (value.lat && value.lng) {
        return `${value.name} (${value.lat.toFixed(6)}, ${value.lng.toFixed(6)})`
      }
      return value.name
    }
    return JSON.stringify(value, null, 2)
  }
  return value
}
</script>

<style scoped lang="scss">
.ai-task-planning-page {
  height: 100%;
  padding: 0;
}

.page-container {
  display: flex;
  height: 100%;
  gap: 16px;
  padding: 16px;
}

// 左侧对话区域
.chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  height: 100%;
  max-height: calc(100vh - 32px); // 减去 padding
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e0e0e0;
  background: #4a90e2;
  color: white;
  flex-shrink: 0; // 防止头部被压缩
}

.header-title {
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  color: white;
}

.title-text {
  font-size: 20px;
  font-weight: 600;
}

.subtitle-text {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 2px;
}

// 消息容器
.messages-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px;
  background: #f8f9fa;
  min-height: 0; // 允许 flex 子元素缩小
  
  // 自定义滚动条样式
  &::-webkit-scrollbar {
    width: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
    
    &:hover {
      background: #a8a8a8;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.empty-text {
  margin-top: 16px;
  font-size: 16px;
}

.example-prompts {
  margin-top: 24px;
  text-align: center;
}

.example-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.example-chip {
  margin: 4px;
}

// 消息样式
.message {
  display: flex;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-right: 12px;
}

.message.user .message-avatar {
  background: #667eea;
  color: white;
}

.message.assistant .message-avatar {
  background: #f0f0f0;
  color: #666;
}

.message-content {
  flex: 1;
  max-width: 70%;
}

.message.user .message-content {
  margin-left: auto;
  margin-right: 0;
}

.message-text {
  background: white;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message.user .message-text {
  background: #667eea;
  color: white;
}

.message-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
  padding: 0 4px;
}

// 任务规划卡片
.task-plan-card {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-top: 12px;
}

.plan-header {
  font-weight: 600;
  font-size: 15px;
  color: #333;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.plan-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-item {
  display: flex;
  font-size: 14px;
}

.plan-label {
  font-weight: 500;
  color: #666;
  min-width: 100px;
}

.plan-value {
  color: #333;
}

.plan-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e0e0e0;
}

// 输入区域
.input-section {
  padding: 16px 24px;
  border-top: 1px solid #e0e0e0;
  background: white;
  flex-shrink: 0; // 防止输入框被压缩
  position: relative;
  z-index: 1;
}

.message-input {
  :deep(.q-field__control) {
    border-radius: 24px;
  }
}

.input-hint {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
  text-align: center;
}

// 打字指示器
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-10px);
  }
}

// 右侧预览区域
.preview-section {
  width: 400px;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e0e0e0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.preview-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.current-task {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.task-summary {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.summary-text {
  flex: 1;
}

.summary-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.summary-value {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.task-details {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item-flex {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-item-flex:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 12px;
  color: #999;
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.task-json {
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}

.json-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2d2d2d;
  color: white;
  font-size: 13px;
  font-weight: 500;
}

.json-content {
  padding: 16px;
  margin: 0;
  color: #d4d4d4;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  overflow-x: auto;
}

.task-actions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
}

.no-task {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.no-task p {
  margin-top: 16px;
  font-size: 16px;
}

.hint-text {
  font-size: 14px;
  color: #bbb;
}
</style>

