<template>
  <div class="row q-pa-sm justify-between tech-control-panel">
    <div>
      <q-tabs
        v-model="tab"
        dense
        class="text-grey"
        active-color="primary"
        indicator-color="primary"
        align="justify"
        narrow-indicator
      >
        <q-tab name="joystick" label="摇杆控制"/>
        <q-tab name="position" label="坐标控制"/>
        <q-tab name="point" label="打点控制"/>
      </q-tabs>

      <q-separator/>

      <q-tab-panels v-model="tab" animated>
        <q-tab-panel name="joystick">
          <div class="column items-center">
            <div class="row q-pa-md items-center q-gutter-lg">
              <CompassControl class="q-mb-md"
                              @update="updateLeftJoystick"/>

              <div class="column q-gutter-sm">
                <q-btn label="返航" color="primary" class="tech-btn"
                       @click="sendCommand('go_home')"
                       :disable="!droneStatus.isFlying"
                />

                <q-toggle
                  v-model="rosControlEnabled"
                  label="ROS控制"
                  color="primary"
                  class="q-mt-sm"
                  @update:model-value="onRosControlChange"
                />
                <q-toggle
                  v-model="joystickEnabled"
                  label="启用摇杆"
                  color="primary"
                  class="q-mt-sm"
                  @update:model-value="onJoystickToggle"
                />
              </div>

              <CompassControl
                class="q-mb-md"
                @update="updateRightJoystick"
              />

            </div>

          </div>
        </q-tab-panel>

        <q-tab-panel name="position">
          <div class="q-pa-xs" style="max-width: 400px;">
            <!-- 输入框区域 -->
            <div class="row q-col-gutter-sm">
              <div class="col-6">
                <q-input v-model.number="pos.x" label="X (m)" filled dense/>
              </div>
              <div class="col-6">
                <q-input v-model.number="pos.y" label="Y (m)" filled/>
              </div>
              <div class="col-6">
                <q-input v-model.number="pos.z" label="Z (m)" filled/>
              </div>
              <div class="col-6">
                <q-input v-model.number="pos.yaw" label="Yaw (°)" filled/>
              </div>
            </div>

            <!-- 按钮区域 -->
            <div class="row justify-between q-mt-sm">
              <q-btn
                class="tech-btn"
                label="发送位置指令"
                color="primary"
                :loading="isSending"
                @click="sendPositionCommand(pos)"
              />
              <q-btn
                class="tech-btn"
                label="重置"
                color="secondary"
                flat
                @click="onReset"/>
            </div>
          </div>
        </q-tab-panel>

        <q-tab-panel name="point">
          <div class="row items-center justify-around q-mt-sm">
            <q-btn
              class="tech-btn"
              label="前往目标点"
              color="primary"
              @click="sendTargetCommand"/>
            <q-btn
              class="tech-btn"
              label="设置原点坐标"
              color="secondary"
              @click="sendOriginCommand"/>
          </div>
        </q-tab-panel>
      </q-tab-panels>
            <!-- ======================================================= -->
      <!-- 新增：任务模式设置 (Swarm Type) 控制器 -->
      <!-- ======================================================= -->
      <q-separator class="q-my-md" />
      <div class="q-px-md q-pb-sm">
        <div class="text-subtitle2 q-mb-xs text-grey-8">任务模式设置 (Swarm Type)</div>
        <div class="row items-center q-gutter-sm">
          <q-input
            v-model.number="swarmType"
            type="number"
            label="模式值"
            dense
            filled
            style="max-width: 120px"
            hint="0:手动, 2:航线"
          />
          <q-btn
            label="设置模式"
            color="deep-orange"
            @click="setSwarmType"
            class="tech-btn"
            icon="settings"
          />
        </div>
      </div>
    </div>
  </div>

</template>
<script setup>
import {ref, onMounted, onUnmounted} from 'vue'
import {useDroneStore} from 'stores/drone'
import {storeToRefs} from 'pinia'
import CompassControl from "./CompassControl.vue";
import { Notify } from 'quasar'

const droneStore = useDroneStore()

// 解构 action 函数
const { sendJoystickData, sendCommand, sendPosition, sendTarget, sendOrigin, sendJsonCommand } = droneStore

// =======================================================
// 【关键】使用 storeToRefs 后，这些都是 Ref 对象
// =======================================================
const { droneStatus, lastCalculatedPosition, originPosition } = storeToRefs(droneStore)

const tab = ref("joystick")
const leftJoystickValues = ref({x: 0, y: 0})
const rightJoystickValues = ref({x: 0, y: 0})
const rosControlEnabled = ref(false)
const joystickEnabled = ref(false)
let joystickInterval = null;

const updateLeftJoystick = (values) => {
  leftJoystickValues.value = values
}
const updateRightJoystick = (values) => {
  rightJoystickValues.value = values
}

const swarmType = ref(0);

function setSwarmType() {
  const typeValue = Number(swarmType.value);
  if (isNaN(typeValue)) {
    Notify.create({ type: 'negative', message: '请输入一个有效的数字！' });
    return;
  }
  sendJsonCommand('set_swarm_type', typeValue);
  Notify.create({ type: 'positive', message: `任务模式 (Swarm Type) 已发送指令: ${typeValue}`, icon: 'check_circle' });
}

onMounted(() => {
  joystickInterval = setInterval(() => {
    sendJoystickData({
      left_stick_x: rightJoystickValues.value.x,
      left_stick_y: rightJoystickValues.value.y,
      right_stick_x: leftJoystickValues.value.x,
      right_stick_y: leftJoystickValues.value.y,
    })
  }, 100);
});

onUnmounted(() => {
  if (joystickInterval) {
    clearInterval(joystickInterval)
    joystickInterval = null;
  }
});

const onRosControlChange = (value) => {
  sendCommand(value ? 'enable_ros_control' : 'disable_ros_control')
}

const onJoystickToggle = (value) => {
  sendCommand(value ? 'enable_vstick' : 'disable_vstick')
}

const pos = ref({ x: 0, y: 0, z: 0, yaw: 0 })
const isSending = ref(false)

function sendPositionCommand(pos) {
  sendPosition(pos)
  isSending.value=true
  setTimeout(()=>isSending.value = false, 1000)
}

function onReset(){
  pos.value = { x: 0, y: 0, z: 0, yaw: 0 }
}

// =======================================================
// 【重大修改】修正 sendOriginCommand 函数
// =======================================================
function sendOriginCommand(){
  // 检查 lastCalculatedPosition.value 是否有有效数据
  if(!lastCalculatedPosition.value || lastCalculatedPosition.value.lng === '' || lastCalculatedPosition.value.lat === ''){
    Notify.create({
      type: 'warning',
      message: '请先在地图上左键点击一个点作为原点!'
    });
    return;
  }

  // 通过 .value 修改 Ref 内部对象的属性
  originPosition.value.lng = lastCalculatedPosition.value.lng
  originPosition.value.lat = lastCalculatedPosition.value.lat

  console.log("设置原点，发送数据:", originPosition.value);

  // 将 Ref 内部的普通对象 (.value) 传递给 action
  sendOrigin(originPosition.value)

  Notify.create({
      type: 'positive',
      message: `原点已设置`
    });
}

// =======================================================
// 【重大修改】修正 sendTargetCommand 函数
// =================================log======================
function sendTargetCommand(){
  // 检查 lastCalculatedPosition.value 是否有有效数据
  if(!lastCalculatedPosition.value || lastCalculatedPosition.value.lng === '' || lastCalculatedPosition.value.lat === ''){
    Notify.create({
      type: 'warning',
      message: '请先在地图上左键点击一个目标点!'
    });
    return
  }

  console.log("前往目标点，发送数据:", lastCalculatedPosition.value);

  // 将 Ref 内部的普通对象 (.value) 传递给 action
  sendTarget(lastCalculatedPosition.value)
}
</script>

<style scoped>
.tech-control-panel {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 248, 250, 0.95) 100%);
  border: 1px solid #4A90E2;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(74, 144, 226, 0.15),
  inset 0 1px 0 rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  transform: scale(0.8);
  transform-origin: bottom;
}

.tech-btn {
  background: linear-gradient(145deg, rgba(74, 144, 226, 0.1) 0%, rgba(255, 255, 255, 0.9) 100%);
  border: 1px solid #4A90E2;
  color: #2C3E50;
  border-radius: 8px;
  transition: all 0.3s ease;
  text-shadow: 0 0 2px rgba(44, 62, 80, 0.1);
}

.tech-btn:hover {
  box-shadow: 0 4px 20px rgba(74, 144, 226, 0.3);
  transform: translateY(-2px);
  background: linear-gradient(145deg, rgba(74, 144, 226, 0.2) 0%, rgba(255, 255, 255, 1) 100%);
}

.tech-btn:active {
  transform: translateY(0);
}
</style>

