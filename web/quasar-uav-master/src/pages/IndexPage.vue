<template>
  <q-page class="command-dashboard">
    <div class="dashboard-grid"></div>

    <section class="dashboard-heading">
      <div>
        <div class="eyebrow"><span></span> AI FLEET INTELLIGENCE PLATFORM</div>
        <h1>集群智能管理中心</h1>
        <p>融合感知、任务推演与自主协同的无人机集群运行态势</p>
      </div>
      <div class="heading-meta">
        <div><small>系统时钟 / CST</small><strong>{{ currentTime }}</strong></div>
        <div><small>AI 核心状态</small><strong class="healthy"><i></i>运行正常</strong></div>
      </div>
    </section>

    <section class="kpi-grid">
      <article v-for="item in kpis" :key="item.label" class="kpi-panel">
        <div class="kpi-top"><span>{{ item.code }}</span><q-icon :name="item.icon" /></div>
        <div class="kpi-value"><strong>{{ item.value }}</strong><em>{{ item.unit }}</em></div>
        <div class="kpi-label">{{ item.label }}</div>
        <div class="data-track"><i :style="{ width: item.progress + '%' }"></i></div>
        <div class="kpi-foot"><span>{{ item.note }}</span><b :class="item.tone">{{ item.status }}</b></div>
      </article>
    </section>

    <section class="dashboard-main">
      <article class="industrial-panel ai-topology">
        <header class="panel-header">
          <div><span class="panel-index">01</span><h2>AI 集群决策拓扑</h2></div>
          <div class="live-tag"><i></i> LIVE COMPUTING</div>
        </header>
        <div class="topology-stage">
          <div class="scan-line"></div>
          <svg class="topology-links" viewBox="0 0 800 420" preserveAspectRatio="none" aria-hidden="true">
            <circle cx="400" cy="210" r="135" />
            <circle cx="400" cy="210" r="178" class="outer-ring" />
            <path d="M400 210 L400 42 M400 210 L648 112 M400 210 L648 308 M400 210 L400 378 M400 210 L152 308 M400 210 L152 112" />
          </svg>
          <div class="ai-core">
            <div class="core-ring"></div>
            <q-icon name="memory" />
            <strong>AI CORE</strong>
            <span>DECISION ENGINE</span>
            <b>{{ aiCoreLoad }}%</b>
          </div>
          <div v-for="(node, index) in aiNodes" :key="node.name" class="topology-node" :class="`node-${index + 1}`">
            <q-icon :name="node.icon" />
            <div><strong>{{ node.name }}</strong><span>{{ node.en }}</span></div>
            <i></i>
          </div>
          <div class="stage-corner top-left">SYS // SWARM-AI</div>
          <div class="stage-corner bottom-right">SYNC {{ syncLatency }} ms</div>
        </div>
        <footer class="topology-footer">
          <div><span>感知融合</span><b>READY</b></div>
          <div><span>推理引擎</span><b>READY</b></div>
          <div><span>任务调度</span><b>READY</b></div>
          <div><span>安全策略</span><b>ACTIVE</b></div>
        </footer>
      </article>

      <div class="side-stack">
        <article class="industrial-panel resource-panel">
          <header class="panel-header">
            <div><span class="panel-index">02</span><h2>智能资源负载</h2></div>
            <span class="mono">RESOURCE</span>
          </header>
          <div v-for="item in resources" :key="item.label" class="resource-row">
            <div><span>{{ item.label }}</span><b>{{ item.value }}%</b></div>
            <div class="resource-track"><i :style="{ width: item.value + '%' }" :class="item.tone"></i></div>
          </div>
          <div class="resource-summary">
            <div><small>推理节点</small><strong>04</strong></div>
            <div><small>模型服务</small><strong>12</strong></div>
            <div><small>平均延迟</small><strong>{{ syncLatency }}<em>ms</em></strong></div>
          </div>
        </article>

        <article class="industrial-panel alert-panel">
          <header class="panel-header">
            <div><span class="panel-index">03</span><h2>智能告警中心</h2></div>
            <span class="alert-count">{{ alertCount }}</span>
          </header>
          <div class="alert-list">
            <div v-if="alerts.length === 0" class="empty-alert"><q-icon name="verified_user" /><div><strong>当前无风险告警</strong><span>AI 安全策略持续监测中</span></div></div>
            <div v-for="alert in alerts" :key="alert.id" class="alert-item"><i></i><div><strong>{{ alert.name }} 电量偏低</strong><span>{{ alert.battery }}% · 建议返航</span></div><time>NOW</time></div>
          </div>
        </article>
      </div>
    </section>

    <section class="dashboard-bottom">
      <article class="industrial-panel fleet-table">
        <header class="panel-header">
          <div><span class="panel-index">04</span><h2>集群设备态势</h2></div>
          <button type="button" @click="router.push('/cluster/ingress')">设备接入 <q-icon name="arrow_forward" /></button>
        </header>
        <div class="table-head"><span>节点编号</span><span>链路地址</span><span>任务状态</span><span>能源</span><span>遥测链路</span></div>
        <div v-if="fleetRows.length === 0" class="table-empty"><span class="empty-signal"></span><div><strong>等待无人机节点接入</strong><small>接入后将在此同步显示实时遥测数据</small></div></div>
        <div v-for="row in fleetRows" :key="row.id" class="table-row">
          <span><i class="online-dot"></i>{{ row.name }}</span><span class="mono">{{ row.ip }}</span><span>{{ row.state }}</span><span>{{ row.battery }}%</span><span><b class="signal-bars">▂▄▆█</b> STABLE</span>
        </div>
      </article>

      <article class="industrial-panel event-stream">
        <header class="panel-header">
          <div><span class="panel-index">05</span><h2>AI 事件流</h2></div>
          <span class="mono">AUTO SCROLL</span>
        </header>
        <div class="event-list">
          <div v-for="event in events" :key="event.time + event.text"><time>{{ event.time }}</time><i :class="event.type"></i><span>{{ event.text }}</span></div>
        </div>
      </article>

      <article class="industrial-panel quick-actions">
        <header class="panel-header"><div><span class="panel-index">06</span><h2>智能任务入口</h2></div></header>
        <button type="button" @click="router.push('/mission/ai-planning')"><q-icon name="psychology" /><div><strong>AI 任务规划</strong><span>自然语言生成任务</span></div><q-icon name="north_east" /></button>
        <button type="button" @click="router.push('/swarm/control')"><q-icon name="hub" /><div><strong>集群协同控制</strong><span>多机编队与控制</span></div><q-icon name="north_east" /></button>
        <button type="button" @click="router.push('/network/topology')"><q-icon name="lan" /><div><strong>网络智能感知</strong><span>链路拓扑与质量</span></div><q-icon name="north_east" /></button>
      </article>
    </section>
  </q-page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useDroneStore } from 'stores/drone'

const router = useRouter()
const droneStore = useDroneStore()
const { droneList, rawTelemetry, acceptedClients, plannedPath, logMessages } = storeToRefs(droneStore)
const safeDroneList = computed(() => droneList.value || [])
const safeTelemetry = computed(() => rawTelemetry.value || {})
const safeAcceptedClients = computed(() => acceptedClients.value || {})
const safePlannedPath = computed(() => plannedPath.value || [])
const safeLogMessages = computed(() => logMessages.value || [])

const now = ref(new Date())
const timer = window.setInterval(() => { now.value = new Date() }, 1000)
onBeforeUnmount(() => window.clearInterval(timer))
const currentTime = computed(() => now.value.toLocaleTimeString('zh-CN', { hour12: false }))

const activeDrones = computed(() => safeDroneList.value.filter(item => safeAcceptedClients.value[item.id] !== false))
const onlineCount = computed(() => activeDrones.value.length)
const batteries = computed(() => activeDrones.value.map(item => Number(safeTelemetry.value[item.id]?.battery_info?.batteries?.[0]?.percent || 0)).filter(Boolean))
const averageBattery = computed(() => batteries.value.length ? Math.round(batteries.value.reduce((a, b) => a + b, 0) / batteries.value.length) : 0)
const alertCount = computed(() => batteries.value.filter(value => value < 20).length)
const aiCoreLoad = computed(() => Math.min(92, 28 + onlineCount.value * 8))
const syncLatency = computed(() => onlineCount.value ? 18 + onlineCount.value * 2 : 0)

const kpis = computed(() => [
  { code: 'FLEET / 01', icon: 'flight', value: onlineCount.value, unit: '架', label: '在线无人机', progress: Math.min(100, onlineCount.value * 10), note: `注册节点 ${safeDroneList.value.length}`, status: onlineCount.value ? '实时在线' : '等待接入', tone: onlineCount.value ? 'ok' : 'idle' },
  { code: 'MISSION / 02', icon: 'route', value: safePlannedPath.value.length ? 1 : 0, unit: '项', label: '执行中任务', progress: safePlannedPath.value.length ? 58 : 0, note: `${safePlannedPath.value.length} 个航迹点`, status: safePlannedPath.value.length ? '执行中' : '任务就绪', tone: 'ok' },
  { code: 'ENERGY / 03', icon: 'battery_charging_full', value: averageBattery.value || '--', unit: averageBattery.value ? '%' : '', label: '集群平均电量', progress: averageBattery.value, note: alertCount.value ? `${alertCount.value} 个低电节点` : '能源状态稳定', status: alertCount.value ? '需要关注' : '正常', tone: alertCount.value ? 'warn' : 'ok' },
  { code: 'SAFETY / 04', icon: 'shield', value: alertCount.value, unit: '条', label: '实时风险告警', progress: alertCount.value ? Math.min(100, alertCount.value * 18) : 4, note: 'AI 策略持续监测', status: alertCount.value ? '存在风险' : '安全', tone: alertCount.value ? 'danger' : 'ok' }
])

const aiNodes = [
  { name: '多源感知', en: 'PERCEPTION', icon: 'sensors' },
  { name: '路径推演', en: 'PATH PLANNING', icon: 'route' },
  { name: '协同调度', en: 'SCHEDULING', icon: 'account_tree' },
  { name: '自主导航', en: 'NAVIGATION', icon: 'near_me' },
  { name: '通信组网', en: 'NETWORKING', icon: 'cell_tower' },
  { name: '安全决策', en: 'SECURITY', icon: 'verified_user' }
]

const resources = computed(() => [
  { label: 'AI 推理负载', value: aiCoreLoad.value, tone: 'cyan' },
  { label: '集群通信负载', value: Math.min(88, onlineCount.value * 9), tone: 'green' },
  { label: '任务队列占用', value: safePlannedPath.value.length ? 46 : 8, tone: 'amber' },
  { label: '遥测数据吞吐', value: Math.min(94, onlineCount.value * 12), tone: 'cyan' }
])

const alerts = computed(() => activeDrones.value.map(item => ({ id: item.id, name: item.name || item.id, battery: Number(safeTelemetry.value[item.id]?.battery_info?.batteries?.[0]?.percent || 0) })).filter(item => item.battery > 0 && item.battery < 20))
const fleetRows = computed(() => activeDrones.value.slice(0, 4).map(item => ({ id: item.id, name: item.name || item.id, ip: item.ip || '--', state: safeTelemetry.value[item.id]?.flystate ? '飞行任务中' : '地面待命', battery: Number(safeTelemetry.value[item.id]?.battery_info?.batteries?.[0]?.percent || 0) || '--' })))
const events = computed(() => {
  if (safeLogMessages.value.length) return safeLogMessages.value.slice(0, 5).map((text, index) => ({ time: text.match(/\[(.*?)\]/)?.[1] || currentTime.value, text: text.replace(/^\[.*?\]\s*/, ''), type: index === 0 ? 'live' : 'normal' }))
  return [
    { time: currentTime.value, text: 'AI 决策引擎完成自检，等待任务输入', type: 'live' },
    { time: '--:--:--', text: '集群通信服务已就绪', type: 'normal' },
    { time: '--:--:--', text: '安全策略库加载完成', type: 'normal' },
    { time: '--:--:--', text: '等待无人机节点建立遥测链路', type: 'idle' }
  ]
})
</script>

<style scoped>
.command-dashboard { position: relative; min-height: 100%; padding: 24px; overflow: hidden; background: #080d12; color: #eef7f8; }
.dashboard-grid { position: absolute; inset: 0; pointer-events: none; background-image: linear-gradient(rgba(51,214,232,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(51,214,232,.035) 1px, transparent 1px); background-size: 32px 32px; mask-image: linear-gradient(to bottom, #000, transparent 86%); }
.dashboard-heading, .kpi-grid, .dashboard-main, .dashboard-bottom { position: relative; z-index: 1; }
.dashboard-heading { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px; }
.eyebrow { color: #33d6e8; font: 600 10px/1 'Roboto Mono', Consolas, monospace; letter-spacing: .23em; }
.eyebrow span { display: inline-block; width: 26px; height: 2px; margin: 0 9px 3px 0; background: #33d6e8; box-shadow: 0 0 8px #33d6e8; }
h1 { margin: 10px 0 6px; font-size: clamp(26px, 2.2vw, 38px); line-height: 1.1; letter-spacing: .06em; font-weight: 700; }
.dashboard-heading p { margin: 0; color: #94aab1; font-size: 13px; }
.heading-meta { display: flex; gap: 28px; padding: 10px 0; }
.heading-meta div { min-width: 120px; border-left: 1px solid rgba(116,169,190,.3); padding-left: 12px; }
.heading-meta small { display: block; margin-bottom: 5px; color: #718992; font: 9px 'Roboto Mono', Consolas, monospace; letter-spacing: .12em; }
.heading-meta strong { color: #eaf4f5; font: 15px 'Roboto Mono', Consolas, monospace; }
.heading-meta .healthy { color: #63e6a8; }.healthy i { display: inline-block; width: 6px; height: 6px; margin: 0 7px 2px 0; background: #63e6a8; box-shadow: 0 0 9px #63e6a8; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px; }
.kpi-panel, .industrial-panel { position: relative; background: linear-gradient(180deg, rgba(18,29,37,.97), rgba(10,17,22,.98)); border: 1px solid rgba(116,169,190,.25); box-shadow: inset 2px 0 0 rgba(51,214,232,.5), 0 10px 28px rgba(0,0,0,.22); }
.kpi-panel { min-height: 148px; padding: 14px 16px; }
.kpi-panel::after, .industrial-panel::after { content: ''; position: absolute; top: -1px; right: -1px; width: 18px; height: 18px; border-top: 2px solid #33d6e8; border-right: 2px solid #33d6e8; }
.kpi-top, .kpi-foot { display: flex; justify-content: space-between; align-items: center; }.kpi-top span { color: #71909b; font: 9px 'Roboto Mono', Consolas, monospace; letter-spacing: .16em; }.kpi-top .q-icon { color: #33d6e8; font-size: 19px; }
.kpi-value { margin-top: 10px; line-height: 1; }.kpi-value strong { font: 700 32px 'Roboto Mono', Consolas, monospace; }.kpi-value em { margin-left: 5px; color: #9ab1b8; font-style: normal; font-size: 11px; }
.kpi-label { margin: 5px 0 10px; color: #dce9eb; font-size: 12px; letter-spacing: .06em; }.data-track, .resource-track { height: 3px; background: rgba(123,153,163,.15); overflow: hidden; }.data-track i { display: block; height: 100%; background: #33d6e8; box-shadow: 0 0 10px #33d6e8; }
.kpi-foot { margin-top: 9px; color: #708991; font-size: 9px; }.kpi-foot b { font: 600 9px 'Roboto Mono', Consolas, monospace; }.kpi-foot .ok { color: #63e6a8; }.kpi-foot .warn { color: #f5b84b; }.kpi-foot .danger { color: #ff6b5f; }.kpi-foot .idle { color: #91a4aa; }
.dashboard-main { display: grid; grid-template-columns: minmax(0, 2fr) minmax(300px, .8fr); gap: 12px; margin-bottom: 12px; }
.panel-header { height: 46px; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; border-bottom: 1px solid rgba(116,169,190,.2); background: rgba(8,15,20,.48); }.panel-header > div { display: flex; align-items: center; }.panel-header h2 { margin: 0; color: #e9f3f4; font-size: 13px; letter-spacing: .08em; }.panel-index { margin-right: 10px; color: #33d6e8; font: 10px 'Roboto Mono', Consolas, monospace; }.mono { color: #6f8992; font: 9px 'Roboto Mono', Consolas, monospace; letter-spacing: .12em; }
.live-tag { color: #63e6a8; font: 9px 'Roboto Mono', Consolas, monospace; letter-spacing: .12em; }.live-tag i { width: 6px; height: 6px; margin-right: 7px; background: #63e6a8; box-shadow: 0 0 8px #63e6a8; animation: blink 1.7s infinite; }
.topology-stage { position: relative; height: 390px; overflow: hidden; background: radial-gradient(circle at center, rgba(51,214,232,.09), transparent 42%), linear-gradient(rgba(51,214,232,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(51,214,232,.03) 1px, transparent 1px); background-size: auto, 24px 24px, 24px 24px; }
.topology-links { position: absolute; inset: 0; width: 100%; height: 100%; fill: none; stroke: rgba(51,214,232,.3); stroke-width: 1; stroke-dasharray: 4 5; }.topology-links .outer-ring { stroke: rgba(116,169,190,.13); stroke-dasharray: 2 10; }.scan-line { position: absolute; z-index: 1; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, rgba(51,214,232,.7), transparent); box-shadow: 0 0 15px rgba(51,214,232,.4); animation: scan 5s linear infinite; }
.ai-core { position: absolute; z-index: 3; left: 50%; top: 50%; width: 128px; height: 128px; transform: translate(-50%,-50%); display: flex; flex-direction: column; justify-content: center; align-items: center; background: #0d1c23; border: 1px solid rgba(51,214,232,.75); clip-path: polygon(12% 0,88% 0,100% 12%,100% 88%,88% 100%,12% 100%,0 88%,0 12%); box-shadow: 0 0 38px rgba(51,214,232,.15); }.ai-core .q-icon { color: #33d6e8; font-size: 29px; }.ai-core strong { margin-top: 5px; font: 700 15px 'Roboto Mono', Consolas, monospace; letter-spacing: .08em; }.ai-core span { color: #76939c; font: 8px 'Roboto Mono', Consolas, monospace; }.ai-core b { margin-top: 5px; color: #63e6a8; font: 11px 'Roboto Mono', Consolas, monospace; }.core-ring { position: absolute; inset: -12px; border: 1px dashed rgba(51,214,232,.28); border-radius: 50%; animation: rotate 14s linear infinite; }
.topology-node { position: absolute; z-index: 2; min-width: 130px; display: flex; align-items: center; gap: 9px; padding: 9px 10px; background: rgba(11,22,28,.96); border: 1px solid rgba(116,169,190,.3); box-shadow: inset 2px 0 #33d6e8; }.topology-node > .q-icon { color: #33d6e8; font-size: 20px; }.topology-node strong,.topology-node span { display:block; }.topology-node strong { font-size: 11px; }.topology-node span { margin-top: 2px; color: #66818a; font: 7px 'Roboto Mono', Consolas, monospace; letter-spacing: .08em; }.topology-node i { position: absolute; right: 7px; top: 7px; width: 4px; height: 4px; background: #63e6a8; box-shadow: 0 0 6px #63e6a8; }.node-1 { left: 50%; top: 8px; transform: translateX(-50%); }.node-2 { right: 6%; top: 72px; }.node-3 { right: 6%; bottom: 62px; }.node-4 { left: 50%; bottom: 7px; transform: translateX(-50%); }.node-5 { left: 6%; bottom: 62px; }.node-6 { left: 6%; top: 72px; }.stage-corner { position: absolute; color: #45616b; font: 8px 'Roboto Mono', Consolas, monospace; letter-spacing: .1em; }.top-left { top: 10px; left: 12px; }.bottom-right { right: 12px; bottom: 9px; }
.topology-footer { display: grid; grid-template-columns: repeat(4,1fr); min-height: 46px; border-top: 1px solid rgba(116,169,190,.18); }.topology-footer div { display:flex; justify-content:center; align-items:center; gap:10px; border-right: 1px solid rgba(116,169,190,.15); font-size:10px; }.topology-footer span { color:#78929a; }.topology-footer b { color:#63e6a8; font:8px 'Roboto Mono',Consolas,monospace; }
.side-stack { display: grid; grid-template-rows: 1.25fr .75fr; gap: 12px; }.resource-panel { padding-bottom: 12px; }.resource-row { padding: 12px 16px 0; }.resource-row > div:first-child { display:flex; justify-content:space-between; margin-bottom:7px; color:#9bb0b6; font-size:10px; }.resource-row b { color:#dcebed; font:10px 'Roboto Mono',Consolas,monospace; }.resource-track i { display:block;height:100%; }.resource-track .cyan { background:#33d6e8; }.resource-track .green { background:#63e6a8; }.resource-track .amber { background:#f5b84b; }.resource-summary { display:grid;grid-template-columns:repeat(3,1fr);margin:18px 14px 0;border:1px solid rgba(116,169,190,.17); }.resource-summary div { padding:10px;border-right:1px solid rgba(116,169,190,.17); }.resource-summary small { display:block;color:#6f8992;font-size:8px; }.resource-summary strong { font:17px 'Roboto Mono',Consolas,monospace; }.resource-summary em { margin-left:2px;color:#72909a;font-size:8px;font-style:normal; }.alert-count { min-width:24px;padding:2px 6px;text-align:center;color:#f5b84b;border:1px solid rgba(245,184,75,.4);font:10px 'Roboto Mono',Consolas,monospace; }.alert-list { padding:13px; }.empty-alert,.alert-item { display:flex;align-items:center;gap:10px;min-height:62px;padding:10px;background:rgba(8,16,21,.55);border:1px solid rgba(116,169,190,.14); }.empty-alert > .q-icon { color:#63e6a8;font-size:25px; }.empty-alert strong,.empty-alert span,.alert-item strong,.alert-item span { display:block; }.empty-alert strong,.alert-item strong { font-size:11px; }.empty-alert span,.alert-item span { margin-top:3px;color:#708991;font-size:9px; }.alert-item i { width:5px;height:30px;background:#ff6b5f; }.alert-item time { margin-left:auto;color:#ff6b5f;font:8px 'Roboto Mono',Consolas,monospace; }
.dashboard-bottom { display:grid;grid-template-columns:minmax(0,1.45fr) minmax(260px,.8fr) minmax(240px,.65fr);gap:12px; }.panel-header button { display:flex;align-items:center;gap:5px;color:#33d6e8;background:none;border:0;font-size:10px;cursor:pointer; }.table-head,.table-row { display:grid;grid-template-columns:1.1fr 1.2fr .9fr .6fr .9fr;align-items:center;min-height:36px;padding:0 14px;column-gap:12px; }.table-head { color:#69828a;background:rgba(8,15,20,.45);font:8px 'Roboto Mono',Consolas,monospace;letter-spacing:.08em; }.table-row { color:#cbdadd;border-top:1px solid rgba(116,169,190,.12);font-size:9px; }.table-row > span:first-child { color:#ecf5f6; }.online-dot { display:inline-block;width:5px;height:5px;margin-right:7px;background:#63e6a8;box-shadow:0 0 6px #63e6a8; }.signal-bars { color:#33d6e8;letter-spacing:1px; }.table-empty { min-height:108px;display:flex;align-items:center;justify-content:center;gap:14px;color:#8da2a8; }.table-empty strong,.table-empty small { display:block; }.table-empty strong { color:#bfced1;font-size:11px; }.table-empty small { margin-top:4px;font-size:9px; }.empty-signal { width:28px;height:28px;border:1px solid #33d6e8;border-radius:50%;box-shadow:0 0 0 7px rgba(51,214,232,.06),0 0 18px rgba(51,214,232,.12); }.event-list { padding:8px 12px; }.event-list > div { display:grid;grid-template-columns:54px 6px 1fr;align-items:center;gap:8px;min-height:31px;border-bottom:1px solid rgba(116,169,190,.1); }.event-list time { color:#607981;font:8px 'Roboto Mono',Consolas,monospace; }.event-list i { width:5px;height:5px;background:#607981; }.event-list i.live { background:#33d6e8;box-shadow:0 0 7px #33d6e8; }.event-list i.idle { background:#f5b84b; }.event-list span { color:#a8babf;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }.quick-actions { padding-bottom:8px; }.quick-actions > button { width:calc(100% - 16px);min-height:43px;margin:8px 8px 0;display:flex;align-items:center;gap:9px;padding:7px 9px;color:#d8e7e9;background:rgba(12,24,30,.8);border:1px solid rgba(116,169,190,.2);text-align:left;cursor:pointer;transition:.2s; }.quick-actions > button:hover { border-color:#33d6e8;background:rgba(51,214,232,.08); }.quick-actions button > .q-icon:first-child { color:#33d6e8;font-size:18px; }.quick-actions button > .q-icon:last-child { margin-left:auto;color:#59737c;font-size:13px; }.quick-actions strong,.quick-actions span { display:block; }.quick-actions strong { font-size:10px; }.quick-actions span { margin-top:2px;color:#67818a;font-size:8px; }
@keyframes scan { from { transform:translateY(0); } to { transform:translateY(390px); } } @keyframes rotate { to { transform:rotate(360deg); } } @keyframes blink { 50% { opacity:.35; } }
@media (max-width: 1180px) { .kpi-grid { grid-template-columns:repeat(2,1fr); }.dashboard-main { grid-template-columns:1fr; }.side-stack { grid-template-columns:1fr 1fr;grid-template-rows:auto; }.dashboard-bottom { grid-template-columns:1fr 1fr; }.quick-actions { grid-column:1/-1; }.quick-actions > button { width:calc(33.333% - 12px);display:inline-flex;margin-right:0; } }
@media (max-width: 760px) { .command-dashboard { padding:14px; }.dashboard-heading { align-items:flex-start; }.heading-meta { display:none; }.kpi-grid,.side-stack,.dashboard-bottom { grid-template-columns:1fr; }.quick-actions { grid-column:auto; }.quick-actions > button { width:calc(100% - 16px); }.topology-stage { height:420px; }.topology-node { min-width:108px; }.node-2,.node-3 { right:2%; }.node-5,.node-6 { left:2%; }.table-head { display:none; }.table-row { grid-template-columns:1fr 1fr;row-gap:8px;padding:10px 14px; }.topology-footer { grid-template-columns:repeat(2,1fr); }.topology-footer div { min-height:36px;border-bottom:1px solid rgba(116,169,190,.12); } }
</style>
