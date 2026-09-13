<template>
  <q-page class="compute-page">
    <!-- 标题栏 -->
    <header class="hero">
      <div>
        <p class="eyebrow">算力感知系统</p>
        <h1>无人机算力实时监控</h1>
        <p class="subhead">GPU资源 · 计算能力 · 负载状态</p>
      </div>
      <div class="status-pill">
        <span class="dot"></span>
        <span>在线节点: {{ computeNodes.length }} | GPU总数: {{ totalGPUs }}</span>
      </div>
    </header>

    <!-- 算力资源表 -->
    <section class="card table-card">
      <div class="card-header">
        <div>
          <h2>算力资源状态表</h2>
          <p>机载计算设备GPU配置与使用情况</p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>无人机ID</th>
              <th>IP地址</th>
              <th>网络类型</th>
              <th>GPU数量</th>
              <th>GPU型号</th>
              <th>CPU核心数</th>
              <th>总显存(GB)</th>
              <th>已用显存(GB)</th>
              <th>GPU利用率(%)</th>
              <th>CPU利用率(%)</th>
              <th>温度(°C)</th>
              <th>功耗(W)</th>
              <th>计算状态</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="node in computeNodes" :key="node.id">
              <td style="font-weight: 700;">{{ node.id }}</td>
              <td style="font-family: monospace;">{{ node.ip }}</td>
              <td>
                <span 
                  class="network-badge" 
                  :style="{ background: node.networkType.includes('4G/5G') ? '#3b82f6' : '#10b981' }"
                >
                  {{ node.networkType }}
                </span>
              </td>
              <td style="font-weight: 700; color: #2563eb;">{{ node.gpuCount }}</td>
              <td>{{ node.gpuModel }}</td>
              <td style="font-weight: 600; color: #7c3aed;">{{ node.cpuCores }}</td>
              <td>{{ node.totalMemory }}</td>
              <td>{{ node.usedMemory }}</td>
              <td>
                <div class="usage-bar-container">
                  <div 
                    class="usage-bar" 
                    :style="{ 
                      width: node.gpuUsage + '%', 
                      background: getUsageColor(node.gpuUsage) 
                    }"
                  ></div>
                  <span class="usage-text">{{ node.gpuUsage }}%</span>
                </div>
              </td>
              <td>
                <div class="usage-bar-container">
                  <div 
                    class="usage-bar" 
                    :style="{ 
                      width: node.cpuUsage + '%', 
                      background: getUsageColor(node.cpuUsage) 
                    }"
                  ></div>
                  <span class="usage-text">{{ node.cpuUsage }}%</span>
                </div>
              </td>
              <td :style="{ color: getTempColor(node.temperature) }">{{ node.temperature }}</td>
              <td>{{ node.power }}</td>
              <td>
                <span 
                  class="status-badge" 
                  :style="{ 
                    background: node.status === '计算中' ? '#10b981' : '#64748b',
                    color: 'white'
                  }"
                >
                  {{ node.status }}
                </span>
              </td>
              <td style="color: #64748b; font-size: 12px;">{{ formatTime(node.updated) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- GPU拓扑视图 -->
    <section class="card topo-card">
      <div class="card-header">
        <div>
          <h2>算力拓扑分布</h2>
          <p>无人机GPU资源空间分布与连接状态</p>
        </div>
      </div>
      <div class="topo-wrap">
        <svg 
          ref="topologySvg" 
          viewBox="0 0 800 450" 
          role="img" 
          aria-label="算力拓扑图"
          @pointermove="handlePointerMove"
          @pointerup="endDrag"
        ></svg>
      </div>
      <div class="legend">
        <span class="legend-item">
          <i class="legend-dot" style="background: #3b82f6;"></i>4G/5G网络节点
        </span>
        <span class="legend-item">
          <i class="legend-dot" style="background: #10b981;"></i>自组网节点
        </span>
        <span class="legend-item">
          <i class="legend-icon">🎮</i>GPU设备
        </span>
      </div>
    </section>

    <!-- GPU统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: #dbeafe;">
          <span style="font-size: 32px;">🎮</span>
        </div>
        <div class="stat-content">
          <div class="stat-label">GPU总数</div>
          <div class="stat-value">{{ totalGPUs }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #dcfce7;">
          <span style="font-size: 32px;">⚡</span>
        </div>
        <div class="stat-content">
          <div class="stat-label">平均利用率</div>
          <div class="stat-value">{{ avgUsage }}%</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fef3c7;">
          <span style="font-size: 32px;">💾</span>
        </div>
        <div class="stat-content">
          <div class="stat-label">总显存</div>
          <div class="stat-value">{{ totalMemory }}GB</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fce7f3;">
          <span style="font-size: 32px;">🔥</span>
        </div>
        <div class="stat-content">
          <div class="stat-label">平均温度</div>
          <div class="stat-value">{{ avgTemp }}°C</div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

// 模拟算力数据 - 8个节点，统一配置
const mockComputeData = [
  // 4G/5G + 自组网节点 (10.0.0.1-4)
  {
    id: 'DRONE-01',
    ip: '10.0.0.1',
    meshIp: '10.42.0.101',
    networkType: '4G/5G + 自组网',
    gpuCount: 1,          // 统一为1个GPU
    gpuModel: 'Jetson Orin NX',  // 统一GPU型号
    cpuCores: 8,          // 统一为8核CPU
    totalMemory: 16,
    usedMemory: 5.2,
    gpuUsage: 35,
    cpuUsage: 28,
    temperature: 52,
    power: 25,
    status: '计算中',
    updated: Date.now()
  },
  {
    id: 'DRONE-02',
    ip: '10.0.0.2',
    meshIp: '10.42.0.102',
    networkType: '4G/5G + 自组网',
    gpuCount: 1,
    gpuModel: 'Jetson Orin NX',
    cpuCores: 8,
    totalMemory: 16,
    usedMemory: 3.8,
    gpuUsage: 22,
    cpuUsage: 18,
    temperature: 48,
    power: 18,
    status: '空闲',
    updated: Date.now()
  },
  {
    id: 'DRONE-03',
    ip: '10.0.0.3',
    meshIp: '10.42.0.103',
    networkType: '4G/5G + 自组网',
    gpuCount: 1,
    gpuModel: 'Jetson Orin NX',
    cpuCores: 8,
    totalMemory: 16,
    usedMemory: 11.5,
    gpuUsage: 68,
    cpuUsage: 72,
    temperature: 61,
    power: 45,
    status: '计算中',
    updated: Date.now()
  },
  {
    id: 'DRONE-04',
    ip: '10.0.0.4',
    meshIp: '10.42.0.104',
    networkType: '4G/5G + 自组网',
    gpuCount: 1,
    gpuModel: 'Jetson Orin NX',
    cpuCores: 8,
    totalMemory: 16,
    usedMemory: 7.8,
    gpuUsage: 42,
    cpuUsage: 38,
    temperature: 55,
    power: 32,
    status: '计算中',
    updated: Date.now()
  },
  // 自组网节点 (192.168.1.1-4)
  {
    id: 'DRONE-05',
    ip: '192.168.1.1',
    networkType: '自组网',
    gpuCount: 1,
    gpuModel: 'Jetson Orin NX',
    cpuCores: 8,
    totalMemory: 16,
    usedMemory: 15.2,
    gpuUsage: 63,
    cpuUsage: 58,
    temperature: 65,
    power: 48,
    status: '计算中',
    updated: Date.now()
  },
  {
    id: 'DRONE-06',
    ip: '192.168.1.2',
    networkType: '自组网',
    gpuCount: 1,
    gpuModel: 'Jetson Orin NX',
    cpuCores: 8,
    totalMemory: 16,
    usedMemory: 2.8,
    gpuUsage: 23,
    cpuUsage: 15,
    temperature: 49,
    power: 22,
    status: '空闲',
    updated: Date.now()
  },
  {
    id: 'DRONE-07',
    ip: '192.168.1.3',
    networkType: '自组网',
    gpuCount: 1,
    gpuModel: 'Jetson Orin NX',
    cpuCores: 8,
    totalMemory: 16,
    usedMemory: 13.5,
    gpuUsage: 84,
    cpuUsage: 78,
    temperature: 72,
    power: 55,
    status: '计算中',
    updated: Date.now()
  },
  {
    id: 'DRONE-08',
    ip: '192.168.1.4',
    networkType: '自组网',
    gpuCount: 1,
    gpuModel: 'Jetson Orin NX',
    cpuCores: 8,
    totalMemory: 16,
    usedMemory: 4.1,
    gpuUsage: 34,
    cpuUsage: 25,
    temperature: 55,
    power: 28,
    status: '空闲',
    updated: Date.now()
  }
]

// 数据
const computeNodes = ref(mockComputeData)
const topologySvg = ref(null)

// SVG 拓扑相关
const VIEWBOX = { width: 800, height: 450 }
const CENTER = { x: 400, y: 225 }
const nodes = ref([])
const nodeElements = new Map()
let dragState = null
let animationFrameId = null
let lastTime = 0

// 计算属性
const totalGPUs = computed(() => {
  return computeNodes.value.reduce((sum, node) => sum + node.gpuCount, 0)
})

const avgUsage = computed(() => {
  const total = computeNodes.value.reduce((sum, node) => sum + node.gpuUsage, 0)
  return Math.round(total / computeNodes.value.length)
})

const totalMemory = computed(() => {
  return computeNodes.value.reduce((sum, node) => sum + node.totalMemory, 0)
})

const avgTemp = computed(() => {
  const total = computeNodes.value.reduce((sum, node) => sum + node.temperature, 0)
  return Math.round(total / computeNodes.value.length)
})

// 工具函数
function formatTime(timestamp) {
  const date = typeof timestamp === 'number' ? new Date(timestamp) : new Date()
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function getUsageColor(usage) {
  if (usage > 80) return '#ef4444'
  if (usage > 50) return '#f59e0b'
  return '#10b981'
}

function getTempColor(temp) {
  if (temp > 70) return '#ef4444'
  if (temp > 60) return '#f59e0b'
  return '#10b981'
}

// 同步拓扑数据
function syncTopologyData() {
  nodes.value = []

  computeNodes.value.forEach((node, index) => {
    const angle = (index / computeNodes.value.length) * Math.PI * 2
    const radius = 150

    nodes.value.push({
      id: `${node.id}-${node.ip}`,
      label: node.id,
      ip: node.ip,
      networkType: node.networkType.includes('4G/5G') ? '4G/5G' : '自组网',
      gpuCount: node.gpuCount,
      x: CENTER.x + Math.cos(angle) * radius,
      y: CENTER.y + Math.sin(angle) * radius,
      orbitAngle: angle,
      orbitRadius: radius,
      orbitSpeed: (index % 2 === 0 ? 1 : -1) * 0.08
    })
  })

  renderSvgElements()
}

// 渲染 SVG 元素
function renderSvgElements() {
  if (!topologySvg.value) return

  const svg = topologySvg.value
  svg.innerHTML = ''
  nodeElements.clear()

  const ns = 'http://www.w3.org/2000/svg'

  // 渲染中心计算集群标识
  const centerGroup = document.createElementNS(ns, 'g')
  const centerCircle = document.createElementNS(ns, 'circle')
  centerCircle.setAttribute('cx', CENTER.x)
  centerCircle.setAttribute('cy', CENTER.y)
  centerCircle.setAttribute('r', '50')
  centerCircle.setAttribute('fill', '#1e293b')
  centerCircle.setAttribute('stroke', '#64748b')
  centerCircle.setAttribute('stroke-width', '2')

  const centerText = document.createElementNS(ns, 'text')
  centerText.setAttribute('x', CENTER.x)
  centerText.setAttribute('y', CENTER.y - 5)
  centerText.setAttribute('text-anchor', 'middle')
  centerText.setAttribute('fill', '#e2e8f0')
  centerText.setAttribute('font-size', '14')
  centerText.setAttribute('font-weight', '700')
  centerText.textContent = '算力集群'

  const centerSubText = document.createElementNS(ns, 'text')
  centerSubText.setAttribute('x', CENTER.x)
  centerSubText.setAttribute('y', CENTER.y + 12)
  centerSubText.setAttribute('text-anchor', 'middle')
  centerSubText.setAttribute('fill', '#94a3b8')
  centerSubText.setAttribute('font-size', '12')
  centerSubText.textContent = `${totalGPUs.value} GPUs`

  centerGroup.appendChild(centerCircle)
  centerGroup.appendChild(centerText)
  centerGroup.appendChild(centerSubText)
  svg.appendChild(centerGroup)

  // 渲染连接线
  nodes.value.forEach(node => {
    const line = document.createElementNS(ns, 'line')
    line.setAttribute('x1', CENTER.x)
    line.setAttribute('y1', CENTER.y)
    line.setAttribute('x2', node.x)
    line.setAttribute('y2', node.y)
    line.setAttribute('stroke', node.networkType === '4G/5G' ? '#3b82f6' : '#10b981')
    line.setAttribute('stroke-width', '2')
    line.setAttribute('stroke-opacity', '0.4')
    line.setAttribute('stroke-dasharray', '5,5')
    svg.appendChild(line)
  })

  // 渲染节点
  nodes.value.forEach(node => {
    const g = document.createElementNS(ns, 'g')
    g.setAttribute('class', 'compute-node')
    g.style.cursor = 'grab'
    g.dataset.id = node.id

    const circle = document.createElementNS(ns, 'circle')
    circle.setAttribute('r', '35')
    circle.setAttribute('fill', '#0f172a')
    circle.setAttribute('stroke', node.networkType === '4G/5G' ? '#3b82f6' : '#10b981')
    circle.setAttribute('stroke-width', '3')

    const textId = document.createElementNS(ns, 'text')
    textId.setAttribute('text-anchor', 'middle')
    textId.setAttribute('dy', '-5')
    textId.setAttribute('fill', '#e2e8f0')
    textId.setAttribute('font-weight', '700')
    textId.setAttribute('font-size', '14')
    textId.textContent = node.label

    const gpuText = document.createElementNS(ns, 'text')
    gpuText.setAttribute('text-anchor', 'middle')
    gpuText.setAttribute('dy', '10')
    gpuText.setAttribute('fill', '#fbbf24')
    gpuText.setAttribute('font-size', '12')
    gpuText.textContent = `🎮 ${node.gpuCount}`

    const ipBg = document.createElementNS(ns, 'rect')
    ipBg.setAttribute('fill', 'rgba(15, 23, 42, 0.9)')
    ipBg.setAttribute('stroke', '#334155')
    ipBg.setAttribute('stroke-width', '1')
    ipBg.setAttribute('rx', '4')
    ipBg.setAttribute('height', '20')
    const ipWidth = node.ip.length * 7 + 10
    ipBg.setAttribute('width', ipWidth)
    ipBg.setAttribute('x', -ipWidth / 2)
    ipBg.setAttribute('y', '45')

    const ipText = document.createElementNS(ns, 'text')
    ipText.setAttribute('text-anchor', 'middle')
    ipText.setAttribute('dy', '60')
    ipText.setAttribute('fill', '#94a3b8')
    ipText.setAttribute('font-size', '10')
    ipText.setAttribute('font-family', 'monospace')
    ipText.textContent = node.ip

    g.appendChild(circle)
    g.appendChild(textId)
    g.appendChild(gpuText)
    g.appendChild(ipBg)
    g.appendChild(ipText)

    g.onpointerdown = (e) => startDrag(e, node)

    svg.appendChild(g)
    nodeElements.set(node.id, { g, node, circle })
  })

  updatePositions()
}

// 更新位置
function updatePositions() {
  nodeElements.forEach(({ g, node }) => {
    g.setAttribute('transform', `translate(${node.x}, ${node.y})`)
  })
}

// 动画循环
function tick(timestamp) {
  const dt = lastTime ? (timestamp - lastTime) / 1000 : 0
  lastTime = timestamp

  nodes.value.forEach(node => {
    if (dragState && dragState.node === node) return

    node.orbitAngle += node.orbitSpeed * dt
    node.x = CENTER.x + Math.cos(node.orbitAngle) * node.orbitRadius
    node.y = CENTER.y + Math.sin(node.orbitAngle) * node.orbitRadius
  })

  updatePositions()
  animationFrameId = requestAnimationFrame(tick)
}

// 拖拽相关
function startDrag(event, node) {
  const rect = topologySvg.value.getBoundingClientRect()
  dragState = {
    node,
    startX: event.clientX,
    startY: event.clientY,
    origX: node.x,
    origY: node.y,
    rect
  }

  const element = nodeElements.get(node.id)
  if (element) {
    element.g.style.cursor = 'grabbing'
    element.circle.setAttribute('stroke-width', '5')
  }

  event.currentTarget.setPointerCapture(event.pointerId)
}

function handlePointerMove(event) {
  if (!dragState) return

  const dx = event.clientX - dragState.startX
  const dy = event.clientY - dragState.startY

  const scaleX = VIEWBOX.width / dragState.rect.width
  const scaleY = VIEWBOX.height / dragState.rect.height

  dragState.node.x = dragState.origX + dx * scaleX
  dragState.node.y = dragState.origY + dy * scaleY

  const relX = dragState.node.x - CENTER.x
  const relY = dragState.node.y - CENTER.y
  dragState.node.orbitRadius = Math.sqrt(relX * relX + relY * relY)
  dragState.node.orbitAngle = Math.atan2(relY, relX)

  updatePositions()
}

function endDrag() {
  if (!dragState) return

  const element = nodeElements.get(dragState.node.id)
  if (element) {
    element.g.style.cursor = 'grab'
    element.circle.setAttribute('stroke-width', '3')
  }

  dragState = null
}

// 生命周期
onMounted(() => {
  console.log('ComputeSensePage mounted')
  syncTopologyData()
  animationFrameId = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})
</script>

<style scoped>
.compute-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 40px 24px;
  display: grid;
  gap: 32px;
  background: #f8fafc;
  min-height: 100vh;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 24px;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 1px;
  color: #2563eb;
  font-weight: 700;
  margin-bottom: 8px;
}

h1 {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: #0f172a;
}

.subhead {
  margin-top: 8px;
  color: #64748b;
  font-size: 14px;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #e0f2fe;
  color: #0369a1;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
}

.dot {
  width: 8px;
  height: 8px;
  background: #0ea5e9;
  border-radius: 50%;
  box-shadow: 0 0 8px #0ea5e9;
  animation: blink 2s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.card-header h2 {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
}

.card-header p {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 1400px;
}

thead {
  background: #f8fafc;
  color: #475569;
}

th {
  text-align: left;
  padding: 12px 16px;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

td {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  color: #334155;
  white-space: nowrap;
}

tbody tr:hover {
  background: #f1f5f9;
}

.network-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: white;
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.usage-bar-container {
  position: relative;
  width: 100px;
  height: 20px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.usage-bar {
  height: 100%;
  transition: width 0.3s ease;
}

.usage-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  font-weight: 600;
  color: #1e293b;
}

.topo-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  color: #e2e8f0;
}

.topo-card .card-header {
  border-bottom: 1px solid #1e293b;
}

.topo-card h2 {
  color: #f8fafc;
}

.topo-card p {
  color: #94a3b8;
}

.topo-wrap {
  position: relative;
  height: 450px;
  background-image:
    linear-gradient(rgba(56, 189, 248, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(56, 189, 248, 0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  overflow: hidden;
}

svg {
  width: 100%;
  height: 100%;
  display: block;
}

.compute-node circle {
  transition: all 0.3s;
}

.compute-node:hover circle {
  stroke-width: 5px !important;
  filter: drop-shadow(0 0 12px currentColor);
}

.legend {
  padding: 16px 24px;
  display: flex;
  gap: 24px;
  font-size: 12px;
  color: #94a3b8;
  background: #0b1120;
  border-top: 1px solid #1e293b;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-icon {
  font-size: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.stat-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 4px 20px -4px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px -6px rgba(0, 0, 0, 0.12);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
}

@media (max-width: 860px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-pill {
    align-self: flex-start;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>

