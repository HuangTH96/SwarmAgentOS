<template>
  <q-page padding>
    <div class="text-h6 q-mb-md">集群管理 / 无人机接入</div>

    <q-card flat bordered>
      <q-card-section>
        <div class="row items-center q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-btn color="primary" label="刷新列表" @click="refresh" :loading="loading"/>
          </div>
          <div class="col-12 col-md-6">
            <q-input dense outlined v-model="keyword" placeholder="搜索(名称/ID/IP)" clearable/>
          </div>
        </div>
      </q-card-section>
      <q-separator/>
      <q-card-section>
        <q-table
          flat
          bordered
          :rows="filteredClients"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="{ rowsPerPage: 10 }"
        >
          <template #body-cell-accept="props">
            <q-td :props="props">
              <q-toggle
                color="primary"
                :model-value="isAccepted(props.row.id)"
                @update:model-value="setAccepted(props.row.id, $event)"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import {computed, ref, onMounted} from 'vue'
import {useDroneStore} from 'stores/drone'

const droneStore = useDroneStore()
const loading = ref(false)
const keyword = ref('')

const columns = [
  { name: 'name', label: '名称', field: 'name', align: 'left' },
  { name: 'id', label: 'ID', field: 'id', align: 'left' },
  { name: 'ip', label: 'IP', field: 'ip', align: 'left' },
  { name: 'accept', label: '接收数据', field: 'accept', align: 'center' }
]

const filteredClients = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return droneStore.droneList
  return droneStore.droneList.filter(c => {
    return (
      (c.name || '').toLowerCase().includes(kw) ||
      (c.id || '').toLowerCase().includes(kw) ||
      (c.ip || '').toLowerCase().includes(kw)
    )
  })
})

function isAccepted(id) {
  return droneStore.isClientAccepted(id)
}

function setAccepted(id, val) {
  droneStore.setClientAccepted(id, val)
}

async function refresh() {
  loading.value = true
  try {
    await droneStore.fetchClients()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (!droneStore.droneList || droneStore.droneList.length === 0) {
    refresh()
  }
})
</script>

<style scoped>
</style>


