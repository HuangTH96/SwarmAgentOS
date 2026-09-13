<template>
  <q-page class="cellular-page">
    <!-- 标题栏 -->
    <header class="hero">
      <div>
        <p class="eyebrow">UAV Network Overview</p>
        <h1>无人机网络状态与拓扑</h1>
        <p class="subhead">实时展示不同无人机的链路质量、时延与节点关系。</p>
      </div>
      <div class="status-pill">
        <span class="dot"></span>
        <span>在线 {{ networkMetrics.length }} / {{ networkMetrics.length }}</span>
      </div>
    </header>

    <!-- 网络状态表 -->
    <section class="card table-card">
      <div class="card-header">
        <h2>网络状态表</h2>
        <p>已接入无人机 IP 与链路指标</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>节点 IP</th>
              <th>链路质量</th>
              <th>网络带宽(Mbps)</th>
              <th>下行速率(Mbps)</th>
              <th>上行速率(Mbps)</th>
              <th>丢包率(%)</th>
              <th>传输时延(ms)</th>
              <th>时延抖动(ms)</th>
              <th>链路负载(%)</th>
              <th>轮询使用情况</th>
              <th>终端干扰阈值</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="drone in networkMetrics" :key="drone.ip || drone.client_id">
              <td>{{ drone.ip || 'N/A' }}</td>
              <td>{{ drone.quality || calculateQuality(drone) }}</td>
              <td>{{ formatNumber(drone.bandwidth) }}</td>
              <td>{{ formatNumber(drone.download_speed / 1024) }}</td>
              <td>{{ formatNumber(drone.upload_speed / 1024) }}</td>
              <td>{{ formatNumber(drone.packet_loss) }}</td>
              <td>{{ formatNumber(drone.latency) }}</td>
              <td>{{ formatNumber(drone.jitter || 0) }}</td>
              <td>{{ drone.load || calculateLoad(drone) }}</td>
              <td>{{ drone.poll || '正常' }}</td>
              <td>{{ drone.interference || '低' }}</td>
              <td>{{ formatTime(drone.updated || Date.now()) }}</td>
            </tr>
            <tr v-if="networkMetrics.length === 0">
              <td colspan="12" style="text-align: center; color: #999;">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 拓扑关系图 -->
    <section class="card topo-card">
      <div class="card-header">
        <h2>拓扑关系图</h2>
        <p>节点之间的连接关系与角色</p>
        <form class="node-form" @submit.prevent="handleAddNode">
          <input 
            v-model="newNodeIp" 
            type="text" 
            placeholder="输入新节点 IP" 
            autocomplete="off" 
          />
          <button type="submit">加入节点</button>
        </form>
      </div>
      <div class="topo-wrap">
        <svg 
          ref="topologySvg" 
          viewBox="0 0 800 420" 
          role="img" 
          aria-label="无人机拓扑图"
          @pointermove="handlePointerMove"
          @pointerup="endDrag"
          @pointerleave="endDrag"
        ></svg>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot core"></i>核心节点</span>
        <span class="legend-item"><i class="legend-dot edge"></i>无人机节点</span>
      </div>
    </section>
  </q-page>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { getNetworkMetrics } from 'src/services/api'

// 数据
const networkMetrics = ref([])
const newNodeIp = ref('')
const topologySvg = ref(null)

// SVG 拓扑相关
const VIEWBOX = { width: 800, height: 420 }
const nodes = ref([
  { id: 'BS', label: 'BS', x: 400, y: 200, type: 'core', pulseDelay: '0s' }
])
const links = ref([])
const nodeElements = new Map()
const linkElements = []
let dragState = null
let dragHandlersAttached = false
let refreshInterval = null
let animationFrameId = null
let lastTime = 0

// 工具函数
function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function formatNumber(value) {
  if (value === null || value === undefined) return '0.00'
  return Number(value).toFixed(2)
}

function formatTime(timestamp) {
  const date = typeof timestamp === 'number' ? new Date(timestamp) : new Date()
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function calculateQuality(drone) {
  // 根据丢包率和时延计算链路质量 (1-3)
  const loss = drone.packet_loss || 0
  const latency = drone.latency || 0
  if (loss < 0.5 && latency < 50) return 3
  if (loss < 2 && latency < 100) return 2
  return 1
}

function calculateLoad(drone) {
  // 根据带宽使用情况估算负载
  const bandwidth = drone.bandwidth || 0
  const usage = (drone.download_speed + drone.upload_speed) / 1024 || 0
  if (bandwidth === 0) return 0
  return Math.round((usage / bandwidth) * 100)
}

// 模拟静态数据 - 所有网络节点（包含两个网络段）
const mockCellularData = [
  // 4G/5G网络段 (10.0.0.x)
  {
    ip: '10.0.0.1',
    client_id: 'UAV-01',
    bandwidth: 8.5,
    download_speed: 6200,
    upload_speed: 4800,
    packet_loss: 0.2,
    latency: 25,
    jitter: 8.5,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  },
  {
    ip: '10.0.0.2',
    client_id: 'UAV-02',
    bandwidth: 6.8,
    download_speed: 4500,
    upload_speed: 3900,
    packet_loss: 0.5,
    latency: 32,
    jitter: 12.3,
    poll: '正常',
    interference: '中',
    updated: Date.now()
  },
  {
    ip: '10.0.0.3',
    client_id: 'UAV-03',
    bandwidth: 10.2,
    download_speed: 7800,
    upload_speed: 6100,
    packet_loss: 0.1,
    latency: 18,
    jitter: 5.2,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  },
  {
    ip: '10.0.0.4',
    client_id: 'UAV-04',
    bandwidth: 7.3,
    download_speed: 5100,
    upload_speed: 4200,
    packet_loss: 0.8,
    latency: 45,
    jitter: 15.7,
    poll: '繁忙',
    interference: '中',
    updated: Date.now()
  },
  // 自组网段 (192.168.1.x)
  {
    ip: '192.168.1.1',
    client_id: 'UAV-01',
    bandwidth: 18.5,
    download_speed: 8200,
    upload_speed: 7800,
    packet_loss: 0.0,
    latency: 12,
    jitter: 3.5,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  },
  {
    ip: '192.168.1.2',
    client_id: 'UAV-02',
    bandwidth: 16.8,
    download_speed: 7500,
    upload_speed: 6900,
    packet_loss: 0.1,
    latency: 15,
    jitter: 4.3,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  },
  {
    ip: '192.168.1.3',
    client_id: 'UAV-03',
    bandwidth: 20.2,
    download_speed: 9800,
    upload_speed: 8600,
    packet_loss: 0.0,
    latency: 10,
    jitter: 2.8,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  },
  {
    ip: '192.168.1.4',
    client_id: 'UAV-04',
    bandwidth: 17.3,
    download_speed: 8100,
    upload_speed: 7200,
    packet_loss: 0.2,
    latency: 18,
    jitter: 5.1,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  }
]

// 获取网络指标数据
async function fetchNetworkMetrics() {
  try {
    const data = await getNetworkMetrics()
    // 如果后端有数据则使用，否则使用模拟数据
    networkMetrics.value = (data && data.length > 0) ? data : mockCellularData
    console.log('Network metrics updated:', networkMetrics.value)
  } catch (error) {
    console.error('Failed to fetch network metrics:', error)
    // 出错时使用模拟数据
    networkMetrics.value = mockCellularData
  }
}

// 同步节点数据
function syncNodesFromDrones() {
  const prevEdges = nodes.value.filter(node => node.type === 'edge')
  nodes.value = [nodes.value[0]] // 保留 BS 节点
  links.value = []
  
  networkMetrics.value.forEach((drone, index) => {
    const existing = prevEdges.find(node => node.label === (drone.ip || drone.client_id))
    const id = `n${index + 1}`
    
    nodes.value.push({
      id,
      label: drone.ip || drone.client_id,
      x: existing ? existing.x : 0,
      y: existing ? existing.y : 0,
      type: 'edge',
      orbitRadius: existing ? existing.orbitRadius : 0,
      orbitAngle: existing ? existing.orbitAngle : 0,
      orbitSpeed: existing ? existing.orbitSpeed : 0.35 + index * 0.05,
      pulseDelay: `${0.4 + index * 0.3}s`
    })
    
    links.value.push({ from: 'BS', to: id })
  })
  
  layoutNodes()
  renderTopology()
}

// 布局节点
function layoutNodes() {
  const center = getOrbitCenter()
  const radiusBase = 120
  const angleStep = 2.399963229728653
  const edges = nodes.value.filter(node => node.type === 'edge')
  const padding = 60
  const maxRadius = Math.max(
    60,
    Math.min(
      center.x - padding,
      VIEWBOX.width - padding - center.x,
      center.y - padding,
      VIEWBOX.height - padding - center.y
    )
  )

  edges.forEach((node, index) => {
    const radius = Math.min(radiusBase + (index % 3) * 28, maxRadius)
    const angle = index * angleStep + (index % 2) * 0.25
    node.orbitRadius = node.orbitRadius || radius
    node.orbitAngle = node.orbitAngle || angle
    node.x = center.x + Math.cos(node.orbitAngle) * node.orbitRadius
    node.y = center.y + Math.sin(node.orbitAngle) * node.orbitRadius
  })
}

function getOrbitCenter() {
  const core = nodes.value.find(node => node.type === 'core')
  return core ? { x: core.x, y: core.y } : { x: 400, y: 200 }
}

// 渲染拓扑图
function renderTopology() {
  if (!topologySvg.value) return
  
  const svg = topologySvg.value
  svg.innerHTML = ''
  nodeElements.clear()
  linkElements.length = 0

  const ns = 'http://www.w3.org/2000/svg'
  
  // 添加滤镜定义
  const defs = document.createElementNS(ns, 'defs')
  defs.innerHTML = `
    <filter id="glow-core" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <filter id="glow-edge" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  `
  svg.appendChild(defs)

  // 渲染连接线
  links.value.forEach(link => {
    const line = document.createElementNS(ns, 'line')
    line.setAttribute('stroke', '#9cc3ff')
    line.setAttribute('stroke-width', '2')
    line.setAttribute('stroke-opacity', '0.65')
    line.dataset.from = link.from
    line.dataset.to = link.to
    svg.appendChild(line)
    linkElements.push(line)
  })

  // 渲染节点
  nodes.value.forEach(node => {
    const group = document.createElementNS(ns, 'g')
    group.setAttribute('class', 'node-group')
    group.dataset.id = node.id
    group.style.transformOrigin = `${node.x}px ${node.y}px`
    group.style.animation = 'pulse 4s ease-in-out infinite'
    group.style.animationDelay = node.pulseDelay || '0s'

    const circle = document.createElementNS(ns, 'circle')
    circle.setAttribute('r', node.type === 'core' ? 42 : 34)
    circle.setAttribute('fill', node.type === 'core' ? '#3b0c75' : '#0b2b4b')
    circle.setAttribute('stroke', node.type === 'core' ? '#c084fc' : '#7dd3fc')
    circle.setAttribute('stroke-width', '3')
    circle.setAttribute('filter', node.type === 'core' ? 'url(#glow-core)' : 'url(#glow-edge)')

    const label = document.createElementNS(ns, 'text')
    label.setAttribute('text-anchor', 'middle')
    label.setAttribute('fill', '#eaf2ff')
    label.setAttribute('font-size', node.type === 'core' ? '16' : '12')
    label.setAttribute('font-family', '"SF Pro Display", "PingFang SC", sans-serif')
    label.textContent = node.label

    group.appendChild(circle)
    group.appendChild(label)
    
    // 添加拖拽事件
    if (node.type === 'edge') {
      group.style.cursor = 'grab'
      group.onpointerdown = (e) => startDrag(e, node.id)
    }
    
    svg.appendChild(group)
    nodeElements.set(node.id, { group, circle, label })
  })

  updateTopologyPositions()
}

// 更新拓扑位置
function updateTopologyPositions() {
  nodes.value.forEach(node => {
    const element = nodeElements.get(node.id)
    if (!element) return
    element.circle.setAttribute('cx', node.x)
    element.circle.setAttribute('cy', node.y)
    element.label.setAttribute('x', node.x)
    element.label.setAttribute('y', node.y + 4)
    element.group.style.transformOrigin = `${node.x}px ${node.y}px`
  })

  linkElements.forEach(line => {
    const from = nodes.value.find(node => node.id === line.dataset.from)
    const to = nodes.value.find(node => node.id === line.dataset.to)
    if (!from || !to) return
    line.setAttribute('x1', from.x)
    line.setAttribute('y1', from.y)
    line.setAttribute('x2', to.x)
    line.setAttribute('y2', to.y)
  })
}

// 更新轨道位置（动画）
function updateOrbitPositions(dt) {
  if (!dt || !nodeElements.size) return
  const center = getOrbitCenter()
  
  nodes.value.forEach(node => {
    if (node.type !== 'edge') return
    if (dragState && dragState.id === node.id) return
    
    node.orbitAngle += node.orbitSpeed * dt
    node.x = center.x + Math.cos(node.orbitAngle) * node.orbitRadius
    node.y = center.y + Math.sin(node.orbitAngle) * node.orbitRadius
  })
  
  updateTopologyPositions()
}

// 动画循环
function tick(timestamp) {
  const dt = lastTime ? (timestamp - lastTime) / 1000 : 0
  lastTime = timestamp
  
  updateOrbitPositions(dt)
  
  animationFrameId = requestAnimationFrame(tick)
}

// 拖拽相关
function startDrag(event, nodeId) {
  const node = nodes.value.find(item => item.id === nodeId)
  if (!node || node.type === 'core') return

  const point = getSvgPoint(event)
  dragState = {
    id: nodeId,
    offsetX: point.x - node.x,
    offsetY: point.y - node.y
  }
  
  const element = nodeElements.get(nodeId)
  if (element) {
    element.group.classList.add('dragging')
    element.group.style.cursor = 'grabbing'
  }
  
  event.currentTarget.setPointerCapture(event.pointerId)
}

function handlePointerMove(event) {
  if (!dragState) return
  
  const node = nodes.value.find(item => item.id === dragState.id)
  if (!node) return
  
  const point = getSvgPoint(event)
  node.x = clamp(point.x - dragState.offsetX, 60, VIEWBOX.width - 60)
  node.y = clamp(point.y - dragState.offsetY, 80, VIEWBOX.height - 60)
  
  const center = getOrbitCenter()
  node.orbitAngle = Math.atan2(node.y - center.y, node.x - center.x)
  node.orbitRadius = Math.hypot(node.x - center.x, node.y - center.y)
  
  updateTopologyPositions()
}

function endDrag(event) {
  if (!dragState) return
  
  const element = nodeElements.get(dragState.id)
  if (element) {
    element.group.classList.remove('dragging')
    element.group.style.cursor = 'grab'
  }
  
  dragState = null
}

function getSvgPoint(event) {
  if (!topologySvg.value) return { x: 0, y: 0 }
  const rect = topologySvg.value.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * VIEWBOX.width
  const y = ((event.clientY - rect.top) / rect.height) * VIEWBOX.height
  return { x, y }
}

// 添加节点
function handleAddNode() {
  const ip = newNodeIp.value.trim()
  if (!ip) return
  
  const exists = networkMetrics.value.some(drone => 
    (drone.ip || drone.client_id) === ip
  )
  if (exists) {
    newNodeIp.value = ''
    return
  }

  // 添加新的模拟节点
  networkMetrics.value.push({
    ip: ip,
    client_id: ip,
    quality: 2,
    bandwidth: 3.2,
    download_speed: 2600,
    upload_speed: 2400,
    packet_loss: 0.1,
    latency: 0.35,
    jitter: 6.2,
    load: 30,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  })

  newNodeIp.value = ''
  syncNodesFromDrones()
}

// 监听数据变化
watch(networkMetrics, () => {
  syncNodesFromDrones()
}, { deep: true })

// 生命周期
onMounted(async () => {
  console.log('CellularCommPage mounted')
  
  await fetchNetworkMetrics()
  syncNodesFromDrones()
  
  // 启动动画
  animationFrameId = requestAnimationFrame(tick)
  
  // 启动自动刷新（每3秒）
  refreshInterval = setInterval(async () => {
    await fetchNetworkMetrics()
  }, 3000)
})

onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})
</script>

<style scoped>
.cellular-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px 80px;
  display: grid;
  gap: 28px;
  background: radial-gradient(1200px 600px at 10% 10%, #ffffff 0%, #f2f5fa 45%, #edf2f9 100%);
  min-height: 100vh;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 12px;
  color: #5f6b7a;
  margin-bottom: 10px;
}

h1 {
  font-size: clamp(28px, 3.5vw, 42px);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: #0a0a0a;
}

.subhead {
  margin-top: 10px;
  color: #5f6b7a;
  font-size: 16px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: #ffffff;
  border: 1px solid #e3e7ef;
  padding: 10px 16px;
  border-radius: 999px;
  box-shadow: 0 18px 50px rgba(12, 24, 48, 0.12);
  font-size: 14px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #35c759;
  box-shadow: 0 0 8px rgba(53, 199, 89, 0.8);
}

.card {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 18px 50px rgba(12, 24, 48, 0.12);
  border: 1px solid rgba(227, 231, 239, 0.7);
  overflow: hidden;
}

.card-header {
  padding: 24px 28px 10px;
}

.card-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #0a0a0a;
}

.card-header p {
  margin-top: 6px;
  color: #5f6b7a;
  font-size: 14px;
}

.table-wrap {
  overflow-x: auto;
  padding: 0 16px 24px;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 880px;
}

thead th {
  font-size: 13px;
  font-weight: 600;
  color: #2c3b52;
  text-align: left;
  padding: 16px 12px;
  background: linear-gradient(180deg, rgba(240, 244, 250, 0.95), rgba(229, 235, 244, 0.9));
  border-bottom: 1px solid #e3e7ef;
}

tbody td {
  padding: 14px 12px;
  font-size: 13px;
  color: #132033;
  border-bottom: 1px solid #e3e7ef;
  white-space: nowrap;
}

tbody tr:nth-child(even) {
  background: #f7f9fc;
}

tbody tr:hover {
  background: #eef4ff;
}

.topo-card {
  background: linear-gradient(180deg, #0c1626 0%, #0f1f33 60%, #121a2b 100%);
  color: #e8f1ff;
}

.topo-card .card-header h2,
.topo-card .card-header p {
  color: #e8f1ff;
}

.topo-card .card-header p {
  color: rgba(232, 241, 255, 0.65);
}

.node-form {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.node-form input {
  flex: 1 1 220px;
  background: rgba(10, 20, 36, 0.55);
  border: 1px solid rgba(120, 150, 200, 0.35);
  border-radius: 999px;
  padding: 10px 16px;
  color: #e8f1ff;
  font-size: 14px;
  outline: none;
}

.node-form input::placeholder {
  color: rgba(232, 241, 255, 0.5);
}

.node-form button {
  border: 0;
  border-radius: 999px;
  padding: 10px 20px;
  background: linear-gradient(120deg, #3b82f6, #6366f1);
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 10px 30px rgba(59, 130, 246, 0.35);
  transition: filter 0.2s;
}

.node-form button:hover {
  filter: brightness(1.05);
}

.topo-wrap {
  padding: 12px 20px 26px;
}

svg {
  width: 100%;
  height: auto;
  aspect-ratio: 800 / 420;
  display: block;
  min-height: 320px;
  background: radial-gradient(circle at 20% 20%, rgba(78, 144, 255, 0.25), transparent 45%),
    radial-gradient(circle at 80% 70%, rgba(144, 81, 255, 0.18), transparent 50%),
    linear-gradient(180deg, rgba(8, 14, 24, 0.6), rgba(7, 12, 20, 0.9));
  border-radius: 18px;
  border: 1px solid rgba(110, 140, 190, 0.15);
}

.node-group.dragging {
  cursor: grabbing !important;
}

.legend {
  display: flex;
  gap: 18px;
  padding: 0 28px 24px;
  font-size: 13px;
  color: rgba(232, 241, 255, 0.75);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.legend-dot.core {
  background: #a855f7;
  box-shadow: 0 0 12px rgba(168, 85, 247, 0.8);
}

.legend-dot.edge {
  background: #60a5fa;
  box-shadow: 0 0 12px rgba(96, 165, 250, 0.8);
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.9;
  }
  50% {
    transform: scale(1.05);
    opacity: 1;
  }
}

@media (max-width: 860px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-pill {
    align-self: flex-start;
  }

  .legend {
    flex-direction: column;
    gap: 8px;
  }
}
</style>





