<template>
  <q-page class="topology-page">
    <!-- 标题栏 -->
    <div class="page-header q-pa-md">
      <div class="text-h5">网络拓扑</div>
      <div class="text-caption text-grey-7">实时显示无人机网络连接关系和性能指标</div>
    </div>

    <!-- 拓扑图区域 (65%高度) -->
    <div class="topology-graph-container">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-state">
        <q-spinner-dots color="primary" size="50px" />
        <div class="text-subtitle1 text-grey-7 q-mt-md">正在加载网络拓扑...</div>
      </div>
      
      <div v-else ref="cytoscapeContainer" class="cytoscape-canvas"></div>
      
      <!-- 空状态提示 -->
      <div v-if="!isLoading && networkMetrics.length === 0" class="empty-state">
        <q-icon name="device_hub" size="64px" color="grey-5" />
        <div class="text-h6 text-grey-6 q-mt-md">暂无无人机数据</div>
        <div class="text-caption text-grey-5">等待无人机连接...</div>
      </div>
      
      <!-- 网络统计信息 -->
      <div v-if="!isLoading && networkMetrics.length > 0" class="topology-stats">
        <q-chip 
          v-for="group in topologyData.groups" 
          :key="group.segment"
          :color="getColorName(group.color)"
          text-color="white"
          icon="router"
          size="sm"
        >
          {{ group.segment === 'unknown' ? '未知' : group.segment + '.x' }}: {{ group.drones.length }}台
        </q-chip>
      </div>
    </div>

    <!-- 网络指标面板 (35%高度) -->
    <div class="metrics-panel">
      <div class="panel-header">
        <q-icon name="analytics" size="20px" class="q-mr-sm" />
        <span class="text-subtitle1">网络性能指标</span>
        <q-space />
        <q-badge :label="`${networkMetrics.length} 架无人机`" color="primary" />
      </div>
      
      <div class="panel-content">
        <div v-if="networkMetrics.length === 0" class="text-center text-grey-6 q-pa-md">
          暂无数据
        </div>
        
        <!-- 按网络组显示指标 -->
        <div v-else>
          <div 
            v-for="group in topologyData.groups" 
            :key="group.segment"
            class="network-group"
          >
            <!-- 该组的无人机指标表格 -->
            <q-table
              :rows="group.drones"
              :columns="metricsColumns"
              row-key="client_id"
              flat
              dense
              :pagination="{ rowsPerPage: 0 }"
              hide-pagination
              class="metrics-table"
              :row-class="row => selectedNodeId === row.client_id ? 'selected-row' : ''"
              @row-click="(evt, row) => handleDroneClick(row.client_id)"
            >
              <template v-slot:body-cell-client_id="props">
                <q-td :props="props">
                  <div class="drone-id-cell">
                    <q-icon name="flight" size="16px" class="q-mr-xs" />
                    <span class="text-weight-medium">{{ props.value }}</span>
                  </div>
                </q-td>
              </template>
              
              <template v-slot:body-cell-ip="props">
                <q-td :props="props">
                  <div class="ip-cell">
                    <q-icon name="language" size="14px" class="q-mr-xs text-grey-6" />
                    <span>{{ props.value || 'N/A' }}</span>
                  </div>
                </q-td>
              </template>
            </q-table>
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { getNetworkMetrics } from 'src/services/api'
import cytoscape from 'cytoscape'

// 数据
const networkMetrics = ref([])
const cytoscapeContainer = ref(null)
let cy = null
const selectedNodeId = ref(null)
const isLoading = ref(true)
let refreshInterval = null
const previousDataHash = ref(null) // 用于检测数据变化
const previousTopologyHash = ref(null) // 用于检测拓扑结构变化

// 表格列定义
const metricsColumns = [
  { name: 'client_id', label: 'ID', field: 'client_id', align: 'left', sortable: true },
  { name: 'ip', label: 'IP地址', field: 'ip', align: 'left', sortable: true },
  { name: 'bandwidth', label: '带宽', field: 'bandwidth', align: 'right', sortable: true, format: val => `${val} Mbps` },
  { name: 'download_speed', label: '下行', field: 'download_speed', align: 'right', sortable: true, format: val => `${val} KB/s` },
  { name: 'upload_speed', label: '上行', field: 'upload_speed', align: 'right', sortable: true, format: val => `${val} KB/s` },
  { name: 'packet_loss', label: '丢包率', field: 'packet_loss', align: 'right', sortable: true, format: val => `${val}%` },
  { name: 'latency', label: '时延', field: 'latency', align: 'right', sortable: true, format: val => `${val} ms` },
  { name: 'connection_time', label: '连接时间', field: 'connection_time', align: 'right', sortable: true, format: val => formatConnectionTime(val) }
]

// 格式化连接时间
function formatConnectionTime(seconds) {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  return `${Math.floor(seconds / 3600)}小时`
}

/**
 * 计算拓扑结构哈希值（只包含节点ID和连接关系）
 */
function calculateTopologyHash(data) {
  if (!data || data.length === 0) return 'empty'
  
  // 只关注节点ID和IP（拓扑结构），不关注性能指标
  const topologyString = data
    .map(drone => `${drone.client_id}|${drone.ip}`)
    .sort()
    .join('::')
  
  return topologyString
}

/**
 * 检查拓扑结构是否发生变化
 */
function hasTopologyChanged(newData) {
  const newHash = calculateTopologyHash(newData)
  const changed = newHash !== previousTopologyHash.value
  
  if (changed) {
    console.log('拓扑结构发生变化，重新渲染图形')
    previousTopologyHash.value = newHash
  } else {
    console.log('拓扑结构未变化，跳过图形渲染')
  }
  
  return changed
}

/**
 * 计算数据哈希值，用于检测数据是否变化
 */
function calculateDataHash(data) {
  if (!data || data.length === 0) return 'empty'
  
  // 创建一个包含关键字段的字符串
  const hashString = data
    .map(drone => {
      return `${drone.client_id}|${drone.ip}|${drone.bandwidth}|${drone.download_speed}|${drone.upload_speed}|${drone.packet_loss}|${drone.latency}`
    })
    .sort() // 排序确保顺序一致
    .join('::')
  
  return hashString
}

/**
 * 检查数据是否发生变化
 */
function hasDataChanged(newData) {
  const newHash = calculateDataHash(newData)
  const changed = newHash !== previousDataHash.value
  
  if (changed) {
    console.log('数据发生变化，更新表格')
    previousDataHash.value = newHash
  } else {
    console.log('数据未变化，跳过更新')
  }
  
  return changed
}

// 获取网络指标数据
async function fetchNetworkMetrics() {
  try {
    const data = await getNetworkMetrics()
    
    // 检查拓扑结构是否变化
    const topologyChanged = hasTopologyChanged(data)
    
    // 检查数据是否变化
    const dataChanged = hasDataChanged(data)
    
    // 只有数据真正变化时才更新
    if (dataChanged) {
      networkMetrics.value = data
      console.log('Network metrics updated:', data)
      
      // 只有拓扑结构变化时才重新渲染图形
      if (topologyChanged && cy) {
        renderTopology()
      }
    }
  } catch (error) {
    console.error('Failed to fetch network metrics:', error)
  }
}

/**
 * 解析IP地址，提取网络段（前三段）
 */
function parseNetworkSegment(ip) {
  if (!ip || typeof ip !== 'string') return 'unknown'
  
  ip = ip.trim()
  const ipPattern = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/
  const match = ip.match(ipPattern)
  
  if (!match) return 'unknown'
  
  const segments = [match[1], match[2], match[3], match[4]]
  for (const segment of segments) {
    const num = parseInt(segment, 10)
    if (num < 0 || num > 255) return 'unknown'
  }
  
  return `${match[1]}.${match[2]}.${match[3]}`
}

/**
 * 根据网络段对无人机进行分组，并创建BS节点
 */
function groupDronesByNetwork() {
  const groups = new Map()
  
  networkMetrics.value.forEach(drone => {
    const segment = parseNetworkSegment(drone.ip)
    
    if (!groups.has(segment)) {
      groups.set(segment, {
        segment,
        bs_node: {
          id: `bs_${segment}`,
          segment,
          label: `BS ${segment}`,
          drone_count: 0
        },
        drones: [],
        color: ''
      })
    }
    
    const group = groups.get(segment)
    group.drones.push({
      ...drone,
      segment
    })
    group.bs_node.drone_count = group.drones.length
  })
  
  return groups
}

/**
 * 为不同的网络组分配颜色
 */
function getGroupColor(index) {
  const colors = [
    '#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336',
    '#00BCD4', '#FFEB3B', '#795548', '#607D8B', '#E91E63'
  ]
  return colors[index % colors.length]
}

// 计算拓扑数据
const topologyData = computed(() => {
  const networkGroups = groupDronesByNetwork()
  const nodes = []
  const edges = []
  const groups = []
  
  let groupIndex = 0
  
  networkGroups.forEach((group, segment) => {
    const groupColor = getGroupColor(groupIndex)
    group.color = groupColor
    
    groups.push(group)
    
    // 添加BS节点
    nodes.push({
      id: group.bs_node.id,
      type: 'bs',
      label: group.bs_node.label,
      segment,
      color: groupColor,
      drone_count: group.bs_node.drone_count
    })
    
    // 添加无人机节点
    group.drones.forEach(drone => {
      nodes.push({
        id: drone.client_id,
        type: 'drone',
        label: drone.client_id,
        ip: drone.ip,
        segment,
        color: groupColor,
        metrics: drone
      })
      
      // 创建从BS到无人机的边
      edges.push({
        id: `${group.bs_node.id}-${drone.client_id}`,
        source: group.bs_node.id,
        target: drone.client_id,
        color: groupColor
      })
    })
    
    groupIndex++
  })
  
  return { nodes, edges, groups }
})

// 初始化
onMounted(async () => {
  console.log('NetworkTopologyPage mounted')
  
  await fetchNetworkMetrics()
  isLoading.value = false
  
  setTimeout(() => {
    initCytoscape()
  }, 50)
  
  // 启动自动刷新（每3秒）
  refreshInterval = setInterval(async () => {
    await fetchNetworkMetrics()
  }, 3000)
})

// 清理
onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (cy) {
    cy.destroy()
    cy = null
  }
})

/**
 * 初始化 Cytoscape
 */
function initCytoscape() {
  if (!cytoscapeContainer.value) {
    setTimeout(initCytoscape, 100)
    return
  }
  
  cy = cytoscape({
    container: cytoscapeContainer.value,
    
    style: [
      // BS节点样式
      {
        selector: 'node[type="bs"]',
        style: {
          'shape': 'hexagon',
          'width': 80,
          'height': 80,
          'background-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 14,
          'font-weight': 'bold',
          'text-valign': 'center',
          'text-halign': 'center',
          'color': '#fff',
          'text-outline-width': 0,
          'border-width': 3,
          'border-color': '#fff'
        }
      },
      // 无人机节点样式
      {
        selector: 'node[type="drone"]',
        style: {
          'shape': 'ellipse',
          'width': 50,
          'height': 50,
          'background-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 11,
          'font-weight': 600,
          'text-valign': 'center',
          'text-halign': 'center',
          'color': '#333',
          'text-outline-width': 2,
          'text-outline-color': '#fff',
          'border-width': 2,
          'border-color': '#fff'
        }
      },
      // 边样式
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': 'data(color)',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': 'data(color)',
          'curve-style': 'bezier',
          'opacity': 0.7
        }
      },
      // 选中状态
      {
        selector: 'node:selected',
        style: {
          'border-width': 4,
          'border-color': '#FFD700'
        }
      }
    ],
    
    layout: {
      name: 'grid',
      rows: 1
    },
    
    minZoom: 0.5,
    maxZoom: 2
  })
  
  renderTopology()
  setupInteractions()
}

/**
 * 设置交互
 */
function setupInteractions() {
  if (!cy) return
  
  cy.on('tap', 'node', (event) => {
    const node = event.target
    const nodeId = node.data('id')
    const nodeType = node.data('type')
    
    cy.nodes().removeClass('selected')
    node.addClass('selected')
    
    if (nodeType === 'drone') {
      selectedNodeId.value = nodeId
    } else if (nodeType === 'bs') {
      // 高亮该BS节点连接的所有无人机
      const connectedNodes = node.neighborhood('node[type="drone"]')
      connectedNodes.addClass('selected')
    }
  })
  
  cy.on('tap', (event) => {
    if (event.target === cy) {
      cy.nodes().removeClass('selected')
      selectedNodeId.value = null
    }
  })
}

/**
 * 渲染拓扑图
 */
function renderTopology() {
  if (!cy) return
  
  const data = topologyData.value
  cy.elements().remove()
  
  if (data.nodes.length === 0) return
  
  cy.batch(() => {
    data.nodes.forEach(node => {
      cy.add({
        group: 'nodes',
        data: node
      })
    })
    
    data.edges.forEach(edge => {
      cy.add({
        group: 'edges',
        data: edge
      })
    })
  })
  
  // 使用同心圆布局，BS节点在中心
  cy.layout({
    name: 'concentric',
    concentric: (node) => node.data('type') === 'bs' ? 2 : 1,
    levelWidth: () => 1,
    minNodeSpacing: 100,
    animate: true,
    animationDuration: 500
  }).run()
  
  cy.fit(null, 50)
}

// 移除 watch，不再自动监听 topologyData 变化

/**
 * 处理无人机点击
 */
function handleDroneClick(droneId) {
  if (!cy) return
  
  cy.nodes().removeClass('selected')
  const node = cy.getElementById(droneId)
  
  if (node.length > 0) {
    node.addClass('selected')
    selectedNodeId.value = droneId
    
    cy.animate({
      center: { eles: node },
      zoom: 1.5
    }, {
      duration: 500
    })
  }
}

/**
 * 获取颜色名称
 */
function getColorName(color) {
  const colorMap = {
    '#2196F3': 'blue',
    '#4CAF50': 'green',
    '#FF9800': 'orange',
    '#9C27B0': 'purple',
    '#F44336': 'red',
    '#00BCD4': 'cyan',
    '#FFEB3B': 'yellow',
    '#795548': 'brown',
    '#607D8B': 'blue-grey',
    '#E91E63': 'pink'
  }
  return colorMap[color] || 'primary'
}
</script>

<style scoped>
.topology-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.page-header {
  flex-shrink: 0;
  border-bottom: 1px solid #e0e0e0;
}

.topology-graph-container {
  flex: 65;
  position: relative;
  background: #fafafa;
  overflow: hidden;
  min-height: 400px;
}

.cytoscape-canvas {
  width: 100%;
  height: 100%;
}

.empty-state, .loading-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 10;
}

.topology-stats {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-width: 400px;
  z-index: 5;
}

.metrics-panel {
  flex: 35;
  display: flex;
  flex-direction: column;
  border-top: 2px solid #e0e0e0;
  background: white;
}

.panel-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px;
  max-height: calc(35vh - 60px); /* 确保有滚动条 */
}

.network-group {
  margin-bottom: 8px;
}

.group-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #f5f5f5;
  border-left: 4px solid;
  border-radius: 4px;
  margin-bottom: 8px;
}

.metrics-table {
  margin-bottom: 4px;
}

.metrics-table :deep(.selected-row) {
  background: #E3F2FD !important;
}

.metrics-table :deep(tbody tr) {
  cursor: pointer;
}

.metrics-table :deep(tbody tr:hover) {
  background: #f5f5f5;
}

.drone-id-cell, .ip-cell {
  display: flex;
  align-items: center;
}
</style>

