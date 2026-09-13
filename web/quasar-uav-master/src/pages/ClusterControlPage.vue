<template>
  <q-page class="q-pa-md column items-center justify-start industrial-subpage">
    <q-card class="q-pa-md" style="width: 100%; max-width: 800px;">
      <q-card-section>
        <div class="text-h6">集群控制中心</div>
        <div class="text-subtitle2 text-grey">选择多架无人机，准备集群控制任务</div>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <q-select
          v-model="selectedDrones"
          :options="droneOptions"
          label="选择参与集群的无人机"
          multiple
          emit-value
          map-options
          filled
        />

        <q-select
          v-model="leaderDrone"
          :options="selectedDrones"
          label="指定主控无人机"
          emit-value
          map-options
          filled
          class="q-mt-md"
          :disable="selectedDrones.length === 0"
        />

        <q-banner v-if="selectedDrones.length && leaderDrone" class="bg-grey-2 q-mt-md">
          当前集群包含 <strong>{{ selectedDrones.length }}</strong> 架无人机，主控机为 <strong>{{ leaderDrone }}</strong>
        </q-banner>
      </q-card-section>

      <q-separator />

      <q-card-actions align="right">
        <q-btn label="发送测试指令" color="primary" flat :disable="!leaderDrone" />
        <q-btn label="重置选择" color="negative" flat @click="resetSelection" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'

const droneOptions = [
  { label: 'Drone A', value: 'droneA' },
  { label: 'Drone B', value: 'droneB' },
  { label: 'Drone C', value: 'droneC' },
  { label: 'Drone D', value: 'droneD' }
]

const selectedDrones = ref([])
const leaderDrone = ref(null)

function resetSelection() {
  selectedDrones.value = []
  leaderDrone.value = null
}
</script>

<style scoped>
.q-page {
  min-height: 100vh;
  background-color: #f5faff;
}
</style>
