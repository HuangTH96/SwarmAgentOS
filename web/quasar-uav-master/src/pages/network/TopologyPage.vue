<template>
  <q-page class="topology-page">
    <!-- 标题栏 -->
    <div class="page-header q-pa-md">
      <div class="text-h5">网络拓扑</div>
      <div class="text-caption text-grey-7">实时显示无人机网络连接关系</div>
    </div>

    <!-- 拓扑图区域 (70%高度) -->
    <div class="topology-graph-container">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-state">
        <q-spinner-dots color="primary" size="50px" />
        <div class="text-subtitle1 text-grey-7 q-mt-md">正在加载网络拓扑...</div>
      </div>
      
      <div v-else ref="cytoscapeContainer" class="cytoscape-canvas"></div>
      
      <!-- 空状态提示 -->
      <div v-if="!isLoading && droneList.length === 0" class="empty-state">
        <q-icon name="device_hub" size="64px" color="grey-5" />
        <div class="text-h6 text-grey-6 q-mt-md">暂无无人机数据</div>
        <div class="text-caption text-grey-5">等待无人机连接...</div>
      </div>
      
      <!-- 网络统计信息 -->
      <div v-if="!isLoading && droneList.length > 0" class="topology-stats">
        <q-chip 
          v-for="group in topologyData.groups" 
          :key="group.segment"
          :color="getColorName(group.color)"
          text-color="white"
          icon="router"
          size="sm"
        >
          {{ group.segment === 'unknown' ? '未知' : group.segment + '.x' }}: {{ group.count }}台
        </q-chip>
      </div>
    </div>

    <!-- IP信息面板 (30%高度) -->
    <div class="ip-info-panel">
      <div class="panel-header">
        <q-icon name="info" size="20px" class="q-mr-sm" />
        <span class="text-subtitle1">IP 信息列表</span>
        <q-space />
        <q-badge :label="`${droneList.length} 架无人机`" color="primary" />
      </div>
      
      <div class="panel-content">
        <div v-if="droneList.length === 0" class="text-center text-grey-6 q-pa-md">
          暂无数据
        </div>
        
        <!-- 按网络组显示IP信息 -->
        <div v-else>
          <div 
            v-for="(group, index) in topologyData.groups" 
            :key="group.segment"
            class="network-group"
          >
            <!-- 网络组标题 -->
            <div class="group-header" :style="{ borderLeftColor: group.color }">
              <q-icon name="router" :color="getColorName(group.color)" class="q-mr-sm" />
              <span class="text-weight-medium">
                网络段: {{ group.segment === 'unknown' ? '未知网络' : group.segment + '.x' }}
              </span>
              <q-space />
              <q-badge :label="`${group.count} 台`" :color="getColorName(group.color)" />
            </div>
            
            <!-- 该组的无人机列表 -->
            <div class="group-drones">
              <div 
                v-for="drone in getDronesInGroup(group.segment)" 
                :key="drone.id"
                class="drone-item"
                :class="{ 'selected': selectedNodeId === drone.id }"
                @click="handleDroneClick(drone.id)"
              >
                <div class="drone-id">
                  <q-icon name="flight" size="18px" class="q-mr-xs" />
                  <span class="text-weight-medium">{{ drone.id }}</span>
                </div>
                <div class="drone-ip">
                  <q-icon name="language" size="16px" class="q-mr-xs text-grey-6" />
                  <span class="text-grey-7">{{ drone.ip }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useDroneStore } from 'src/stores/drone'
import cytoscape from 'cytoscape'

// 获取 Drone Store
const droneStore = useDroneStore()
const droneList = computed(() => droneStore.droneList || [])

// 引用
const cytoscapeContainer = ref(null)
let cy = null // Cytoscape 实例
const selectedNodeId = ref(null) // 当前选中的节点ID
const isLoading = ref(true) // 加载状态

// 计算拓扑数据
const topologyData = computed(() => generateTopologyData())

// 防抖定时器
let renderDebounceTimer = null

/**
 * 解析IP地址，提取网络段（前三段）
 * @param {string} ip - IP地址字符串
 * @returns {string} 网络段，格式为 "X.X.X"，无效时返回 "unknown"
 */
function parseNetworkSegment(ip) {
  // 处理空值和无效输入
  if (!ip || typeof ip !== 'string') {
    return 'unknown'
  }

  // 去除首尾空格
  ip = ip.trim()

  // 验证IP地址格式并提取前三段
  const ipPattern = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/
  const match = ip.match(ipPattern)

  if (!match) {
    return 'unknown'
  }

  // 验证每段数字在0-255范围内
  const segments = [match[1], match[2], match[3], match[4]]
  for (const segment of segments) {
    const num = parseInt(segment, 10)
    if (num < 0 || num > 255) {
      return 'unknown'
    }
  }

  // 返回前三段作为网络段
  return `${match[1]}.${match[2]}.${match[3]}`
}

/**
 * 根据网络段对无人机进行分组
 * @returns {Map<string, Array>} 网络段到无人机列表的映射
 */
function groupDronesByNetwork() {
  const groups = new Map()

  console.log('Grouping drones, droneList:', droneList.value)

  // 遍历所有无人机
  droneList.value.forEach(drone => {
    console.log('Processing drone:', drone)
    // 获取无人机的IP地址（可能在不同的字段中）
    const ip = drone.ip || drone.address || drone.client_ip || null
    console.log('Drone IP:', ip)
    
    // 解析网络段
    const segment = parseNetworkSegment(ip)
    console.log('Network segment:', segment)
    
    // 将无人机添加到对应的网络组
    if (!groups.has(segment)) {
      groups.set(segment, [])
    }
    
    groups.get(segment).push({
      ...drone,
      ip: ip || '未知',
      segment: segment
    })
  })

  console.log('Grouped drones:', groups)
  return groups
}

/**
 * 为不同的网络组分配颜色
 * @param {number} index - 组索引
 * @returns {string} 颜色值
 */
function getGroupColor(index) {
  // Material Design 配色方案
  const colors = [
    '#2196F3', // Blue
    '#4CAF50', // Green
    '#FF9800', // Orange
    '#9C27B0', // Purple
    '#F44336', // Red
    '#00BCD4', // Cyan
    '#FFEB3B', // Yellow
    '#795548', // Brown
    '#607D8B', // Blue Grey
    '#E91E63', // Pink
  ]
  return colors[index % colors.length]
}

/**
 * 生成拓扑图数据结构
 * @returns {Object} 包含 nodes、edges 和 groups 的拓扑数据
 */
function generateTopologyData() {
  const networkGroups = groupDronesByNetwork()
  const nodes = []
  const edges = []
  const groups = []

  let groupIndex = 0

  // 遍历每个网络组
  networkGroups.forEach((drones, segment) => {
    const groupColor = getGroupColor(groupIndex)
    
    // 添加组信息
    groups.push({
      segment: segment,
      color: groupColor,
      count: drones.length
    })

    // 为该组的每个无人机创建节点
    drones.forEach(drone => {
      nodes.push({
        id: drone.id,
        label: drone.id,
        ip: drone.ip,
        segment: segment,
        group: segment,
        color: groupColor
      })
    })

    // 在同一网络组内创建连接边（网状连接）
    // 只有当组内有多个无人机时才创建边
    if (drones.length > 1) {
      for (let i = 0; i < drones.length; i++) {
        for (let j = i + 1; j < drones.length; j++) {
          edges.push({
            source: drones[i].id,
            target: drones[j].id,
            group: segment
          })
        }
      }
    }

    groupIndex++
  })

  return {
    nodes,
    edges,
    groups
  }
}

// 组件挂载时初始化
onMounted(() => {
  console.log('TopologyPage mounted')
  console.log('DroneStore:', droneStore)
  console.log('DroneList:', droneList.value)
  
  // 先设置加载完成，让容器渲染出来
  setTimeout(() => {
    isLoading.value = false
    console.log('Loading complete, droneList:', droneList.value)
    // 等待 DOM 更新后再初始化 Cytoscape
    setTimeout(() => {
      initCytoscape()
    }, 50)
  }, 300)
})

// 组件卸载时清理
onBeforeUnmount(() => {
  // 清理防抖定时器
  if (renderDebounceTimer) {
    clearTimeout(renderDebounceTimer)
  }
  
  // 销毁 Cytoscape 实例
  if (cy) {
    cy.destroy()
    cy = null
  }
})

/**
 * 初始化 Cytoscape 实例
 */
function initCytoscape() {
  if (!cytoscapeContainer.value) {
    console.warn('Cytoscape container not ready, will retry...')
    // 容器还没准备好，稍后重试
    setTimeout(initCytoscape, 100)
    return
  }

  cy = cytoscape({
    container: cytoscapeContainer.value,
    
    // 基本样式
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'label': 'data(label)',
          'width': 60,
          'height': 60,
          'font-family': 'Inter, Noto Sans SC, sans-serif',
          'font-size': 12,
          'font-weight': 600,
          'text-valign': 'center',
          'text-halign': 'center',
          'color': '#333',
          'text-outline-width': 2,
          'text-outline-color': '#fff',
          'border-width': 2,
          'border-color': '#fff',
          'overlay-padding': 6
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#ccc',
          'target-arrow-color': '#ccc',
          'curve-style': 'bezier',
          'opacity': 0.6
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 4,
          'border-color': '#FFD700',
          'overlay-opacity': 0.2
        }
      }
    ],

    // 初始布局
    layout: {
      name: 'grid',
      rows: 1
    },

    // 交互设置
    minZoom: 0.5,
    maxZoom: 2
  })

  console.log('Cytoscape initialized')
  
  // 初始渲染
  renderTopology()
  
  // 设置交互事件
  setupInteractions()
}

/**
 * 设置拓扑图交互功能
 */
function setupInteractions() {
  if (!cy) return

  // 节点点击事件
  cy.on('tap', 'node', (event) => {
    const node = event.target
    const nodeId = node.data('id')
    
    // 取消之前的选中状态
    cy.nodes().removeClass('selected')
    
    // 选中当前节点
    node.addClass('selected')
    selectedNodeId.value = nodeId
    
    console.log('Node clicked:', nodeId)
  })

  // 节点悬停事件 - 显示详细信息
  cy.on('mouseover', 'node', (event) => {
    const node = event.target
    const data = node.data()
    
    // 创建 tooltip（使用 Quasar 的 notify 或自定义 tooltip）
    const tooltipText = `
      ID: ${data.id}
      IP: ${data.ip}
      网络段: ${data.segment}
    `.trim()
    
    // 临时显示在节点上方（可以后续优化为更好的 tooltip）
    node.data('tooltip', tooltipText)
  })

  // 节点移出事件
  cy.on('mouseout', 'node', (event) => {
    const node = event.target
    node.removeData('tooltip')
  })

  // 背景点击事件 - 取消选中
  cy.on('tap', (event) => {
    if (event.target === cy) {
      cy.nodes().removeClass('selected')
      selectedNodeId.value = null
    }
  })
}

/**
 * 渲染拓扑图（带防抖优化）
 */
function renderTopology() {
  if (!cy) {
    console.warn('Cytoscape not initialized')
    return
  }

  const data = topologyData.value
  console.log('Rendering topology with data:', data)

  // 清空现有元素
  cy.elements().remove()

  // 如果没有数据，直接返回
  if (data.nodes.length === 0) {
    console.log('No nodes to render')
    return
  }

  console.log(`Rendering ${data.nodes.length} nodes and ${data.edges.length} edges`)

  // 批量添加元素以提高性能
  cy.batch(() => {
    // 添加节点
    data.nodes.forEach(node => {
      cy.add({
        group: 'nodes',
        data: {
          id: node.id,
          label: node.label,
          ip: node.ip,
          segment: node.segment,
          color: node.color
        }
      })
    })

    // 添加边
    data.edges.forEach(edge => {
      cy.add({
        group: 'edges',
        data: {
          id: `${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target
        }
      })
    })
  })

  // 应用力导向布局
  cy.layout({
    name: 'cose',
    animate: true,
    animationDuration: 500,
    nodeRepulsion: 8000,
    idealEdgeLength: 100,
    edgeElasticity: 100,
    nestingFactor: 1.2,
    gravity: 80,
    numIter: 1000,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0
  }).run()

  // 适应视图
  cy.fit(null, 50)

  console.log(`Topology rendered successfully`)
}

/**
 * 防抖渲染函数
 */
function debouncedRenderTopology() {
  // 清除之前的定时器
  if (renderDebounceTimer) {
    clearTimeout(renderDebounceTimer)
  }
  
  // 设置新的定时器
  renderDebounceTimer = setTimeout(() => {
    renderTopology()
  }, 300) // 300ms 防抖延迟
}

// 监听拓扑数据变化，使用防抖自动重新渲染
watch(topologyData, () => {
  debouncedRenderTopology()
}, { deep: true })

/**
 * 获取指定网络段的无人机列表
 * @param {string} segment - 网络段
 * @returns {Array} 无人机列表
 */
function getDronesInGroup(segment) {
  const groups = groupDronesByNetwork()
  return groups.get(segment) || []
}

/**
 * 处理IP列表中的无人机点击事件
 * @param {string} droneId - 无人机ID
 */
function handleDroneClick(droneId) {
  if (!cy) return
  
  // 取消之前的选中状态
  cy.nodes().removeClass('selected')
  
  // 选中对应节点
  const node = cy.getElementById(droneId)
  if (node.length > 0) {
    node.addClass('selected')
    selectedNodeId.value = droneId
    
    // 将视图聚焦到该节点
    cy.animate({
      center: { eles: node },
      zoom: 1.5
    }, {
      duration: 500
    })
  }
}

/**
 * 根据颜色值获取 Quasar 颜色名称（用于 badge）
 * @param {string} color - 十六进制颜色值
 * @returns {string} Quasar 颜色名称
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
  height: 100vh; /* 使用视口高度 */
  overflow: hidden;
  font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

.page-header {
  flex-shrink: 0;
  border-bottom: 1px solid #e0e0e0;
}

.page-header .text-h5 {
  font-weight: 600;
  letter-spacing: -0.02em;
}

.page-header .text-caption {
  font-weight: 400;
  letter-spacing: 0.01em;
}

/* 拓扑图容器 - 70%高度 */
.topology-graph-container {
  flex: 7;
  position: relative;
  background: #fafafa;
  overflow: hidden;
  min-height: 400px; /* 添加最小高度 */
}

.cytoscape-canvas {
  width: 100%;
  height: 100%;
  min-height: 400px; /* 添加最小高度 */
}

/* 空状态样式 */
.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 10;
}

.empty-state .text-h6 {
  font-weight: 500;
}

.empty-state .text-caption {
  font-weight: 400;
}

/* 加载状态样式 */
.loading-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 10;
}

.loading-state .text-subtitle1 {
  font-weight: 500;
}

/* 拓扑统计信息 */
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

/* IP信息面板 - 30%高度 */
.ip-info-panel {
  flex: 3;
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

.panel-header .text-subtitle1 {
  font-weight: 600;
  letter-spacing: -0.01em;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 网络组样式 */
.network-group {
  margin-bottom: 16px;
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

.group-header .text-weight-medium {
  font-weight: 600;
  letter-spacing: -0.01em;
}

.group-drones {
  padding-left: 8px;
}

.drone-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.drone-item:hover {
  background: #f5f5f5;
  border-color: #2196F3;
  transform: translateX(4px);
}

.drone-item.selected {
  background: #E3F2FD;
  border-color: #2196F3;
  border-width: 2px;
}

.drone-id {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.drone-ip {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}
</style>






