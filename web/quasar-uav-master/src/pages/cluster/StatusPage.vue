<template>
  <q-page padding>
    <div class="text-h6 q-mb-md">集群管理 / 无人机状态</div>

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
          :rows="rows"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="{ rowsPerPage: 10 }"
        >
          <template #body-cell-battery="props">
            <q-td :props="props">
              <q-badge :color="batteryColor(props.row.battery)">🔋 {{ formatPercent(props.row.battery) }}</q-badge>
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
  { name: 'battery', label: '电量(%)', field: 'battery', align: 'center' },
  { name: 'altitude', label: '高度(m)', field: 'altitude', align: 'right' },
  { name: 'speed', label: '速度(m/s)', field: 'speed', align: 'right' },
  { name: 'heading', label: '航向(°)', field: 'heading', align: 'right' },
  { name: 'latitude', label: '纬度', field: 'latitude', align: 'right' },
  { name: 'longitude', label: '经度', field: 'longitude', align: 'right' },
]

const acceptedList = computed(() => {
  return droneStore.droneList.filter(d => droneStore.isClientAccepted(d.id))
})

const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return acceptedList.value
  return acceptedList.value.filter(c => (
    (c.name || '').toLowerCase().includes(kw) ||
    (c.id || '').toLowerCase().includes(kw) ||
    (c.ip || '').toLowerCase().includes(kw)
  ))
})

const rows = computed(() => filteredList.value.map(c => {
  const t = droneStore.rawTelemetry[c.id] || {}
  const battery = t?.battery_info?.batteries?.[0]?.percent
  return {
    id: c.id,
    name: c.name || c.id,
    ip: c.ip,
    battery: typeof battery === 'number' ? battery : null,
    altitude: t.height ?? null,
    speed: t.speed ?? null,
    heading: t.head ?? null,
    latitude: t.latitude ?? null,
    longitude: t.longtitude ?? null,
  }
}))

function formatNumber(val, digits = 2) {
  if (val === null || typeof val === 'undefined' || Number.isNaN(val)) return '-'
  const num = Number(val)
  if (Number.isNaN(num)) return '-'
  return num.toFixed(digits)
}

function formatPercent(val) {
  if (val === null || typeof val === 'undefined') return 'N/A'
  return `${formatNumber(val, 0)}`
}

function batteryColor(level) {
  if (typeof level !== 'number') return 'grey'
  if (level > 50) return 'green'
  if (level > 20) return 'orange'
  return 'red'
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


