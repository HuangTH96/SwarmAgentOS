<template>
  <div
    class="joystick-area compass-area tech-compass"
    ref="baseElement"
    @mousedown.prevent="onStart"
    @touchstart.prevent="onStart"
  >
    <!-- 中心摇杆 -->
    <div
      class="joystick-stick compass-stick tech-stick"
      ref="stickElement"
      :style="stickStyle"
    >
      <div class="stick-center">
        <q-icon name="camera" size="md" color="white" class="tech-icon" />
      </div>
    </div>

    <!-- 上下左右方向图标 -->
    <div class="direction-indicators">
      <div class="direction up tech-direction">
        <q-icon name="keyboard_arrow_up" size="md" class="tech-icon" />
      </div>

      <div class="direction down tech-direction">
        <q-icon name="keyboard_arrow_down" size="md" class="tech-icon" />
      </div>

      <div class="direction left tech-direction">
        <q-icon name="keyboard_arrow_left" size="md" class="tech-icon" />
      </div>

      <div class="direction right tech-direction">
        <q-icon name="keyboard_arrow_right" size="md" class="tech-icon" />
      </div>
    </div>

    <!-- 中心点 -->
    <div class="center-point tech-center"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['update'])

const baseElement = ref(null)
const stickElement = ref(null)

const stickX = ref(0)
const stickY = ref(0)
const maxDistance = 40
const EPSILON = 0.001
let isDragging = false
let center = { x: 0, y: 0 }

const previousEmittedValues = { x: null, y: null }

const stickStyle = computed(() => ({
  transform: `translate(${stickX.value}px, ${stickY.value}px)`
}))

const updateStickPosition = (dx, dy) => {
  const distance = Math.sqrt(dx * dx + dy * dy)
  let fx = dx
  let fy = dy

  if (distance > maxDistance) {
    fx = (dx / distance) * maxDistance
    fy = (dy / distance) * maxDistance
  }

  stickX.value = fx
  stickY.value = fy
  emitJoystickUpdate(fx, fy)
}

const emitJoystickUpdate = (dx, dy) => {
  const currentX = parseFloat((dx / maxDistance).toFixed(4))
  const currentY = parseFloat((-dy / maxDistance).toFixed(4))

  if (
    Math.abs(currentX - previousEmittedValues.x) > EPSILON ||
    Math.abs(currentY - previousEmittedValues.y) > EPSILON
  ) {
    previousEmittedValues.x = currentX
    previousEmittedValues.y = currentY
    emit('update', { x: currentX, y: currentY })
  }
}

const resetStick = () => {
  stickX.value = 0
  stickY.value = 0
  emitJoystickUpdate(0, 0)
}

const onStart = (e) => {
  e.preventDefault()
  isDragging = true

  const rect = baseElement.value.getBoundingClientRect()
  center = {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2
  }

  const moveHandler = (moveEvent) => {
    const touch = moveEvent.touches ? moveEvent.touches[0] : null
    const clientX = touch ? touch.clientX : moveEvent.clientX
    const clientY = touch ? touch.clientY : moveEvent.clientY
    const dx = clientX - center.x
    const dy = clientY - center.y
    updateStickPosition(dx, dy)
  }

  const endHandler = () => {
    isDragging = false
    resetStick()
    document.removeEventListener('mousemove', moveHandler)
    document.removeEventListener('mouseup', endHandler)
    document.removeEventListener('mouseleave', endHandler)
    document.removeEventListener('touchmove', moveHandler)
    document.removeEventListener('touchend', endHandler)
    document.removeEventListener('touchcancel', endHandler)
  }

  document.addEventListener('mousemove', moveHandler)
  document.addEventListener('mouseup', endHandler)
  document.addEventListener('mouseleave', endHandler)
  document.addEventListener('touchmove', moveHandler, { passive: false })
  document.addEventListener('touchend', endHandler)
  document.addEventListener('touchcancel', endHandler)
}

onMounted(() => {
  emitJoystickUpdate(0, 0)
})

onUnmounted(() => {
  isDragging = false
})
</script>

<style scoped>
.joystick-area {
  position: relative;
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 248, 250, 0.95) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #4A90E2;
  margin-bottom: 14px;
  box-shadow:
    0 8px 32px rgba(74, 144, 226, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  overflow: hidden;
}

.compass-area {
  border-color: #4A90E2;
}

.compass-area::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 50%;
  background: conic-gradient(from 0deg, transparent, rgba(74, 144, 226, 0.1), transparent);
  animation: rotate 4s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.joystick-stick {
  position: absolute;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  cursor: grab;
  transition: transform 0.1s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #4A90E2, #7BB3F0);
  box-shadow:
    0 4px 15px rgba(74, 144, 226, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  color: #ffffff;
  z-index: 10;
  border: 1px solid #4A90E2;
}

.joystick-stick:active {
  cursor: grabbing;
  transform: scale(0.95);
  box-shadow:
    0 6px 20px rgba(74, 144, 226, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.stick-center {
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.center-point {
  position: absolute;
  width: 5px;
  height: 5px;
  background: #4A90E2;
  border-radius: 50%;
  z-index: 5;
  box-shadow: 0 0 10px rgba(74, 144, 226, 0.5);
}

.direction-indicators {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.direction {
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4A90E2;
  font-size: 12px;
  transition: all 0.3s ease;
  z-index: 2;
  background: rgba(74, 144, 226, 0.1);
  border: 1px solid rgba(74, 144, 226, 0.3);
}

.direction:hover {
  background: rgba(74, 144, 226, 0.2);
  box-shadow: 0 0 10px rgba(74, 144, 226, 0.3);
}

.direction.up {
  top: 6px;
  left: 50%;
  transform: translateX(-50%);
}

.direction.down {
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
}

.direction.left {
  left: 6px;
  top: 50%;
  transform: translateY(-50%);
}

.direction.right {
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
}

.tech-icon {
  text-shadow: 0 0 8px rgba(74, 144, 226, 0.3);
}

.tech-compass {
  position: relative;
}

.tech-compass::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 80px;
  height: 80px;
  border: 1px solid rgba(74, 144, 226, 0.2);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

</style>
