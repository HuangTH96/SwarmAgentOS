<template>
  <q-page class="settings-page q-pa-md">
    <div class="page-header q-mb-lg">
      <div class="text-h4 text-weight-bold">系统设置</div>
      <div class="text-caption text-grey-7">配置系统参数和个人偏好</div>
    </div>

    <div class="settings-container">
      <!-- 用户信息卡片 -->
      <q-card class="settings-card q-mb-md">
        <q-card-section>
          <div class="text-h6 q-mb-md">
            <q-icon name="account_circle" class="q-mr-sm" />
            用户信息
          </div>
          <q-separator class="q-mb-md" />
          
          <div class="info-row">
            <span class="info-label">用户名：</span>
            <span class="info-value">{{ authStore.user?.username || '未登录' }}</span>
          </div>
          
          <div class="info-row">
            <span class="info-label">登录状态：</span>
            <q-badge :color="authStore.isAuthenticated ? 'positive' : 'negative'">
              {{ authStore.isAuthenticated ? '已登录' : '未登录' }}
            </q-badge>
          </div>
          
          <div class="info-row">
            <span class="info-label">Token：</span>
            <span class="info-value token-text">{{ authStore.token ? authStore.token.substring(0, 20) + '...' : '无' }}</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- 系统配置卡片 -->
      <q-card class="settings-card q-mb-md">
        <q-card-section>
          <div class="text-h6 q-mb-md">
            <q-icon name="settings" class="q-mr-sm" />
            系统配置
          </div>
          <q-separator class="q-mb-md" />
          
          <div class="setting-item">
            <div class="setting-label">
              <q-icon name="language" class="q-mr-sm" />
              语言设置
            </div>
            <q-select
              v-model="language"
              :options="languageOptions"
              outlined
              dense
              style="max-width: 200px"
            />
          </div>
          
          <div class="setting-item">
            <div class="setting-label">
              <q-icon name="palette" class="q-mr-sm" />
              主题模式
            </div>
            <q-select
              v-model="theme"
              :options="themeOptions"
              outlined
              dense
              style="max-width: 200px"
            />
          </div>
          
          <div class="setting-item">
            <div class="setting-label">
              <q-icon name="notifications" class="q-mr-sm" />
              通知提醒
            </div>
            <q-toggle
              v-model="notifications"
              color="primary"
              label="启用通知"
            />
          </div>
          
          <div class="setting-item">
            <div class="setting-label">
              <q-icon name="volume_up" class="q-mr-sm" />
              声音提示
            </div>
            <q-toggle
              v-model="sound"
              color="primary"
              label="启用声音"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- 连接配置卡片 -->
      <q-card class="settings-card q-mb-md">
        <q-card-section>
          <div class="text-h6 q-mb-md">
            <q-icon name="wifi" class="q-mr-sm" />
            连接配置
          </div>
          <q-separator class="q-mb-md" />
          
          <div class="info-row">
            <span class="info-label">WebSocket状态：</span>
            <q-badge :color="droneStore.droneList.length > 0 ? 'positive' : 'warning'">
              {{ droneStore.droneList.length > 0 ? '已连接' : '未连接' }}
            </q-badge>
          </div>
          
          <div class="info-row">
            <span class="info-label">已连接无人机：</span>
            <span class="info-value">{{ droneStore.droneList.length }} 架</span>
          </div>
          
          <div class="q-mt-md">
            <q-btn
              color="primary"
              icon="refresh"
              label="重新连接"
              @click="reconnectWebSocket"
              :loading="reconnecting"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- AI API 配置卡片 -->
      <q-card class="settings-card q-mb-md">
        <q-card-section>
          <div class="text-h6 q-mb-md">
            <q-icon name="smart_toy" class="q-mr-sm" />
            AI API 配置
          </div>
          <q-separator class="q-mb-md" />
          
          <div class="setting-item">
            <div class="setting-label">
              <q-icon name="cloud" class="q-mr-sm" />
              API 提供商
            </div>
            <q-select
              v-model="aiApiProvider"
              :options="aiApiProviders"
              outlined
              dense
              style="max-width: 200px"
              @update:model-value="saveAiApiConfig"
            />
          </div>
          
          <div class="setting-item">
            <div class="setting-label">
              <q-icon name="vpn_key" class="q-mr-sm" />
              API Key
            </div>
            <q-input
              v-model="aiApiKey"
              type="password"
              outlined
              dense
              placeholder="输入您的 API Key"
              style="max-width: 400px"
              @blur="saveAiApiConfig"
            >
              <template v-slot:append>
                <q-icon
                  :name="showApiKey ? 'visibility_off' : 'visibility'"
                  class="cursor-pointer"
                  @click="showApiKey = !showApiKey"
                />
              </template>
            </q-input>
          </div>
          
          <div class="setting-item">
            <div class="setting-label">
              <q-icon name="link" class="q-mr-sm" />
              API 端点 (可选)
            </div>
            <q-input
              v-model="aiApiEndpoint"
              outlined
              dense
              placeholder="留空使用默认端点"
              style="max-width: 400px"
              @blur="saveAiApiConfig"
            />
          </div>
          
          <div class="api-status">
            <q-icon 
              :name="aiApiKey ? 'check_circle' : 'error'" 
              :color="aiApiKey ? 'positive' : 'grey'" 
              size="sm"
            />
            <span :class="aiApiKey ? 'text-positive' : 'text-grey'">
              {{ aiApiKey ? 'API 已配置' : '未配置 API' }}
            </span>
          </div>
          
          <div class="api-help">
            <q-icon name="help_outline" size="sm" class="q-mr-xs" />
            <span class="help-text">
              如何获取 API Key？查看 
              <a href="#" @click.prevent="showApiGuide = true" class="help-link">配置指南</a>
            </span>
          </div>
        </q-card-section>
      </q-card>

      <!-- 关于系统卡片 -->
      <q-card class="settings-card">
        <q-card-section>
          <div class="text-h6 q-mb-md">
            <q-icon name="info" class="q-mr-sm" />
            关于系统
          </div>
          <q-separator class="q-mb-md" />
          
          <div class="info-row">
            <span class="info-label">系统名称：</span>
            <span class="info-value">无人机集群操作系统</span>
          </div>
          
          <div class="info-row">
            <span class="info-label">版本号：</span>
            <span class="info-value">v1.0.0</span>
          </div>
          
          <div class="info-row">
            <span class="info-label">构建时间：</span>
            <span class="info-value">2024-01-08</span>
          </div>
        </q-card-section>
      </q-card>
      <div class="action-buttons q-mt-lg">
        <q-btn
          color="negative"
          icon="logout"
          label="退出登录"
          @click="handleLogout"
          size="md"
        />
        
        <q-btn
          flat
          color="primary"
          icon="arrow_back"
          label="返回"
          @click="goBack"
          size="md"
        />
      </div>
    </div>

    <!-- API 配置指南对话框 -->
    <q-dialog v-model="showApiGuide" maximized>
      <q-card>
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">AI API 配置指南</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-none" style="max-height: 80vh; overflow-y: auto;">
          <div class="api-guide-content">
            <h3>支持的 API 提供商</h3>
            
            <div class="provider-section">
              <h4>1. OpenAI (推荐)</h4>
              <p><strong>官网</strong>: <a href="https://platform.openai.com/" target="_blank">https://platform.openai.com/</a></p>
              <p><strong>申请步骤</strong>:</p>
              <ol>
                <li>访问 OpenAI 官网注册账号</li>
                <li>登录后访问 API Keys 页面</li>
                <li>点击 "Create new secret key" 创建密钥</li>
                <li>复制并保存 API Key（只显示一次）</li>
              </ol>
              <p><strong>定价</strong>: GPT-3.5-turbo 约 $0.002/1K tokens</p>
            </div>

            <div class="provider-section">
              <h4>2. 阿里云通义千问</h4>
              <p><strong>官网</strong>: <a href="https://dashscope.aliyun.com/" target="_blank">https://dashscope.aliyun.com/</a></p>
              <p><strong>申请步骤</strong>:</p>
              <ol>
                <li>使用阿里云账号登录</li>
                <li>开通 DashScope 服务</li>
                <li>在控制台创建 API Key</li>
              </ol>
              <p><strong>定价</strong>: 通义千问-Turbo 约 ¥0.008/1K tokens</p>
            </div>

            <div class="provider-section">
              <h4>3. 百度文心一言</h4>
              <p><strong>官网</strong>: <a href="https://cloud.baidu.com/product/wenxinworkshop" target="_blank">https://cloud.baidu.com/product/wenxinworkshop</a></p>
              <p><strong>申请步骤</strong>:</p>
              <ol>
                <li>登录百度智能云</li>
                <li>创建应用获取 API Key</li>
                <li>使用 API Key 获取 Access Token</li>
              </ol>
              <p><strong>定价</strong>: ERNIE-Bot-turbo 约 ¥0.012/千tokens</p>
            </div>

            <div class="provider-section">
              <h4>4. 智谱AI (GLM)</h4>
              <p><strong>官网</strong>: <a href="https://open.bigmodel.cn/" target="_blank">https://open.bigmodel.cn/</a></p>
              <p><strong>申请步骤</strong>:</p>
              <ol>
                <li>注册并登录智谱AI</li>
                <li>在控制台创建 API Key</li>
                <li>新用户赠送免费额度</li>
              </ol>
              <p><strong>定价</strong>: GLM-3-Turbo 约 ¥0.005/千tokens</p>
            </div>

            <h3>推荐配置</h3>
            <div class="recommendation">
              <p><strong>国内用户</strong>: 推荐使用智谱AI或通义千问（网络稳定，有免费额度）</p>
              <p><strong>国外用户</strong>: 推荐使用 OpenAI（功能最强大）</p>
            </div>

            <h3>配置示例</h3>
            <pre class="config-example">
API 提供商: 智谱AI
API Key: your-api-key.xxxxxxxx
API 端点: (留空使用默认)
            </pre>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import { useDroneStore } from 'src/stores/drone'

const router = useRouter()
const $q = useQuasar()
const authStore = useAuthStore()
const droneStore = useDroneStore()

// 设置项
const language = ref(localStorage.getItem('app_language') || '中文')
const languageOptions = ['中文', 'English']

// 新用户默认使用深色主题；已保存的用户偏好仍然优先。
const theme = ref(localStorage.getItem('app_theme') || '深色')
const themeOptions = ['浅色', '深色', '自动']

const notifications = ref(localStorage.getItem('app_notifications') !== 'false')
const sound = ref(localStorage.getItem('app_sound') !== 'false')
const reconnecting = ref(false)

// AI API 配置
const aiApiProvider = ref('')
const aiApiProviders = ['OpenAI', 'Azure OpenAI', '通义千问', '文心一言', '智谱AI', '自定义']
const aiApiKey = ref('')
const aiApiEndpoint = ref('')
const showApiKey = ref(false)
const showApiGuide = ref(false)

// 加载 AI API 配置
async function loadAiApiConfig() {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) return
    
    const response = await fetch('/api/ai-config', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      aiApiProvider.value = data.ai_api_provider || 'OpenAI'
      aiApiKey.value = data.ai_api_key || ''
      aiApiEndpoint.value = data.ai_api_endpoint || ''
    }
  } catch (error) {
    console.error('加载 AI 配置失败:', error)
  }
}

// 保存 AI API 配置
async function saveAiApiConfig() {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      $q.notify({
        type: 'warning',
        message: '请先登录',
        position: 'top'
      })
      return
    }
    
    const response = await fetch('/api/ai-config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        ai_api_provider: aiApiProvider.value,
        ai_api_key: aiApiKey.value,
        ai_api_endpoint: aiApiEndpoint.value
      })
    })
    
    if (response.ok) {
      // 同时保存到 localStorage 作为缓存（可选）
      localStorage.setItem('ai_api_provider', aiApiProvider.value)
      localStorage.setItem('ai_api_key', aiApiKey.value)
      localStorage.setItem('ai_api_endpoint', aiApiEndpoint.value)
      
      $q.notify({
        type: 'positive',
        message: 'AI API 配置已保存到服务器',
        position: 'top'
      })
    } else {
      throw new Error('保存失败')
    }
  } catch (error) {
    console.error('保存 AI 配置失败:', error)
    $q.notify({
      type: 'negative',
      message: '保存 AI 配置失败',
      position: 'top'
    })
  }
}

// 监听主题变化
watch(theme, (newTheme) => {
  localStorage.setItem('app_theme', newTheme)
  
  if (newTheme === '深色') {
    $q.dark.set(true)
  } else if (newTheme === '浅色') {
    $q.dark.set(false)
  } else {
    // 自动模式：根据系统设置
    $q.dark.set('auto')
  }
  
  $q.notify({
    type: 'positive',
    message: `已切换到${newTheme}模式`,
    position: 'top'
  })
})

// 监听语言变化
watch(language, (newLang) => {
  localStorage.setItem('app_language', newLang)
  $q.notify({
    type: 'positive',
    message: `语言已切换到${newLang}`,
    position: 'top'
  })
})

// 监听通知设置变化
watch(notifications, (newVal) => {
  localStorage.setItem('app_notifications', newVal.toString())
})

// 监听声音设置变化
watch(sound, (newVal) => {
  localStorage.setItem('app_sound', newVal.toString())
})

// 初始化时应用主题
onMounted(() => {
  if (theme.value === '深色') {
    $q.dark.set(true)
  } else if (theme.value === '浅色') {
    $q.dark.set(false)
  } else {
    $q.dark.set('auto')
  }
  
  // 如果有 token 但没有加载用户信息，则加载
  if (authStore.token && !authStore.meLoaded) {
    authStore.fetchMe()
  }
  
  // 加载 AI API 配置
  loadAiApiConfig()
})

// 重新连接WebSocket
function reconnectWebSocket() {
  reconnecting.value = true
  droneStore.connectWebSocket()
  
  setTimeout(() => {
    reconnecting.value = false
    $q.notify({
      type: 'positive',
      message: '重新连接成功',
      position: 'top'
    })
  }, 1000)
}

// 退出登录
function handleLogout() {
  $q.dialog({
    title: '确认退出',
    message: '确定要退出登录吗？',
    cancel: {
      label: '取消',
      color: 'grey',
      flat: true
    },
    ok: {
      label: '退出',
      color: 'negative'
    },
    persistent: true
  }).onOk(() => {
    authStore.logout()
    router.push('/login')
    $q.notify({
      type: 'positive',
      message: '已成功退出登录',
      position: 'top'
    })
  })
}

// 返回
function goBack() {
  router.back()
}
</script>

<style scoped>
.settings-page {
  max-width: 1200px;
  margin: 0 auto;
  font-family: 'Inter', 'Noto Sans SC', sans-serif;
}

.page-header {
  padding-bottom: 16px;
  border-bottom: 2px solid #e0e0e0;
}

.page-header .text-h4 {
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #2C3E50;
}

.settings-container {
  max-width: 800px;
}

.settings-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
}

.settings-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.settings-card .text-h6 {
  font-weight: 600;
  color: #2C3E50;
  display: flex;
  align-items: center;
}

.info-row {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-weight: 600;
  color: #666;
  min-width: 120px;
  font-size: 14px;
}

.info-value {
  color: #333;
  font-size: 14px;
  font-weight: 500;
}

.token-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #666;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  font-weight: 600;
  color: #333;
  font-size: 14px;
  display: flex;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: flex-start;
}

.api-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 14px;
}

.api-help {
  display: flex;
  align-items: center;
  margin-top: 12px;
  font-size: 13px;
  color: #666;
}

.help-text {
  display: flex;
  align-items: center;
}

.help-link {
  color: #1976d2;
  text-decoration: none;
  margin-left: 4px;
}

.help-link:hover {
  text-decoration: underline;
}

.api-guide-content {
  padding: 20px;
  font-family: 'Inter', 'Noto Sans SC', sans-serif;
}

.api-guide-content h3 {
  color: #2C3E50;
  margin-top: 24px;
  margin-bottom: 16px;
  font-size: 20px;
  font-weight: 600;
}

.api-guide-content h4 {
  color: #4a90e2;
  margin-top: 16px;
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
}

.provider-section {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.provider-section p {
  margin: 8px 0;
  line-height: 1.6;
}

.provider-section ol {
  margin: 8px 0;
  padding-left: 24px;
}

.provider-section li {
  margin: 4px 0;
}

.provider-section a {
  color: #1976d2;
  text-decoration: none;
}

.provider-section a:hover {
  text-decoration: underline;
}

.recommendation {
  background: #e3f2fd;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #1976d2;
}

.recommendation p {
  margin: 8px 0;
  line-height: 1.6;
}

.config-example {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  overflow-x: auto;
}

/* 深色主题下提高设置页文字、分隔线和辅助区域的对比度。 */
:deep(body.body--dark) .page-header {
  border-bottom-color: rgba(255, 255, 255, 0.18);
}

:deep(body.body--dark) .page-header .text-h4,
:deep(body.body--dark) .settings-card .text-h6,
:deep(body.body--dark) .api-guide-content h3 {
  color: #f2f6f8;
}

:deep(body.body--dark) .page-header .text-caption,
:deep(body.body--dark) .info-label,
:deep(body.body--dark) .api-help,
:deep(body.body--dark) .help-text,
:deep(body.body--dark) .token-text {
  color: #b7c5cc !important;
}

:deep(body.body--dark) .info-value,
:deep(body.body--dark) .setting-label,
:deep(body.body--dark) .provider-section,
:deep(body.body--dark) .provider-section p,
:deep(body.body--dark) .provider-section li,
:deep(body.body--dark) .recommendation p {
  color: #e5edf0;
}

:deep(body.body--dark) .info-row,
:deep(body.body--dark) .setting-item {
  border-bottom-color: rgba(255, 255, 255, 0.14);
}

:deep(body.body--dark) .api-status,
:deep(body.body--dark) .provider-section {
  background: rgba(255, 255, 255, 0.07);
}

:deep(body.body--dark) .recommendation {
  background: rgba(33, 150, 243, 0.2);
}

:deep(body.body--dark) .api-guide-content h4 {
  color: #72c7ff;
}
</style>
