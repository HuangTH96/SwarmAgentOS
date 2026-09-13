<template>
  <q-card flat bordered class="tech-card text-primary q-pa-sm">
    <!-- 标题 -->
    <q-expansion-item
      v-model="expanded"
      icon="webhook"
      label="多选无人机"
      :caption="curDroneCaption"
      class="tech-expansion"
    >
      <!-- 多选控制按钮 -->
      <template v-slot:header>
        <q-item-section>
          <q-item-label>多选无人机</q-item-label>
          <q-item-label caption>{{ curDroneCaption }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <div class="row q-gutter-xs">
            <q-btn
              flat
              dense
              round
              icon="select_all"
              color="primary"
              @click.stop="selectAllDrones"
              size="sm"
            >
              <q-tooltip>全选</q-tooltip>
            </q-btn>
            <q-btn
              v-if="selectedDroneIds.length > 0"
              flat
              dense
              round
              icon="clear_all"
              color="negative"
              @click.stop="clearMultiSelection"
              size="sm"
            >
              <q-tooltip>清空选择</q-tooltip>
            </q-btn>
          </div>
        </q-item-section>
      </template>

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
            :active="selectedDroneIds.includes(drone.id)"
            @click="handleSelectDrone(drone.id)"
          >
            <q-item-section side>
              <q-checkbox
                :model-value="selectedDroneIds.includes(drone.id)"
                @update:model-value="toggleDroneSelection(drone.id)"
                @click.stop
              />
            </q-item-section>

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
const {droneList, selectedDroneIds, rawTelemetry} = storeToRefs(droneStore)
const {isClientAccepted, toggleDroneSelection, clearMultiSelection, selectAllDrones} = droneStore

// 电量颜色函数
const getBatteryColor = (level) => {
  if (level > 50) return 'green'
  if (level > 20) return 'orange'
  return 'red'
}

// 标题下方展示的无人机 IP + Port
const displayedDrones = computed(() => droneList.value.filter(d => isClientAccepted(d.id)))

const curDroneCaption = computed(() => {
  if (selectedDroneIds.value.length === 0) return '未选择无人机'
  if (selectedDroneIds.value.length === 1) {
    const drone = displayedDrones.value.find(d => d.id === selectedDroneIds.value[0])
    return drone ? `${drone.ip}` : '未知无人机'
  }
  return `已选择 ${selectedDroneIds.value.length} 架无人机`
})

// 点击无人机后选中
const handleSelectDrone = (id) => {
  toggleDroneSelection(id)
}
</script>

<style scoped>
.tech-expansion {
  background: transparent;
}
</style>
