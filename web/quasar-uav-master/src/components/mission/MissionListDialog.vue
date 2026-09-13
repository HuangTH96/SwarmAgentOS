<template>
  <q-dialog :model-value="show" @update:model-value="emit('update:show', $event)" persistent>
    <q-card style="min-width: 600px; max-width: 800px;">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">任务列表</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="close" />
      </q-card-section>

      <q-card-section>
        <q-list v-if="missions.length > 0" separator>
          <q-item
            v-for="mission in missions"
            :key="mission.id"
            clickable
            @click="emit('select', mission.id)"
          >
            <q-item-section avatar>
              <q-icon name="flight_takeoff" color="primary" />
            </q-item-section>

            <q-item-section>
              <q-item-label>{{ mission.name }}</q-item-label>
              <q-item-label caption>
                {{ mission.num_uavs }} 架无人机 · {{ formatMissionType(mission.mission_type) }} · {{ mission.created_at }}
              </q-item-label>
            </q-item-section>

            <q-item-section side>
              <div class="row q-gutter-sm">
                <q-btn
                  flat
                  dense
                  round
                  icon="edit"
                  color="primary"
                  @click.stop="emit('edit', mission.id)"
                >
                  <q-tooltip>编辑</q-tooltip>
                </q-btn>
                <q-btn
                  flat
                  dense
                  round
                  icon="delete"
                  color="negative"
                  @click.stop="confirmDelete(mission)"
                >
                  <q-tooltip>删除</q-tooltip>
                </q-btn>
              </div>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-else class="text-center q-pa-lg text-grey-6">
          <q-icon name="inbox" size="64px" />
          <div class="q-mt-md">暂无保存的任务</div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="关闭" color="primary" @click="close" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { useQuasar } from 'quasar'

const $q = useQuasar()

defineProps({
  show: Boolean,
  missions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:show', 'select', 'edit', 'delete'])

function close() {
  emit('update:show', false)
}

function confirmDelete(mission) {
  $q.dialog({
    title: '确认删除',
    message: `确定要删除任务"${mission.name}"吗？此操作不可恢复。`,
    cancel: true,
    persistent: true
  }).onOk(() => {
    emit('delete', mission.id)
  })
}

function formatMissionType(type) {
  const typeMap = {
    'patrol': '巡逻',
    'delivery': '运输',
    'inspection': '巡检'
  }
  return typeMap[type] || type
}
</script>

