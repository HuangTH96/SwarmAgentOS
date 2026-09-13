<template>
  <div class="map-toolbar">
    <q-btn-group flat>
      <q-btn 
        flat 
        icon="add_location" 
        label="添加禁飞区" 
        :color="editMode === 'nofly-zone' ? 'primary' : ''"
        :disable="noFlyZoneCount >= 10"
        @click="$emit('add-nofly-zone')"
      >
        <q-tooltip>点击地图添加禁飞区 ({{ noFlyZoneCount }}/10)</q-tooltip>
      </q-btn>
      
      <q-btn 
        flat 
        icon="place" 
        label="添加必经点" 
        :color="editMode === 'waypoint' ? 'primary' : ''"
        :disable="waypointCount >= 20"
        @click="$emit('add-waypoint')"
      >
        <q-tooltip>点击地图添加必经点 ({{ waypointCount }}/20)</q-tooltip>
      </q-btn>
      
      <q-btn 
        flat 
        icon="flag" 
        label="编辑起点" 
        :color="editMode === 'start' ? 'primary' : ''"
        @click="$emit('edit-start')"
      >
        <q-tooltip>点击地图设置起点</q-tooltip>
      </q-btn>
      
      <q-btn 
        flat 
        icon="outlined_flag" 
        label="编辑终点" 
        :color="editMode === 'end' ? 'primary' : ''"
        @click="$emit('edit-end')"
      >
        <q-tooltip>点击地图设置终点</q-tooltip>
      </q-btn>
    </q-btn-group>

    <q-space />

    <q-btn 
      v-if="editMode" 
      flat 
      icon="close" 
      label="取消" 
      color="negative"
      @click="$emit('cancel-edit')"
    />

    <q-btn 
      flat 
      icon="route" 
      label="生成航迹" 
      color="primary"
      @click="$emit('generate-route')"
    >
      <q-tooltip>根据当前参数生成无人机航迹</q-tooltip>
    </q-btn>
  </div>
</template>

<script>
export default {
  name: 'MapToolbar',
  props: {
    editMode: String,
    noFlyZoneCount: { type: Number, default: 0 },
    waypointCount: { type: Number, default: 0 }
  },
  emits: ['add-nofly-zone', 'add-waypoint', 'edit-start', 'edit-end', 'generate-route', 'cancel-edit']
}
</script>

<style scoped lang="scss">
.map-toolbar {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  padding: 6px 8px;
  background: rgba(9, 19, 25, .94);
  border: 1px solid rgba(116,169,190,.35);
  border-left: 2px solid #33d6e8;
  border-radius: 2px;
  box-shadow: 0 8px 24px rgba(0,0,0,.42), inset 0 1px rgba(255,255,255,.04);
  backdrop-filter: blur(10px);
  z-index: 1000;
}
.map-toolbar :deep(.q-btn) { min-height: 34px; color: #cce0e3; border-radius: 2px; font-size: 10px; letter-spacing: .03em; }
.map-toolbar :deep(.q-btn:hover), .map-toolbar :deep(.q-btn.text-primary) { color: #33d6e8 !important; background: rgba(51,214,232,.1); }
.map-toolbar :deep(.q-btn.text-negative) { color: #ff6b5f !important; }
</style>
