<template>
  <q-card flat bordered class="tech-card text-primary q-pa-sm">
    <!-- 标题 -->
    <q-expansion-item
      v-model="expanded"
      icon="webhook"
      label="当前无人机"
      :caption="curDroneCaption"
      class="tech-expansion"
    >
      <!-- 列表内容 -->
      <q-scroll-area style="height: 150px;">
        <q-list bordered separator>
          <!-- 如果列表为空，显示提示信息 -->
          <q-item v-if="displayedDrones.length === 0">
            <q-item-section>
              <q-item-label caption>等待无人机连接...</q-item-label>
            </q-item-section>
          </q-item>

          <!-- 使用 v-for 遍历无人机列表 -->
          <q-item
            v-for="drone in displayedDrones"
            :key="drone.id"
            clickable
            v-ripple
            :active="drone.id === selectedDroneId"
            @click="handleSelectDrone(drone.id)"
          >
            <q-item-section>
              <q-item-label>{{ drone.name || drone.id }}</q-item-label>
              <q-item-label caption>{{ drone.ip }}</q-item-label>
            </q-item-section>

            <q-item-section side>
              <q-badge :color="getBatteryColor(rawTelemetry[drone.id]?.battery_info?.batteries?.[0]?.percent || 0)">
                🔋 {{ rawTelemetry[drone.id]?.battery_info?.batteries?.[0]?.percent || 'N/A' }}%
              </q-badge>
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-expansion-item>
  </q-card>
</template>

<script setup>
import {ref, computed} from 'vue'
import {useDroneStore} from 'stores/drone'
import {storeToRefs} from 'pinia'

// 折叠控制
const expanded = ref(true)

// store 引入
const droneStore = useDroneStore()
const {droneList, selectedDroneId, rawTelemetry} = storeToRefs(droneStore)
const {selectDrone, isClientAccepted} = droneStore

// 电量颜色函数
const getBatteryColor = (level) => {
  if (level > 50) return 'green'
  if (level > 20) return 'orange'
  return 'red'
}

// 标题下方展示的无人机 IP + Port
const displayedDrones = computed(() => droneList.value.filter(d => isClientAccepted(d.id)))

const curDroneCaption = computed(() => {
  const drone = displayedDrones.value.find(d => d.id === selectedDroneId.value)
  if (!drone) return '未选择无人机'
  return `${drone.ip}`
})

// 点击无人机后选中并折叠面板
const handleSelectDrone = (id) => {
  selectDrone(id)
}
</script>

<style scoped>
.tech-expansion {
  background: transparent;
}
</style>
