<template>
  <q-card bordered class="tech-card q-pa-sm q-gutter-md">
    <!-- 标题 -->
    <div class="row items-center justify-between q-mb-xs">
      <div class="text-subtitle1 text-weight-bold tech-text">设备状态</div>
      <q-badge :color="isConnected ? 'positive' : 'negative'" outline>
        {{ controlStatus }}
      </q-badge>
    </div>

    <!-- 设备信息 -->
    <div class="row items-center q-mt-sm">
      <q-avatar size="40px" class="q-mr-sm tech-avatar">
        <q-icon name="airplanemode_active" size="32px" color="blue" class="tech-icon"/>
      </q-avatar>
      <div>
        <div class="text-subtitle2 text-weight-medium tech-text">{{ droneName }}</div>
        <div class="text-caption text-grey-6 tech-text-secondary">● {{ mode }}</div>
      </div>
    </div>

    <!-- 控制按钮 -->
    <div class="row q-gutter-sm q-mt-sm">
      <q-btn label="飞行控制" outline color="primary" icon="flight" @click="flightControl" class="tech-btn"/>
      <q-btn
        v-if="!droneStatus.isFlying"
        label="一键起飞"
        flat
        class="tech-btn"
        @click="takeoffWithOrigin"
      />
      <q-btn
        v-else
        label="一键降落"
        flat
        class="tech-btn"
        @click="sendCommand('land')"
      />
    </div>

    <div class="tech-separator"></div>

    <!-- 状态信息 -->
    <div class="row items-center justify-around q-mt-md">
      <div class="column items-center">
        <q-icon name="battery_std" color="green-5" size="24px" class="tech-icon"/>
        <div class="text-caption tech-text">{{ batteryLevel }}%</div>
        <div class="text-caption text-grey tech-text-secondary">电池电量</div>
      </div>

      <div class="column items-center">
        <q-icon name="trending_flat" color="teal-6" size="24px" class="tech-icon"/>
        <div class="text-caption tech-text">{{ speed }} m/s</div>
        <div class="text-caption text-grey tech-text-secondary">水平速度</div>
      </div>

      <div class="column items-center">
        <q-icon name="height" color="purple" size="24px" class="tech-icon"/>
        <div class="text-caption tech-text">{{ altitude }} m</div>
        <div class="text-caption text-grey tech-text-secondary">相对高度</div>
      </div>

      <div class="column items-center">
        <q-icon name="navigation" color="orange-5" size="24px" class="tech-icon"/>
        <div class="text-caption tech-text">{{ heading }} °</div>
        <div class="text-caption text-grey tech-text-secondary">机头朝向</div>
      </div>
    </div>


    <div class="tech-separator"></div>
    <CameraView :id="curDroneId"/>
    <!-- <CameraView ip="192.168.1.101"/> -->
  </q-card>
</template>

<script setup>
import {computed} from 'vue'
import {storeToRefs} from 'pinia'
import CameraView from "components/CameraView.vue";
import {useLayoutStore} from "stores/layout-store.js";
import {useDroneStore} from "stores/drone.js";

const droneStore = useDroneStore();
const {sendCommand} = droneStore;
const {droneList, selectedDroneId, originPosition } = storeToRefs(droneStore)

// 使用 storeToRefs 保持响应性
const {selectedDrone, droneStatus, batteryLevel} = storeToRefs(droneStore);

const curDroneId = computed(() => {
  const drone = droneList.value.find(d => d.id === selectedDroneId.value)
  if (!drone) return ''
  return `${drone.id}`
})

const isConnected = computed(() => droneStatus.value.isConnected);
const controlStatus = computed(() => isConnected.value ? '远程控制中' : '连接已断开');
const droneName = computed(() => selectedDrone.value?.id || '未选择无人机');
const mode = computed(() => droneStatus.value.isFlying ? '飞行中' : '地面待命');

// 为显示创建安全的计算属性
const altitude = computed(() => droneStatus.value.altitude?.toFixed(1) || '0.0');
const speed = computed(() => droneStatus.value.speed?.toFixed(1) || '0.0');
const heading = computed(() => droneStatus.value.heading?.toFixed(1) || '0');

const $layoutStore = useLayoutStore()

function flightControl() {
  $layoutStore.controlPanelShow = !$layoutStore.controlPanelShow
}

// 起飞时设置原点位置
async function takeoffWithOrigin() {
  try {
    // 设置原点位置为当前无人机位置
    if (droneStatus.value.isConnected && droneStatus.value.latitude && droneStatus.value.longitude) {
      originPosition.value.lat = droneStatus.value.latitude;
      originPosition.value.lng = droneStatus.value.longitude;
      console.log('设置起飞原点:', originPosition.value);
    }

    // 发送起飞命令
    await sendCommand('takeoff');
  } catch (error) {
    console.error('起飞失败:', error);
  }
}
</script>

<style scoped>
.tech-avatar {
  box-shadow: 0 0 15px rgba(74, 144, 226, 0.3);
}

.tech-text {
  color: #2C3E50;
  text-shadow: 0 0 2px rgba(44, 62, 80, 0.1);
}

.tech-text-secondary {
  color: #4A90E2;
  text-shadow: 0 0 5px rgba(74, 144, 226, 0.2);
}

.tech-icon {
  text-shadow: 0 0 8px rgba(74, 144, 226, 0.3);
}
</style>
