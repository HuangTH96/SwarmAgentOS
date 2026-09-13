<template>
  <q-page class="video-stream-page">
    <!-- 页面头部控制栏 -->
    <div class="video-controls">
      <div class="controls-left">
        <q-btn
          flat
          icon="grid_view"
          :label="layoutMode"
          @click="toggleLayout"
          class="tech-btn"
        />
        <q-btn
          flat
          icon="fullscreen"
          label="全屏模式"
          @click="toggleFullscreen"
          class="tech-btn"
        />
        <q-btn
          flat
          icon="refresh"
          label="刷新"
          @click="refreshStreams"
          class="tech-btn"
        />
      </div>
      <div class="controls-right">
        <q-chip
          v-for="drone in connectedDrones"
          :key="drone.id"
          :color="drone.isConnected ? 'green' : 'red'"
          text-color="white"
          class="drone-status-chip"
        >
          {{ drone.name || drone.id }}
        </q-chip>
      </div>
    </div>

    <!-- 视频展示区域 -->
    <div class="video-container" :class="layoutClass">
      <!-- 网格布局模式 -->
      <template v-if="!isFullscreen">
        <div
          v-for="drone in connectedDrones"
          :key="drone.id"
          class="video-item"
          :class="{ 'selected': selectedVideoId === drone.id }"
          @click="selectVideo(drone.id)"
        >
          <div class="video-header">
            <span class="drone-name">{{ drone.name || drone.id }}</span>
            <div class="video-controls-mini">
              <q-btn
                flat
                dense
                icon="fullscreen"
                size="sm"
                @click.stop="enterFullscreen(drone.id)"
                class="mini-btn"
              />
              <q-btn
                flat
                dense
                icon="volume_off"
                size="sm"
                @click.stop="toggleMute(drone.id)"
                class="mini-btn"
              />
            </div>
          </div>
          <div class="video-wrapper">
            <img
              :src="getStreamUrl(drone.ip)"
              class="video-stream"
              :class="{ 'muted': mutedVideos[drone.id] }"
              @error="handleVideoError(drone.id)"
            />
            <div v-if="videoErrors[drone.id]" class="video-error">
              <q-icon name="error" size="2em" />
              <p>视频流连接失败</p>
            </div>
          </div>
        </div>
      </template>

      <!-- 全屏模式 -->
      <div v-else class="fullscreen-video">
        <div class="fullscreen-header">
          <span class="fullscreen-title">
            {{ selectedDrone?.name || selectedDrone?.id || '无人机视频' }}
          </span>
          <q-btn
            flat
            icon="close"
            @click="exitFullscreen"
            class="exit-fullscreen-btn"
          />
        </div>
        <div class="fullscreen-video-wrapper">
          <img
            :src="getStreamUrl(selectedDrone?.ip)"
            class="fullscreen-stream"
            @error="handleVideoError(selectedDrone?.id)"
          />
          <div v-if="videoErrors[selectedDrone?.id]" class="video-error">
            <q-icon name="error" size="4em" />
            <p>视频流连接失败</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="status-bar">
      <div class="status-left">
        <span>已连接: {{ connectedDrones.length }} 架无人机</span>
        <span v-if="selectedVideoId">当前选中: {{ getDroneName(selectedVideoId) }}</span>
      </div>
      <div class="status-right">
        <q-icon name="wifi" :color="isConnected ? 'green' : 'red'" />
        <span>{{ isConnected ? '已连接' : '未连接' }}</span>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useDroneStore } from 'stores/drone'

const droneStore = useDroneStore()

// 响应式数据
const layoutMode = ref('grid') // grid, 1x1, 2x2, 3x3
const isFullscreen = ref(false)
const selectedVideoId = ref(null)
const mutedVideos = ref({})
const videoErrors = ref({})

// 计算属性
const connectedDrones = computed(() => {
  return droneStore.droneList.filter(drone =>
    droneStore.isClientAccepted(drone.id) && drone.ip
  )
})

const selectedDrone = computed(() => {
  if (!selectedVideoId.value) return null
  return connectedDrones.value.find(d => d.id === selectedVideoId.value)
})

const isConnected = computed(() => droneStore.isConnected)

const layoutClass = computed(() => {
  const count = connectedDrones.value.length
  if (isFullscreen.value) return 'fullscreen'

  if (count <= 1) return 'layout-1x1'
  if (count <= 4) return 'layout-2x2'
  if (count <= 9) return 'layout-3x3'
  return 'layout-grid'
})

// 方法
const getStreamUrl = (ip) => {
  if (!ip) return ''
  return `http://${ip}:8080/?action=stream`
}

const getDroneName = (droneId) => {
  const drone = connectedDrones.value.find(d => d.id === droneId)
  return drone?.name || drone?.id || '未知'
}

const toggleLayout = () => {
  const modes = ['grid', '1x1', '2x2', '3x3']
  const currentIndex = modes.indexOf(layoutMode.value)
  layoutMode.value = modes[(currentIndex + 1) % modes.length]
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value && !selectedVideoId.value && connectedDrones.value.length > 0) {
    selectedVideoId.value = connectedDrones.value[0].id
  }
}

const enterFullscreen = (droneId) => {
  selectedVideoId.value = droneId
  isFullscreen.value = true
}

const exitFullscreen = () => {
  isFullscreen.value = false
}

const selectVideo = (droneId) => {
  selectedVideoId.value = droneId
}

const toggleMute = (droneId) => {
  mutedVideos.value[droneId] = !mutedVideos.value[droneId]
}

const handleVideoError = (droneId) => {
  videoErrors.value[droneId] = true
  console.error(`无人机 ${droneId} 视频流连接失败`)
}

const refreshStreams = () => {
  // 清除错误状态
  videoErrors.value = {}
  // 重新获取无人机列表
  droneStore.fetchClients()
}

// 生命周期
onMounted(() => {
  // 连接WebSocket并获取无人机列表
  droneStore.connectWebSocket()
  droneStore.fetchClients()

  // 如果有无人机，默认选中第一个
  if (connectedDrones.value.length > 0 && !selectedVideoId.value) {
    selectedVideoId.value = connectedDrones.value[0].id
  }
})

onUnmounted(() => {
  // 清理资源
})
</script>

<style scoped>
.video-stream-page {
  height: 100%;
  min-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #F5F8FA 0%, #E3F2FD 50%, #F5F8FA 100%);
  overflow: hidden;
  box-sizing: border-box;
}

.video-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 248, 250, 0.95) 100%);
  border: 1px solid #4A90E2;
  border-radius: 0 0 12px 12px;
  box-shadow: 0 8px 32px rgba(74, 144, 226, 0.15);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}

.controls-left {
  display: flex;
  gap: 8px;
}

.controls-right {
  display: flex;
  gap: 8px;
}

.tech-btn {
  background: linear-gradient(145deg, rgba(74, 144, 226, 0.1) 0%, rgba(255, 255, 255, 0.9) 100%);
  border: 1px solid #4A90E2;
  color: #2C3E50;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.tech-btn:hover {
  box-shadow: 0 4px 20px rgba(74, 144, 226, 0.3);
  transform: translateY(-2px);
  background: linear-gradient(145deg, rgba(74, 144, 226, 0.2) 0%, rgba(255, 255, 255, 1) 100%);
}

.drone-status-chip {
  font-size: 12px;
  font-weight: 500;
  background: rgba(74, 144, 226, 0.1);
  border: 1px solid #4A90E2;
}

.video-container {
  flex: 1;
  padding: 20px;
  display: grid;
  gap: 16px;
  overflow: auto;
  min-height: 0;
}

/* 布局样式 */
.layout-1x1 {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

.layout-2x2 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

.layout-3x3 {
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(3, 1fr);
}

.layout-grid {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  grid-auto-rows: minmax(200px, 1fr);
}

.fullscreen {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

.video-item {
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 248, 250, 0.95) 100%);
  border: 1px solid #4A90E2;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(74, 144, 226, 0.15);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
}

.video-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(74, 144, 226, 0.2);
}

.video-item.selected {
  border: 2px solid #4A90E2;
  box-shadow: 0 0 20px rgba(74, 144, 226, 0.3);
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: linear-gradient(145deg, rgba(74, 144, 226, 0.1) 0%, rgba(255, 255, 255, 0.9) 100%);
  border-bottom: 1px solid rgba(74, 144, 226, 0.3);
  color: #2C3E50;
  font-weight: 500;
  font-size: 14px;
}

.drone-name {
  font-weight: 600;
  color: #2C3E50;
  text-shadow: 0 0 2px rgba(44, 62, 80, 0.1);
}

.video-controls-mini {
  display: flex;
  gap: 4px;
}

.mini-btn {
  color: #2C3E50;
  padding: 4px;
  min-height: 24px;
  min-width: 24px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.mini-btn:hover {
  background: rgba(74, 144, 226, 0.1);
  color: #4A90E2;
}

.video-wrapper {
  position: relative;
  height: calc(100% - 40px);
  overflow: hidden;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: all 0.3s ease;
  border-radius: 0 0 8px 8px;
}

.video-stream.muted {
  filter: grayscale(100%) brightness(0.8);
  opacity: 0.7;
}

.video-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #4A90E2;
  background: rgba(255, 255, 255, 0.9);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #4A90E2;
  box-shadow: 0 4px 15px rgba(74, 144, 226, 0.2);
}

.video-error p {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: #2C3E50;
}

/* 全屏模式样式 */
.fullscreen-video {
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 248, 250, 0.95) 100%);
  border: 1px solid #4A90E2;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(74, 144, 226, 0.15);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
}

.fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: linear-gradient(145deg, rgba(74, 144, 226, 0.1) 0%, rgba(255, 255, 255, 0.9) 100%);
  border-bottom: 1px solid rgba(74, 144, 226, 0.3);
  color: #2C3E50;
}

.fullscreen-title {
  font-size: 18px;
  font-weight: 600;
  color: #2C3E50;
  text-shadow: 0 0 2px rgba(44, 62, 80, 0.1);
}

.exit-fullscreen-btn {
  color: #2C3E50;
  font-size: 20px;
  transition: all 0.2s ease;
}

.exit-fullscreen-btn:hover {
  color: #4A90E2;
  transform: scale(1.1);
}

.fullscreen-video-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.fullscreen-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 248, 250, 0.95) 100%);
  border: 1px solid #4A90E2;
  border-radius: 12px 12px 0 0;
  color: #2C3E50;
  font-size: 14px;
  box-shadow: 0 -4px 15px rgba(74, 144, 226, 0.1);
  flex-shrink: 0;
}

.status-left {
  display: flex;
  gap: 20px;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4A90E2;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .video-container {
    padding: 10px;
    gap: 10px;
  }

  .layout-3x3 {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: repeat(auto-fit, 1fr);
  }

  .video-controls {
    padding: 8px 12px;
  }

  .tech-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .layout-2x2,
  .layout-3x3 {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(auto-fit, 1fr);
  }
}
</style>
