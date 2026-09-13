<template>
  <q-page padding class="industrial-subpage"><div class="subpage-heading"><div><span class="subpage-kicker">SINGLE / AI NAVIGATION</span><h1>视觉语言导航</h1><p>使用自然语言和视觉感知生成飞行控制指令</p></div><q-icon name="psychology" /></div><div class="subpage-content-row"><DroneList style="width: 220px"/><LlmControl class="subpage-feature-card" /></div></q-page>
</template>
<script setup>
import LlmControl from 'components/LLMControl.vue'
import DroneList from 'components/DroneList.vue'
</script>
