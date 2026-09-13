<template>
  <q-page class="tech-page">
    <div class="tech-grid" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: -1;"></div>
    <MapView/>
    <!-- 浮动控制面板按钮 -->
    <q-page-sticky position="top-left" :offset="[9, 9]">
      <MultiDroneList style="width: 250px"/>
    </q-page-sticky>
    <q-page-sticky position="right" :offset="[9, 0]">
      <DroneStatus style="width: 300px"/>
    </q-page-sticky>
    <q-page-sticky position="bottom" :offset="[0, 18]">
      <DroneControl v-show="$layoutStore.controlPanelShow"/>
    </q-page-sticky>
  </q-page>
</template>

<script setup>
import MultiDroneList from "components/MultiDroneList.vue";
import MapView from "components/MapView.vue";
import DroneStatus from "components/DroneStatus.vue";
import DroneControl from "components/DroneControl.vue";
import {useLayoutStore} from "stores/layout-store.js";
import {useDroneStore} from "stores/drone.js";
import {onMounted} from "vue";

const $layoutStore = useLayoutStore()
const droneStore = useDroneStore()

// 页面加载时启用多选模式
onMounted(() => {
  if (!droneStore.multiSelectMode) {
    droneStore.toggleMultiSelectMode()
  }
})

</script>

<style scoped>
.tech-page {
  background: transparent;
  position: relative;
}
</style>
