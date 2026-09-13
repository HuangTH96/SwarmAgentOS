<template>
  <q-page class="q-pa-md">
    <q-card>
      <q-card-section class="row items-center justify-between">
        <div class="text-h6">无人机管理</div>
        <q-btn flat icon="refresh" label="刷新" @click="handleRefresh" />
      </q-card-section>

      <q-separator />

      <q-card-section>
        <q-table
          :rows="droneStore.droneList"
          :columns="columns"
          row-key="id"
          flat
          bordered
          hide-bottom
        >
          <template v-slot:body-cell-actions="props">
            <q-td align="right">
              <q-btn
                v-if="!confirmedMap[props.row.id]"
                flat
                color="primary"
                icon="check"
                label="确认"
                @click="confirmDrone(props.row.id)"
              />
              <q-btn
                v-if="!confirmedMap[props.row.id]"
                flat
                color="negative"
                icon="close"
                label="拒绝"
                @click="rejectDrone(props.row.id)"
              />
              <q-btn
                v-if="confirmedMap[props.row.id]"
                flat
                color="warning"
                icon="link_off"
                label="断开连接"
                @click="disconnectDrone(props.row.id)"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { useDroneStore } from 'src/stores/drone'
import { useQuasar } from 'quasar'

const droneStore = useDroneStore()
const $q = useQuasar()

// 表格列定义
const columns = [
  { name: 'id', label: 'ID', align: 'left', field: 'id' },
  { name: 'name', label: '名称', align: 'left', field: 'name' },
  { name: 'ip', label: 'IP地址', align: 'left', field: 'ip' },
  {
    name: 'actions',
    label: '操作',
    align: 'right',
    field: 'actions',
    sortable: false
  }
]

// 本地确认状态映射表（不依赖 drone.js）
const confirmedMap = reactive({})

// 页面加载时自动拉取列表
onMounted(() => {
  droneStore.fetchClients()
})

// 确认：设置本地状态
function confirmDrone(id) {
  confirmedMap[id] = true
  $q.notify({
    type: 'positive',
    message: `已确认无人机 ${id}`
  })
}

// 拒绝：从 droneList 中移除
function rejectDrone(id) {
  droneStore.droneList = droneStore.droneList.filter(d => d.id !== id)
  delete confirmedMap[id]
  $q.notify({
    type: 'warning',
    message: `已拒绝无人机 ${id}`
  })
}

// 断开连接：重置为“确认 / 拒绝”状态
function disconnectDrone(id) {
  confirmedMap[id] = false
  $q.notify({
    type: 'info',
    message: `已断开与无人机 ${id} 的连接，可重新确认或拒绝`
  })
}

// 刷新：清除所有确认状态并重新拉取
function handleRefresh() {
  Object.keys(confirmedMap).forEach(key => delete confirmedMap[key])
  droneStore.fetchClients()
}
</script>

<style scoped>
.q-table__middle {
  font-size: 14px;
}
</style>
