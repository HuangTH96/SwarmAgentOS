<template>
  <q-page class="mesh-page">
    <!-- 标题栏 -->
    <header class="hero">
      <div>
        <p class="eyebrow">自组网系统</p>
        <h1>自组网实时监控</h1>
        <p class="subhead">自组网信息 · 动态互连 · 状态监测</p>
      </div>
      <div class="status-pill">
        <span class="dot"></span>
        <span>自组网节点数: {{ networkMetrics.length }} | 运行中</span>
      </div>
    </header>

    <!-- 节点链路状态表 -->
    <section class="card table-card">
      <div class="card-header">
        <div>
          <h2>节点链路状态表</h2>
          <p>自组网内部数据指标 (10.42.0.x)</p>
        </div>
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
              <td style="font-family: monospace; font-weight: 700;">{{ drone.ip || 'N/A' }}</td>
              <td style="color: #f59e0b">{{ getQualityStars(drone) }}</td>
              <td>{{ formatNumber(drone.bandwidth) }}</td>
              <td>{{ formatNumber(drone.download_speed / 1024) }}</td>
              <td>{{ formatNumber(drone.upload_speed / 1024) }}</td>
              <td :style="{ color: drone.packet_loss > 0 ? '#ef4444' : '' }">
                {{ formatNumber(drone.packet_loss) }}
              </td>
              <td>{{ Math.round(drone.latency || 0) }}</td>
              <td>{{ formatNumber(drone.jitter || 0) }}</td>
              <td>
                <div class="load-bar-container" :title="`当前负载: ${getLoad(drone)}%`">
                  <div 
                    class="load-bar" 
                    :style="{ 
                      width: getLoad(drone) + '%', 
                      background: getLoadColor(drone) 
                    }"
                  ></div>
                </div>
              </td>
              <td :style="{ color: drone.poll === '正常' ? '#10b981' : '#f59e0b' }">
                {{ drone.poll || '正常' }}
              </td>
              <td>{{ drone.interference || '低' }}</td>
              <td style="color: #64748b; font-size: 12px;">{{ formatTime(drone.updated || Date.now()) }}</td>
            </tr>
            <tr v-if="networkMetrics.length === 0">
              <td colspan="12" style="text-align: center; color: #999;">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 空间拓扑视图 -->
    <section class="card topo-card">
      <div class="card-header">
        <div>
          <h2>空间拓扑视图</h2>
          <p>多节点实时分布与连接状态</p>
        </div>
        <form class="node-form" @submit.prevent="handleAddNode">
          <input 
            v-model="newNodeIp" 
            type="text" 
            placeholder="输入节点 IP (如: 10.42.0.88)" 
            autocomplete="off" 
          />
          <button type="submit">接入网络</button>
        </form>
      </div>
      <div class="topo-wrap">
        <svg 
          ref="topologySvg" 
          viewBox="0 0 800 450" 
          role="img" 
          aria-label="自组网拓扑图"
          @pointermove="handlePointerMove"
          @pointerup="endDrag"
        ></svg>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot active"></i>活跃节点</span>
        <span class="legend-item"><i class="legend-line"></i>自组网链路</span>
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
const VIEWBOX = { width: 800, height: 450 }
const CENTER = { x: 400, y: 225 }
const nodes = ref([])
const links = ref([])
const nodeElements = new Map()
const linkElements = []
let dragState = null
let refreshInterval = null
let animationFrameId = null
let lastTime = 0

// 工具函数
function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function formatNumber(value) {
  if (value === null || value === undefined) return '0.0'
  return Number(value).toFixed(1)
}

function formatTime(timestamp) {
  const date = typeof timestamp === 'number' ? new Date(timestamp) : new Date()
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function getQualityStars(drone) {
  const quality = calculateQuality(drone)
  return '★'.repeat(quality) + '☆'.repeat(5 - quality)
}

function calculateQuality(drone) {
  // 根据丢包率和时延计算链路质量 (1-5)
  const loss = drone.packet_loss || 0
  const latency = drone.latency || 0
  const load = getLoad(drone)
  
  if (loss < 0.5 && latency < 20 && load < 50) return 5
  if (loss < 1 && latency < 30 && load < 60) return 4
  if (loss < 2 && latency < 50 && load < 70) return 3
  if (loss < 5 && latency < 100 && load < 80) return 2
  return 1
}

function getLoad(drone) {
  // 根据带宽使用情况估算负载
  const bandwidth = drone.bandwidth || 0
  const usage = (drone.download_speed + drone.upload_speed) / 1024 || 0
  if (bandwidth === 0) return 30
  return Math.round((usage / bandwidth) * 100)
}

function getLoadColor(drone) {
  const load = getLoad(drone)
  if (load > 80) return '#ef4444'
  if (load > 50) return '#f59e0b'
  return '#3b82f6'
}

// 模拟静态数据 - 所有网络节点（包含两个网络段）
const mockMeshData = [
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
    networkMetrics.value = (data && data.length > 0) ? data : mockMeshData
    console.log('Mesh network metrics updated:', networkMetrics.value)
  } catch (error) {
    console.error('Failed to fetch network metrics:', error)
    // 出错时使用模拟数据
    networkMetrics.value = mockMeshData
  }
}

// 同步拓扑数据
function syncTopologyData() {
  const prevNodes = [...nodes.value]
  nodes.value = []
  links.value = []

  networkMetrics.value.forEach((drone, index) => {
    const existing = prevNodes.find(n => n.ip === (drone.ip || drone.client_id))
    const shortId = (drone.ip || drone.client_id).split('.').pop()

    nodes.value.push({
      id: `node-${index}`,
      ip: drone.ip || drone.client_id,
      shortId: shortId,
      x: existing ? existing.x : CENTER.x + (Math.random() - 0.5) * 100,
      y: existing ? existing.y : CENTER.y + (Math.random() - 0.5) * 100,
      orbitAngle: existing ? existing.orbitAngle : index * (Math.PI * 2 / networkMetrics.value.length),
      orbitRadius: existing ? existing.orbitRadius : 160,
      orbitSpeed: (index % 2 === 0 ? 1 : -1) * 0.1
    })
  })

  // 创建全连接网状拓扑
  for (let i = 0; i < nodes.value.length; i++) {
    for (let j = i + 1; j < nodes.value.length; j++) {
      links.value.push({ 
        source: nodes.value[i], 
        target: nodes.value[j],
        opacity: 0.3 + Math.random() * 0.4
      })
    }
  }

  renderSvgElements()
}

// 渲染 SVG 元素
function renderSvgElements() {
  if (!topologySvg.value) return

  const svg = topologySvg.value
  svg.innerHTML = ''
  nodeElements.clear()
  linkElements.length = 0

  const ns = 'http://www.w3.org/2000/svg'

  // 渲染连接线（全连接）
  links.value.forEach(link => {
    const line = document.createElementNS(ns, 'line')
    line.setAttribute('class', 'link-line')
    line.setAttribute('stroke', '#38bdf8')
    line.setAttribute('stroke-width', '2')
    line.setAttribute('stroke-opacity', link.opacity)
    svg.appendChild(line)
    linkElements.push({ el: line, source: link.source, target: link.target })
  })

  // 渲染节点
  nodes.value.forEach(node => {
    const g = document.createElementNS(ns, 'g')
    g.setAttribute('class', 'topo-node')
    g.style.cursor = 'grab'
    g.dataset.id = node.id

    const circle = document.createElementNS(ns, 'circle')
    circle.setAttribute('r', '30')
    circle.setAttribute('fill', '#0f172a')
    circle.setAttribute('stroke', '#38bdf8')
    circle.setAttribute('stroke-width', '2')

    const textId = document.createElementNS(ns, 'text')
    textId.setAttribute('class', 'id-text')
    textId.setAttribute('text-anchor', 'middle')
    textId.setAttribute('dy', '6')
    textId.setAttribute('fill', '#38bdf8')
    textId.setAttribute('font-weight', '700')
    textId.setAttribute('font-size', '16')
    textId.textContent = node.shortId

    const labelGroup = document.createElementNS(ns, 'g')
    const bgRect = document.createElementNS(ns, 'rect')
    bgRect.setAttribute('class', 'ip-tag-rect')
    bgRect.setAttribute('rx', '4')
    bgRect.setAttribute('height', '22')
    bgRect.setAttribute('fill', 'rgba(15, 23, 42, 0.9)')
    bgRect.setAttribute('stroke', '#334155')
    bgRect.setAttribute('stroke-width', '1')

    const textWidth = node.ip.length * 8 + 10
    bgRect.setAttribute('width', textWidth)
    bgRect.setAttribute('x', -textWidth / 2)
    bgRect.setAttribute('y', '40')

    const ipText = document.createElementNS(ns, 'text')
    ipText.setAttribute('class', 'ip-tag-text')
    ipText.setAttribute('text-anchor', 'middle')
    ipText.setAttribute('dy', '56')
    ipText.setAttribute('fill', '#e2e8f0')
    ipText.setAttribute('font-size', '12')
    ipText.setAttribute('font-family', '"JetBrains Mono", monospace')
    ipText.setAttribute('font-weight', '600')
    ipText.textContent = node.ip

    labelGroup.appendChild(bgRect)
    labelGroup.appendChild(ipText)

    g.appendChild(circle)
    g.appendChild(textId)
    g.appendChild(labelGroup)

    g.onpointerdown = (e) => startDrag(e, node)

    svg.appendChild(g)
    nodeElements.set(node.id, { g, node, circle })
  })
}

// 更新位置
function updatePositions() {
  nodeElements.forEach(({ g, node }) => {
    g.setAttribute('transform', `translate(${node.x}, ${node.y})`)
  })

  linkElements.forEach(({ el, source, target }) => {
    el.setAttribute('x1', source.x)
    el.setAttribute('y1', source.y)
    el.setAttribute('x2', target.x)
    el.setAttribute('y2', target.y)
    
    // 随机闪烁效果
    if (Math.random() > 0.95) {
      el.setAttribute('stroke-opacity', 0.3 + Math.random() * 0.6)
    }
  })
}

// 动画循环
function tick(timestamp) {
  const dt = lastTime ? (timestamp - lastTime) / 1000 : 0
  lastTime = timestamp

  // 更新轨道位置
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
    element.circle.setAttribute('stroke-width', '4')
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
    element.circle.setAttribute('stroke-width', '2')
  }

  dragState = null
}

// 添加节点
function handleAddNode() {
  const ip = newNodeIp.value.trim()
  if (!ip) return

  // 验证 IP 格式
  if (!ip.startsWith('10.42.0.')) {
    alert('请输入有效的自组网 IP 地址 (10.42.0.x)')
    return
  }

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
    bandwidth: 15.0,
    download_speed: 5000,
    upload_speed: 5000,
    packet_loss: 0.0,
    latency: 15.0,
    jitter: 5.0,
    poll: '正常',
    interference: '低',
    updated: Date.now()
  })

  newNodeIp.value = ''
  syncTopologyData()
}

// 监听数据变化
watch(networkMetrics, () => {
  syncTopologyData()
}, { deep: true })

// 生命周期
onMounted(async () => {
  console.log('MeshCommPage mounted')

  await fetchNetworkMetrics()
  syncTopologyData()

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
.mesh-page {
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
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
  min-width: 1000px;
}

thead {
  background: #f8fafc;
  color: #475569;
}

th {
  text-align: left;
  padding: 12px 24px;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

td {
  padding: 12px 24px;
  border-bottom: 1px solid #e2e8f0;
  color: #334155;
  white-space: nowrap;
}

tr:last-child td {
  border-bottom: none;
}

tbody tr:hover {
  background: #f1f5f9;
}

.load-bar-container {
  width: 100px;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.load-bar {
  height: 100%;
  transition: width 0.3s ease;
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

.node-form {
  display: flex;
  gap: 8px;
}

.node-form input {
  background: #0f172a;
  border: 1px solid #334155;
  color: #fff;
  padding: 8px 12px;
  border-radius: 4px;
  font-family: inherit;
  font-size: 12px;
  width: 180px;
  outline: none;
}

.node-form input::placeholder {
  color: #64748b;
}

.node-form button {
  background: #2563eb;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  font-family: inherit;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.node-form button:hover {
  background: #1d4ed8;
}

.topo-wrap {
  position: relative;
  height: 450px;
  background-image:
    linear-gradient(rgba(56, 189, 248, 0.15) 1px, transparent 1px),
    linear-gradient(90deg, rgba(56, 189, 248, 0.15) 1px, transparent 1px);
  background-size: 50px 50px;
  overflow: hidden;
}

svg {
  width: 100%;
  height: 100%;
  display: block;
}

.topo-node circle {
  transition: all 0.3s;
}

.topo-node:hover circle {
  fill: #1e293b;
  stroke: #60a5fa;
  stroke-width: 4px;
  filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.8));
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
  width: 8px;
  height: 8px;
  background: #38bdf8;
  border-radius: 50%;
}

.legend-line {
  width: 24px;
  height: 3px;
  background: #38bdf8;
  opacity: 0.6;
}

@media (max-width: 860px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-pill {
    align-self: flex-start;
  }
}
</style>





