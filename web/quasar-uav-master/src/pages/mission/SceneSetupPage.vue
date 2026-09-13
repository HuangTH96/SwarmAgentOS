<template>
  <q-page class="scene-setup-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <q-btn flat icon="arrow_back" label="返回" @click="goBack" />
      <div class="toolbar-title">任务场景设置</div>
      <q-space />
      <q-btn flat label="保存配置" color="primary" @click="saveConfiguration" :disable="!hasRoutes" />
      <q-btn flat label="导出配置" @click="exportConfiguration" :disable="!hasRoutes" />
    </div>

    <!-- 主内容区域 -->
    <div class="content-wrapper">
      <!-- 左侧地图区域 -->
      <div class="map-container">
        <!-- 地图加载提示 -->
        <div v-if="!mapInstance" class="map-loading">
          <q-spinner color="primary" size="50px" />
          <div class="loading-text">正在加载地图...</div>
        </div>
        
        <div id="amap-container" ref="mapContainer"></div>
        
        <!-- 地图工具栏 -->
        <MapToolbar
          v-if="mapInstance"
          :edit-mode="editMode"
          :no-fly-zone-count="noFlyZones.length"
          :waypoint-count="waypoints.length"
          @add-nofly-zone="startAddNoFlyZone"
          @add-waypoint="startAddWaypoint"
          @edit-start="startEditStart"
          @edit-end="startEditEnd"
          @generate-route="generateRoute"
          @cancel-edit="cancelEdit"
        />
      </div>

      <!-- 右侧参数面板 -->
      <ParameterPanel
        :task-data="taskData"
        :no-fly-zones="noFlyZones"
        :waypoints="waypoints"
        :routes="routes"
        :selected-item="selectedItem"
        @update-nofly-zone="updateNoFlyZone"
        @delete-nofly-zone="deleteNoFlyZone"
        @update-waypoint="updateWaypoint"
        @delete-waypoint="deleteWaypoint"
        @select-item="selectItem"
      />
    </div>

    <!-- 加载提示 -->
    <q-dialog v-model="loading" persistent>
      <q-card>
        <q-card-section class="row items-center">
          <q-spinner color="primary" size="3em" />
          <span class="q-ml-md">{{ loadingMessage }}</span>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>


<script>
import { ref, reactive, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import MapToolbar from 'src/components/mission/MapToolbar.vue'
import ParameterPanel from 'src/components/mission/ParameterPanel.vue'
import { api } from 'src/boot/axios'
import { useMissionStore } from 'src/stores/mission'

export default {
  name: 'SceneSetupPage',
  components: {
    MapToolbar,
    ParameterPanel
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const $q = useQuasar()
    const missionStore = useMissionStore()

    // 状态管理
    const mapContainer = ref(null)
    const mapInstance = ref(null)
    const taskData = ref(null)
    const editMode = ref(null) // 'nofly-zone', 'waypoint', 'start', 'end', null
    const loading = ref(false)
    const loadingMessage = ref('')

    // 地图对象
    const startMarker = ref(null)
    const endMarker = ref(null)
    const noFlyZones = ref([])
    const waypoints = ref([])
    const routes = ref([])
    const selectedItem = ref(null)

    // 计算属性
    const hasRoutes = computed(() => routes.value.length > 0)

    // 初始化地图
    const initMap = () => {
      console.log('开始初始化地图...')
      console.log('window.AMap:', window.AMap)
      console.log('DOM元素:', document.getElementById('amap-container'))
      
      if (!window.AMap) {
        console.error('高德地图 API 未加载')
        $q.notify({
          type: 'negative',
          message: '高德地图加载失败，请检查网络连接或刷新页面'
        })
        return
      }

      try {
        // 创建地图实例
        console.log('创建地图实例...')
        const map = new window.AMap.Map('amap-container', {
          zoom: 15,
          center: [118.8255, 31.9370], // 南航将军路校区
          mapStyle: 'amap://styles/normal',
          viewMode: '2D'
        })

        console.log('地图实例创建成功:', map)
        
        // 立即设置mapInstance，这样loading就会消失
        mapInstance.value = map

        // 等待地图加载完成后显示通知
        map.on('complete', () => {
          console.log('地图加载完成')
          $q.notify({
            type: 'positive',
            message: '地图加载成功',
            position: 'top'
          })
        })

        // 添加地图点击事件
        map.on('click', handleMapClick)
        
      } catch (error) {
        console.error('地图初始化失败:', error)
        $q.notify({
          type: 'negative',
          message: '地图初始化失败: ' + error.message
        })
      }
    }


    // 处理地图点击
    const handleMapClick = (e) => {
      const lnglat = e.lnglat
      
      if (editMode.value === 'start') {
        updateStartPoint(lnglat.lng, lnglat.lat)
        editMode.value = null
      } else if (editMode.value === 'end') {
        updateEndPoint(lnglat.lng, lnglat.lat)
        editMode.value = null
      } else if (editMode.value === 'nofly-zone') {
        addNoFlyZone(lnglat.lng, lnglat.lat)
        editMode.value = null
      } else if (editMode.value === 'waypoint') {
        addWaypoint(lnglat.lng, lnglat.lat)
        editMode.value = null
      }
    }

    // 更新起点
    const updateStartPoint = (lng, lat) => {
      console.log('updateStartPoint 被调用:', lng, lat)
      
      // 验证坐标有效性
      if (!lng || !lat || isNaN(lng) || isNaN(lat)) {
        console.error('无效的起点坐标:', lng, lat)
        return
      }
      
      // 确保taskData存在start_point属性
      if (!taskData.value.start_point) {
        taskData.value.start_point = {}
      }
      
      if (startMarker.value) {
        startMarker.value.setPosition([lng, lat])
        console.log('起点标记位置已更新')
      } else {
        try {
          startMarker.value = new window.AMap.Marker({
            position: [lng, lat],
            draggable: true,
            title: '起点',
            label: {
              content: '起点',
              offset: new window.AMap.Pixel(0, -30),
              direction: 'top'
            }
          })
          
          // 设置红色图标 - 使用更可靠的图标
          const icon = new window.AMap.Icon({
            size: new window.AMap.Size(25, 34),
            image: 'https://webapi.amap.com/theme/v1.3/markers/n/start.png',
            imageSize: new window.AMap.Size(25, 34)
          })
          startMarker.value.setIcon(icon)
          
          mapInstance.value.add(startMarker.value)
          
          startMarker.value.on('dragend', (e) => {
            const pos = e.target.getPosition()
            taskData.value.start_point = { lng: pos.lng, lat: pos.lat }
          })
          
          console.log('起点标记创建成功，位置:', [lng, lat])
        } catch (error) {
          console.error('创建起点标记失败:', error)
        }
      }
      
      taskData.value.start_point = { lng, lat }
      $q.notify({ type: 'positive', message: '起点已更新' })
    }

    // 更新终点
    const updateEndPoint = (lng, lat) => {
      console.log('updateEndPoint 被调用:', lng, lat)
      
      // 验证坐标有效性
      if (!lng || !lat || isNaN(lng) || isNaN(lat)) {
        console.error('无效的终点坐标:', lng, lat)
        return
      }
      
      // 确保taskData存在end_point属性
      if (!taskData.value.end_point) {
        taskData.value.end_point = {}
      }
      
      if (endMarker.value) {
        endMarker.value.setPosition([lng, lat])
        console.log('终点标记位置已更新')
      } else {
        try {
          endMarker.value = new window.AMap.Marker({
            position: [lng, lat],
            draggable: true,
            title: '终点',
            label: {
              content: '终点',
              offset: new window.AMap.Pixel(0, -30),
              direction: 'top'
            }
          })
          
          // 设置绿色图标 - 使用更可靠的图标
          const icon = new window.AMap.Icon({
            size: new window.AMap.Size(25, 34),
            image: 'https://webapi.amap.com/theme/v1.3/markers/n/end.png',
            imageSize: new window.AMap.Size(25, 34)
          })
          endMarker.value.setIcon(icon)
          
          mapInstance.value.add(endMarker.value)
          
          endMarker.value.on('dragend', (e) => {
            const pos = e.target.getPosition()
            taskData.value.end_point = { lng: pos.lng, lat: pos.lat }
          })
          
          console.log('终点标记创建成功，位置:', [lng, lat])
        } catch (error) {
          console.error('创建终点标记失败:', error)
        }
      }
      
      taskData.value.end_point = { lng, lat }
      $q.notify({ type: 'positive', message: '终点已更新' })
    }


    // 添加禁飞区（矩形）
    const addNoFlyZone = (lng, lat) => {
      if (noFlyZones.value.length >= 10) {
        $q.notify({ type: 'warning', message: '最多只能添加10个禁飞区' })
        return
      }

      // 默认矩形大小：200米 x 200米
      const sizeInMeters = 200
      const sizeLat = sizeInMeters / 111000 // 纬度方向
      const sizeLng = sizeInMeters / (111000 * Math.cos(lat * Math.PI / 180)) // 经度方向

      const bounds = [
        [lng - sizeLng / 2, lat - sizeLat / 2], // 西南角
        [lng + sizeLng / 2, lat - sizeLat / 2], // 东南角
        [lng + sizeLng / 2, lat + sizeLat / 2], // 东北角
        [lng - sizeLng / 2, lat + sizeLat / 2], // 西北角
      ]

      const rectangle = new window.AMap.Polygon({
        path: bounds,
        fillColor: '#ff0000',
        fillOpacity: 0.3,
        strokeColor: '#ff0000',
        strokeWeight: 2,
        draggable: true,
        cursor: 'move'
      })

      const zone = {
        id: Date.now(),
        rectangle,
        bounds: {
          north: lat + sizeLat / 2,
          south: lat - sizeLat / 2,
          east: lng + sizeLng / 2,
          west: lng - sizeLng / 2
        },
        center: { lng, lat },
        width: sizeInMeters,
        height: sizeInMeters,
        name: `禁飞区${noFlyZones.value.length + 1}`
      }

      rectangle.on('click', () => selectItem(zone))
      rectangle.on('dragend', (e) => {
        const path = e.target.getPath()
        if (path && path.length > 0) {
          const lngs = path.map(p => p.lng)
          const lats = path.map(p => p.lat)
          zone.bounds = {
            north: Math.max(...lats),
            south: Math.min(...lats),
            east: Math.max(...lngs),
            west: Math.min(...lngs)
          }
          zone.center = {
            lng: (zone.bounds.east + zone.bounds.west) / 2,
            lat: (zone.bounds.north + zone.bounds.south) / 2
          }
        }
      })

      mapInstance.value.add(rectangle)
      noFlyZones.value.push(zone)
      $q.notify({ type: 'positive', message: '禁飞区已添加' })
    }

    // 添加必经点
    const addWaypoint = (lng, lat) => {
      if (waypoints.value.length >= 20) {
        $q.notify({ type: 'warning', message: '最多只能添加20个必经点' })
        return
      }

      try {
        const marker = new window.AMap.Marker({
          position: [lng, lat],
          draggable: true,
          title: `必经点${waypoints.value.length + 1}`
        })
        
        // 设置蓝色图标
        marker.setIcon('//a.amap.com/jsapi_demos/static/demo-center/icons/poi-marker-default.png')

        const waypoint = {
          id: Date.now(),
          marker,
          lat,
          lng,
          sequence: waypoints.value.length,
          name: `必经点${waypoints.value.length + 1}`
        }

        marker.on('click', () => selectItem(waypoint))
        marker.on('dragend', (e) => {
          const pos = e.target.getPosition()
          waypoint.lat = pos.lat
          waypoint.lng = pos.lng
        })

        mapInstance.value.add(marker)
        waypoints.value.push(waypoint)
        $q.notify({ type: 'positive', message: '必经点已添加' })
      } catch (error) {
        console.error('添加必经点失败:', error)
        $q.notify({ type: 'negative', message: '添加必经点失败: ' + error.message })
      }
    }

    // 生成航迹
    const generateRoute = async () => {
      // 验证起点和终点
      if (!taskData.value.start_point || !taskData.value.end_point) {
        $q.notify({ type: 'warning', message: '请先设置起点和终点' })
        return
      }

      // 验证起点和终点坐标
      if (!taskData.value.start_point.lat || !taskData.value.start_point.lng) {
        $q.notify({ type: 'warning', message: '起点坐标无效，请重新设置' })
        return
      }

      if (!taskData.value.end_point.lat || !taskData.value.end_point.lng) {
        $q.notify({ type: 'warning', message: '终点坐标无效，请重新设置' })
        return
      }

      loading.value = true
      loadingMessage.value = '正在生成航迹...'

      try {
        const requestData = {
          start_point: {
            latitude: parseFloat(taskData.value.start_point.lat),
            longitude: parseFloat(taskData.value.start_point.lng),
            name: taskData.value.start_point.name || '起点'
          },
          end_point: {
            latitude: parseFloat(taskData.value.end_point.lat),
            longitude: parseFloat(taskData.value.end_point.lng),
            name: taskData.value.end_point.name || '终点'
          },
          number_uavs: parseInt(taskData.value.num_uavs) || 1,
          mission_type: taskData.value.mission_type || 'patrol',
          no_fly_zones: noFlyZones.value.map(zone => ({
            shape: 'rectangle',
            bounds: {
              north: parseFloat(zone.bounds.north),
              south: parseFloat(zone.bounds.south),
              east: parseFloat(zone.bounds.east),
              west: parseFloat(zone.bounds.west)
            },
            name: zone.name || '禁飞区'
          })),
          waypoints: waypoints.value.map(wp => ({
            latitude: parseFloat(wp.lat),
            longitude: parseFloat(wp.lng),
            name: wp.name || `航迹点${wp.sequence + 1}`,
            sequence: parseInt(wp.sequence)
          }))
        }

        console.log('=== 航迹规划请求数据 ===')
        console.log('禁飞区数量:', noFlyZones.value.length)
        console.log('禁飞区详情:', noFlyZones.value)
        console.log('完整请求数据:', JSON.stringify(requestData, null, 2))
        
        const response = await api.post('/api/route-planning/plan', requestData)
        console.log('航迹规划响应:', response.data)
        
        routes.value = response.data.routes
        
        // 在地图上绘制航迹
        drawRoutes(routes.value)
        
        $q.notify({ type: 'positive', message: '航迹生成成功' })
      } catch (error) {
        console.error('生成航迹失败:', error)
        console.error('错误响应:', error.response)
        console.error('错误详情:', error.response?.data)
        
        let errorMessage = '生成航迹失败'
        if (error.response?.status === 404) {
          errorMessage = '航迹规划服务未找到，请检查后端服务'
        } else if (error.response?.status === 422) {
          errorMessage = '参数验证失败: ' + (error.response?.data?.detail || '请检查输入参数')
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.message) {
          errorMessage = error.message
        }
        
        $q.notify({ 
          type: 'negative', 
          message: errorMessage,
          timeout: 5000
        })
      } finally {
        loading.value = false
      }
    }


    // 绘制航迹
    const routePolylines = ref([])
    const drawRoutes = (routesData) => {
      // 清除旧航迹
      routePolylines.value.forEach(polyline => mapInstance.value.remove(polyline))
      routePolylines.value = []

      const colors = ['#1E90FF', '#FF6347', '#32CD32', '#FFD700', '#9370DB']

      routesData.forEach((route, index) => {
        const path = route.waypoints.map(wp => [wp.longitude, wp.latitude])
        
        const polyline = new window.AMap.Polyline({
          path,
          strokeColor: colors[index % colors.length],
          strokeWeight: 4,
          strokeOpacity: 0.8,
          showDir: true
        })

        mapInstance.value.add(polyline)
        routePolylines.value.push(polyline)

        // 添加航迹标签
        if (path.length > 0) {
          const label = new window.AMap.Text({
            text: `UAV ${route.uav_id + 1}: ${Math.round(route.total_distance)}m`,
            position: path[0],
            offset: new window.AMap.Pixel(10, -10),
            style: {
              'background-color': colors[index % colors.length],
              'color': '#fff',
              'padding': '5px 10px',
              'border-radius': '3px',
              'font-size': '12px'
            }
          })
          mapInstance.value.add(label)
          routePolylines.value.push(label)
        }
      })

      // 自动调整地图视野
      if (routesData.length > 0 && routesData[0].waypoints.length > 0) {
        const allPoints = routesData.flatMap(route => 
          route.waypoints.map(wp => [wp.longitude, wp.latitude])
        )
        mapInstance.value.setFitView()
      }
    }

    // 保存配置
    const saveConfiguration = async () => {
      if (!hasRoutes.value) {
        $q.notify({ type: 'warning', message: '请先生成航迹' })
        return
      }

      loading.value = true
      loadingMessage.value = '正在保存配置...'

      try {
        const requestData = {
          name: taskData.value.name || '未命名任务',
          start_point: {
            lat: taskData.value.start_point?.lat || (waypoints.value.length > 0 ? waypoints.value[0].lat : 0),
            lng: taskData.value.start_point?.lng || (waypoints.value.length > 0 ? waypoints.value[0].lng : 0),
            name: taskData.value.start_point?.name || '起点'
          },
          end_point: {
            lat: taskData.value.end_point?.lat || (waypoints.value.length > 0 ? waypoints.value[waypoints.value.length - 1].lat : 0),
            lng: taskData.value.end_point?.lng || (waypoints.value.length > 0 ? waypoints.value[waypoints.value.length - 1].lng : 0),
            name: taskData.value.end_point?.name || '终点'
          },
          num_uavs: taskData.value.num_uavs || 1,
          mission_type: taskData.value.mission_type || 'patrol',
          no_fly_zones: noFlyZones.value.map(zone => ({
            center: zone.center,
            radius: zone.radius,
            name: zone.name
          })),
          waypoints: waypoints.value.map(wp => ({
            lat: wp.lat,
            lng: wp.lng,
            name: wp.name,
            sequence: wp.sequence
          })),
          routes: routes.value.map(route => ({
            uav_index: route.uav_id,
            waypoints: route.waypoints.map(wp => ({
              lat: wp.latitude,
              lng: wp.longitude,
              name: wp.name || `航点${wp.sequence}`,
              sequence: wp.sequence
            })),
            distance: Math.round(route.total_distance)
          }))
        }

        const response = await missionStore.saveMissionToDatabase(requestData)
        
        $q.notify({ 
          type: 'positive', 
          message: '配置保存成功',
          actions: [
            { label: '返回任务规划', color: 'white', handler: () => {
              router.push('/mission/ai-task-planning')
            }},
            { label: '查看详情', color: 'white', handler: () => {
              router.push(`/mission/detail/${response.mission_id}`)
            }}
          ]
        })
      } catch (error) {
        console.error('保存配置失败:', error)
        $q.notify({ type: 'negative', message: '保存配置失败: ' + (error.response?.data?.detail || error.message) })
      } finally {
        loading.value = false
      }
    }

    // 导出配置
    const exportConfiguration = () => {
      const config = {
        name: taskData.value.name || '未命名任务',
        start_point: taskData.value.start_point,
        end_point: taskData.value.end_point,
        num_uavs: taskData.value.num_uavs,
        mission_type: taskData.value.mission_type,
        no_fly_zones: noFlyZones.value.map(zone => ({
          center: zone.center,
          radius: zone.radius,
          name: zone.name
        })),
        waypoints: waypoints.value.map(wp => ({
          lat: wp.lat,
          lng: wp.lng,
          name: wp.name,
          sequence: wp.sequence
        })),
        routes: routes.value
      }

      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mission_${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)

      $q.notify({ type: 'positive', message: '配置已导出' })
    }

    // 其他辅助函数
    const startAddNoFlyZone = () => { editMode.value = 'nofly-zone' }
    const startAddWaypoint = () => { editMode.value = 'waypoint' }
    const startEditStart = () => { editMode.value = 'start' }
    const startEditEnd = () => { editMode.value = 'end' }
    const cancelEdit = () => { editMode.value = null }
    const selectItem = (item) => { selectedItem.value = item }
    
    const updateNoFlyZone = (id, updates) => {
      const zone = noFlyZones.value.find(z => z.id === id)
      if (zone) {
        Object.assign(zone, updates)
        // 更新矩形的边界
        if (updates.bounds && zone.rectangle) {
          const bounds = updates.bounds
          const path = [
            [bounds.west, bounds.south],
            [bounds.east, bounds.south],
            [bounds.east, bounds.north],
            [bounds.west, bounds.north]
          ]
          zone.rectangle.setPath(path)
        }
      }
    }

    const deleteNoFlyZone = (id) => {
      const index = noFlyZones.value.findIndex(z => z.id === id)
      if (index !== -1) {
        // 删除矩形
        mapInstance.value.remove(noFlyZones.value[index].rectangle)
        noFlyZones.value.splice(index, 1)
        $q.notify({ type: 'positive', message: '禁飞区已删除' })
      }
    }

    const updateWaypoint = (id, updates) => {
      const wp = waypoints.value.find(w => w.id === id)
      if (wp) Object.assign(wp, updates)
    }

    const deleteWaypoint = (id) => {
      const index = waypoints.value.findIndex(w => w.id === id)
      if (index !== -1) {
        mapInstance.value.remove(waypoints.value[index].marker)
        waypoints.value.splice(index, 1)
        // 重新排序和更新标题
        waypoints.value.forEach((wp, i) => {
          wp.sequence = i
          wp.name = `必经点${i + 1}`
          wp.marker.setTitle(`必经点${i + 1}`)
        })
        $q.notify({ type: 'positive', message: '必经点已删除' })
      }
    }

    const goBack = () => {
      // 如果是从任务规划页面跳转过来的，保存更新的任务数据到 store
      if (route.query.fromPlanning === 'true' && taskData.value) {
        const updatedMission = {
          ...missionStore.currentMission,
          startPoint: taskData.value.start_point?.name || taskData.value.start_point,
          targetPoint: taskData.value.end_point?.name || taskData.value.end_point,
          droneCount: taskData.value.num_uavs,
          noFlyZones: noFlyZones.value.map(zone => ({
            center: zone.center,
            radius: zone.radius,
            name: zone.name
          })),
          waypoints: waypoints.value.map(wp => ({
            lat: wp.lat,
            lng: wp.lng,
            name: wp.name,
            sequence: wp.sequence
          })),
          routes: routes.value
        }
        missionStore.setCurrentMission(updatedMission)
      }
      router.back()
    }

    // 等待高德地图 API 加载
    const waitForAMap = () => {
      return new Promise((resolve) => {
        if (window.AMap) {
          console.log('高德地图 API 已加载')
          resolve()
        } else {
          console.log('等待高德地图 API 加载...')
          let checkCount = 0
          const checkInterval = setInterval(() => {
            checkCount++
            if (window.AMap) {
              console.log('高德地图 API 加载完成')
              clearInterval(checkInterval)
              resolve()
            } else if (checkCount > 50) {
              // 等待 5 秒后超时
              console.error('高德地图 API 加载超时')
              clearInterval(checkInterval)
              $q.notify({
                type: 'negative',
                message: '高德地图加载超时，请刷新页面重试',
                position: 'top'
              })
              resolve() // 即使超时也 resolve，避免卡住
            }
          }, 100)
        }
      })
    }
    
    // 生命周期
    onMounted(async () => {
      console.log('组件已挂载')
      
      // 从 store 加载任务数据
      missionStore.loadFromLocalStorage()
      
      if (missionStore.currentMission) {
        taskData.value = {
          name: missionStore.currentMission.taskName || missionStore.currentMission.taskType || '未命名任务',
          num_uavs: missionStore.currentMission.droneCount || 1,
          mission_type: getMissionType(missionStore.currentMission.taskType),
          start_point: extractStartPoint(missionStore.currentMission),
          end_point: extractEndPoint(missionStore.currentMission),
          waypoints: missionStore.currentMission.waypoints || []
        }
      } else {
        // 如果 store 中没有数据，尝试从 localStorage 加载（兼容旧代码）
        const taskDataStr = route.query.taskData || localStorage.getItem('currentTaskData')
        if (taskDataStr) {
          try {
            taskData.value = JSON.parse(taskDataStr)
            console.log('任务数据:', taskData.value)
          } catch (e) {
            console.error('解析任务数据失败:', e)
            taskData.value = { num_uavs: 1, mission_type: 'patrol', waypoints: [] }
          }
        } else {
          taskData.value = { num_uavs: 1, mission_type: 'patrol', waypoints: [] }
        }
      }

      // 等待 DOM 更新
      await nextTick()
      
      // 等待高德地图 API 加载
      await waitForAMap()
      
      // 初始化地图
      console.log('准备初始化地图')
      initMap()

      // 初始化地图
      console.log('准备初始化地图')
      initMap()

        // 如果有起点终点，显示标记（延迟到地图初始化完成后）
        setTimeout(() => {
          if (mapInstance.value) {
            console.log('开始处理起点终点和航迹点...')
            console.log('taskData.value:', JSON.stringify(taskData.value, null, 2))
            
            // 处理起点
            let startPoint = taskData.value.start_point
            console.log('起点数据:', startPoint)
            
            if (startPoint && startPoint.lng && startPoint.lat) {
              console.log('使用 start_point 设置起点:', startPoint)
              updateStartPoint(startPoint.lng, startPoint.lat)
            } else if (taskData.value.waypoints && taskData.value.waypoints.length > 0) {
              // 如果起点没有坐标，但有航迹点，使用第一个航迹点作为起点
              const firstWaypoint = taskData.value.waypoints[0]
              console.log('第一个航迹点:', firstWaypoint)
              if (firstWaypoint && firstWaypoint.lat && firstWaypoint.lng) {
                console.log('使用第一个航迹点作为起点:', firstWaypoint)
                updateStartPoint(firstWaypoint.lng, firstWaypoint.lat)
              } else {
                console.warn('第一个航迹点缺少坐标')
              }
            } else {
              console.warn('没有起点数据，也没有航迹点')
            }
            
            // 处理终点
            let endPoint = taskData.value.end_point
            console.log('终点数据:', endPoint)
            
            if (endPoint && endPoint.lng && endPoint.lat) {
              console.log('使用 end_point 设置终点:', endPoint)
              updateEndPoint(endPoint.lng, endPoint.lat)
            } else if (taskData.value.waypoints && taskData.value.waypoints.length > 0) {
              // 如果终点没有坐标，但有航迹点，使用最后一个航迹点作为终点
              const lastWaypoint = taskData.value.waypoints[taskData.value.waypoints.length - 1]
              console.log('最后一个航迹点:', lastWaypoint)
              if (lastWaypoint && lastWaypoint.lat && lastWaypoint.lng) {
                console.log('使用最后一个航迹点作为终点:', lastWaypoint)
                updateEndPoint(lastWaypoint.lng, lastWaypoint.lat)
              } else {
                console.warn('最后一个航迹点缺少坐标')
              }
            } else {
              console.warn('没有终点数据，也没有航迹点')
            }
            
            // 加载 AI 生成的航迹点
            if (taskData.value.waypoints && taskData.value.waypoints.length > 0) {
              console.log('加载 AI 生成的航迹点，数量:', taskData.value.waypoints.length)
              let loadedCount = 0
              
              taskData.value.waypoints.forEach((wp, index) => {
                console.log(`处理航迹点 ${index + 1}:`, wp)
                if (wp && wp.lat && wp.lng) {
                  try {
                    // 先创建 waypoint 对象
                    const waypoint = {
                      id: Date.now() + index,
                      marker: null,
                      lat: wp.lat,
                      lng: wp.lng,
                      sequence: index,
                      name: wp.name || `航迹点${index + 1}`
                    }
                    
                    const marker = new window.AMap.Marker({
                      position: [wp.lng, wp.lat],
                      draggable: true,
                      title: wp.name || `航迹点${index + 1}`,
                      label: {
                        content: wp.name || `航迹点${index + 1}`,
                        offset: new window.AMap.Pixel(0, -30),
                        direction: 'top'
                      }
                    })
                    
                    // 设置蓝色图标
                    const icon = new window.AMap.Icon({
                      size: new window.AMap.Size(25, 34),
                      image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
                      imageSize: new window.AMap.Size(25, 34)
                    })
                    marker.setIcon(icon)
                    
                    // 设置 marker 到 waypoint
                    waypoint.marker = marker
                    
                    // 添加拖拽事件
                    marker.on('dragend', (e) => {
                      const pos = e.target.getPosition()
                      waypoint.lat = pos.lat
                      waypoint.lng = pos.lng
                    })
                    
                    // 添加点击事件
                    marker.on('click', () => selectItem(waypoint))
                    
                    mapInstance.value.add(marker)
                    waypoints.value.push(waypoint)
                    loadedCount++
                    console.log(`航迹点 ${index + 1} 添加成功`)
                  } catch (error) {
                    console.error(`添加航迹点 ${index + 1} 失败:`, error)
                  }
                } else {
                  console.warn(`航迹点 ${index + 1} 缺少坐标:`, wp)
                }
              })
              
              if (loadedCount > 0) {
                $q.notify({ 
                  type: 'positive', 
                  message: `已加载 ${loadedCount} 个 AI 生成的航迹点` 
                })
                
                // 自动调整地图视野以显示所有标记
                try {
                  mapInstance.value.setFitView()
                  console.log('地图视野已调整')
                } catch (error) {
                  console.error('调整地图视野失败:', error)
                }
              }
            } else {
              console.log('没有航迹点数据')
            }
          } else {
            console.error('地图实例不存在')
          }
        }, 800)
    })
    
    // 辅助函数：提取起点
    const extractStartPoint = (task) => {
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

    // 辅助函数：提取终点
    const extractEndPoint = (task) => {
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

    // 辅助函数：转换任务类型
    const getMissionType = (taskType) => {
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

    onBeforeUnmount(() => {
      if (mapInstance.value) {
        mapInstance.value.destroy()
      }
    })

    return {
      mapContainer,
      mapInstance,
      taskData,
      editMode,
      loading,
      loadingMessage,
      noFlyZones,
      waypoints,
      routes,
      selectedItem,
      hasRoutes,
      startAddNoFlyZone,
      startAddWaypoint,
      startEditStart,
      startEditEnd,
      generateRoute,
      cancelEdit,
      selectItem,
      updateNoFlyZone,
      deleteNoFlyZone,
      updateWaypoint,
      deleteWaypoint,
      saveConfiguration,
      exportConfiguration,
      goBack
    }
  }
}
</script>


<style scoped lang="scss">
.scene-setup-page {
  height: calc(100vh - 72px);
  min-height: 560px;
  display: flex;
  flex-direction: column;
  background: #080d12;
  color: #eef7f8;
}

.toolbar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  min-height: 58px;
  background: #0b141b;
  border-bottom: 1px solid rgba(116,169,190,.32);
  box-shadow: 0 8px 24px rgba(0,0,0,.3);
  z-index: 100;
  position: relative;
}

.toolbar-title {
  color: #edf8f8;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: .08em;
  margin-left: 16px;
}
.toolbar :deep(.q-btn) { color: #c9dcdf; border-radius: 2px; }
.toolbar :deep(.q-btn:hover) { color: #33d6e8; background: rgba(51,214,232,.08); }
.toolbar :deep(.q-btn--flat.text-primary) { color: #33d6e8 !important; }

.content-wrapper {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
  background: #080d12;
}

.map-container {
  flex: 1;
  position: relative;
  z-index: 1;
  min-width: 0;
  border-right: 1px solid rgba(116,169,190,.28);
}

#amap-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  filter: saturate(.78) contrast(1.08) brightness(.72);
}

.map-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  z-index: 1000;
  background: rgba(10, 22, 28, .96);
  padding: 20px;
  border: 1px solid rgba(51,214,232,.38);
  border-radius: 2px;
  box-shadow: 0 0 24px rgba(0,0,0,.4), inset 2px 0 #33d6e8;
}

.loading-text {
  font-size: 16px;
  color: #cce3e5;
}
@media (max-width: 860px) {
  .scene-setup-page { height: auto; min-height: calc(100vh - 72px); }
  .content-wrapper { flex-direction: column; overflow: visible; }
  .map-container { min-height: 55vh; border-right: 0; border-bottom: 1px solid rgba(116,169,190,.28); }
  .parameter-panel { width: 100%; min-height: 300px; }
  #amap-container { min-height: 55vh; }
}
</style>
