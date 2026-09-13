<template>
  <div class="parameter-panel">
    <q-scroll-area class="fit">
      <!-- 任务信息 -->
      <q-card flat bordered class="q-ma-md">
        <q-card-section>
          <div class="text-h6">任务信息</div>
        </q-card-section>
        <q-separator />
        <q-card-section>
          <div class="info-row">
            <span class="label">任务类型:</span>
            <span class="value">{{ missionTypeLabel }}</span>
          </div>
          <div class="info-row">
            <span class="label">无人机数量:</span>
            <span class="value">{{ taskData?.num_uavs || 1 }}</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- 禁飞区列表 -->
      <q-card flat bordered class="q-ma-md">
        <q-card-section>
          <div class="text-h6">禁飞区 ({{ noFlyZones.length }}/10)</div>
        </q-card-section>
        <q-separator />
        <q-list v-if="noFlyZones.length > 0">
          <q-item 
            v-for="zone in noFlyZones" 
            :key="zone.id"
            clickable
            :active="selectedItem?.id === zone.id"
            @click="$emit('select-item', zone)"
          >
            <q-item-section>
              <q-item-label>{{ zone.name }}</q-item-label>
              <q-item-label caption>
                中心: {{ zone.center.lat.toFixed(6) }}, {{ zone.center.lng.toFixed(6) }}
              </q-item-label>
              <q-item-label caption>
                半径: {{ zone.radius }}米
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn 
                flat 
                dense 
                round 
                icon="delete" 
                color="negative"
                @click.stop="$emit('delete-nofly-zone', zone.id)"
              />
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else>
          <div class="text-grey-6 text-center">暂无禁飞区</div>
        </q-card-section>
      </q-card>

      <!-- 必经点列表 -->
      <q-card flat bordered class="q-ma-md">
        <q-card-section>
          <div class="text-h6">必经点 ({{ waypoints.length }}/20)</div>
        </q-card-section>
        <q-separator />
        <q-list v-if="waypoints.length > 0">
          <q-item 
            v-for="waypoint in sortedWaypoints" 
            :key="waypoint.id"
            clickable
            :active="selectedItem?.id === waypoint.id"
            @click="$emit('select-item', waypoint)"
          >
            <q-item-section avatar>
              <q-avatar color="primary" text-color="white">
                {{ waypoint.sequence + 1 }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ waypoint.name }}</q-item-label>
              <q-item-label caption>
                {{ waypoint.lat.toFixed(6) }}, {{ waypoint.lng.toFixed(6) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn 
                flat 
                dense 
                round 
                icon="delete" 
                color="negative"
                @click.stop="$emit('delete-waypoint', waypoint.id)"
              />
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else>
          <div class="text-grey-6 text-center">暂无必经点</div>
        </q-card-section>
      </q-card>

      <!-- 航迹信息 -->
      <q-card flat bordered class="q-ma-md" v-if="routes.length > 0">
        <q-card-section>
          <div class="text-h6">航迹信息</div>
        </q-card-section>
        <q-separator />
        <q-list>
          <q-item v-for="(route, index) in routes" :key="index">
            <q-item-section>
              <q-item-label>UAV {{ route.uav_id + 1 }}</q-item-label>
              <q-item-label caption>
                航点数: {{ route.waypoints.length }}
              </q-item-label>
              <q-item-label caption>
                距离: {{ Math.round(route.total_distance) }}米
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section>
          <div class="info-row">
            <span class="label">总距离:</span>
            <span class="value">{{ totalDistance }}米</span>
          </div>
        </q-card-section>
      </q-card>
    </q-scroll-area>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'ParameterPanel',
  props: {
    taskData: Object,
    noFlyZones: { type: Array, default: () => [] },
    waypoints: { type: Array, default: () => [] },
    routes: { type: Array, default: () => [] },
    selectedItem: Object
  },
  emits: ['update-nofly-zone', 'delete-nofly-zone', 'update-waypoint', 'delete-waypoint', 'select-item'],
  setup(props) {
    const missionTypeLabel = computed(() => {
      const types = {
        patrol: '巡逻',
        delivery: '配送',
        inspection: '巡检'
      }
      return types[props.taskData?.mission_type] || '未知'
    })

    const sortedWaypoints = computed(() => {
      return [...props.waypoints].sort((a, b) => a.sequence - b.sequence)
    })

    const totalDistance = computed(() => {
      return props.routes.reduce((sum, route) => sum + (route.total_distance || 0), 0)
    })

    return {
      missionTypeLabel,
      sortedWaypoints,
      totalDistance
    }
  }
}
</script>

<style scoped lang="scss">
.parameter-panel {
  width: 350px;
  background: #0b141b;
  border-left: 1px solid rgba(116,169,190,.3);
  overflow: hidden;
  position: relative;
  z-index: 10;
}
.parameter-panel :deep(.q-card) { margin: 10px 12px !important; background: linear-gradient(180deg, rgba(18,29,37,.97), rgba(10,17,22,.99)); border: 1px solid rgba(116,169,190,.24); border-radius: 2px; box-shadow: inset 2px 0 rgba(51,214,232,.42), 0 7px 16px rgba(0,0,0,.22); }
.parameter-panel :deep(.q-card__section) { padding: 12px 14px; }
.parameter-panel :deep(.text-h6) { color: #e5f1f2; font-size: 12px; letter-spacing: .07em; }
.parameter-panel :deep(.q-separator) { background: rgba(116,169,190,.2); }
.parameter-panel :deep(.q-item) { min-height: 52px; color: #d8e7e9; border-bottom: 1px solid rgba(116,169,190,.1); }
.parameter-panel :deep(.q-item:hover), .parameter-panel :deep(.q-item--active) { background: rgba(51,214,232,.08); }
.parameter-panel :deep(.q-item__label) { color: #d8e7e9; font-size: 11px; }
.parameter-panel :deep(.q-item__label--caption) { color: #78939b !important; font-size: 9px; }
.parameter-panel :deep(.q-avatar) { background: #17323a !important; color: #33d6e8 !important; border: 1px solid rgba(51,214,232,.4); }
.parameter-panel :deep(.text-grey-6) { color: #78939b !important; }
.parameter-panel :deep(.q-scrollarea__content) { padding-bottom: 18px; }

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;

  .label {
    color: #78939b;
  }

  .value {
    color: #dcebed;
    font-weight: 500;
  }
}
</style>
