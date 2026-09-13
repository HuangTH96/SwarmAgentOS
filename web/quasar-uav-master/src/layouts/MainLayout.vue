<template>
  <q-layout view="hHh lpR fFf" class="tech-layout">
    <!-- 顶部工具栏 -->
    <q-header elevated class="tech-header">
      <q-toolbar class="q-px-auto tech-toolbar">
        <q-btn flat dense round icon="menu" @click="drawer = !drawer" class="tech-btn menu-btn" aria-label="打开导航" />
        <div class="brand-lockup">
          <div class="brand-mark"><q-icon name="flight_takeoff" size="22px" /></div>
          <div class="brand-copy">
            <div class="brand-title">无人机集群操作 OS</div>
            <div class="brand-subtitle">UAV SWARM COMMAND CENTER <span class="brand-dot"></span> ONLINE</div>
          </div>
        </div>
        <div class="header-status"><span class="status-pulse"></span><span>系统运行中</span><span class="status-divider"></span><span class="status-time">LOCAL / 8081</span></div>
        <q-toolbar-title class="text-weight-bold tech-text">无人机集群操作系统</q-toolbar-title>
        <q-space />
        
        <!-- 设置按钮 -->
        <q-btn flat round icon="settings" class="tech-btn">
          <q-menu>
            <q-list style="min-width: 200px">
              <q-item clickable v-close-popup @click="goToSettings">
                <q-item-section avatar>
                  <q-icon name="tune" color="primary" />
                </q-item-section>
                <q-item-section>系统设置</q-item-section>
              </q-item>
              
              <q-item clickable v-close-popup @click="showUserInfo">
                <q-item-section avatar>
                  <q-icon name="account_circle" color="primary" />
                </q-item-section>
                <q-item-section>用户信息</q-item-section>
              </q-item>
              
              <q-separator />
              
              <q-item clickable v-close-popup @click="handleLogout">
                <q-item-section avatar>
                  <q-icon name="logout" color="negative" />
                </q-item-section>
                <q-item-section>退出登录</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </q-toolbar>
    </q-header>

    <!-- 左侧菜单 -->
    <q-drawer v-model="drawer" show-if-above bordered :width="220" class="tech-drawer">
      <q-list padding class="tech-menu">
        <q-item clickable v-ripple to="/" exact class="tech-menu-item">
          <q-item-section avatar><q-icon name="dashboard" class="tech-icon" /></q-item-section>
          <q-item-section class="tech-text">主控制台</q-item-section>
        </q-item>

        <q-expansion-item icon="flight_takeoff" label="单机控制" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/single/flight" class="tech-menu-item">
            <q-item-section avatar><q-icon name="flight" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">飞行控制</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/single/avoidance" class="tech-menu-item">
            <q-item-section avatar><q-icon name="radar" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">单机避障</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/single/path-planning" class="tech-menu-item">
            <q-item-section avatar><q-icon name="route" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">航迹规划</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/single/vln" class="tech-menu-item">
            <q-item-section avatar><q-icon name="psychology" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">视觉语言导航</q-item-section>
          </q-item>

        </q-expansion-item>

        <q-expansion-item icon="groups" label="集群控制" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/swarm/control" class="tech-menu-item">
            <q-item-section avatar><q-icon name="tune" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">协同控制</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/swarm/formation" class="tech-menu-item">
            <q-item-section avatar><q-icon name="polyline" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">协同编队</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/swarm/avoidance" class="tech-menu-item">
            <q-item-section avatar><q-icon name="sensors" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">协同避障</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/swarm/vision-voice" class="tech-menu-item">
            <q-item-section avatar><q-icon name="smart_toy" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">视觉语音导航</q-item-section>
          </q-item>

        </q-expansion-item>

        <q-expansion-item icon="hub" label="集群管理" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/cluster/ingress" class="tech-menu-item">
            <q-item-section avatar><q-icon name="login" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">无人机接入</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/cluster/auth" class="tech-menu-item">
            <q-item-section avatar><q-icon name="verified_user" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">无人机认证</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/cluster/status" class="tech-menu-item">
            <q-item-section avatar><q-icon name="insights" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">无人机状态</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="assignment" label="任务指控" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/mission/scene" class="tech-menu-item">
            <q-item-section avatar><q-icon name="category" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">场景设置</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/mission/task" class="tech-menu-item">
            <q-item-section avatar><q-icon name="rule" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">任务设置</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/mission/ai-planning" class="tech-menu-item">
            <q-item-section avatar><q-icon name="smart_toy" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">AI 任务规划</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="cell_tower" label="集群图传" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/stream/video" class="tech-menu-item">
            <q-item-section avatar><q-icon name="videocam" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">视频传输</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/stream/semantic" class="tech-menu-item">
            <q-item-section avatar><q-icon name="image_search" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">语义图传</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="lan" label="网络管理" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/network/topology" class="tech-menu-item">
            <q-item-section avatar><q-icon name="hub" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">网络拓扑</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/network/cellular" class="tech-menu-item">
            <q-item-section avatar><q-icon name="network_cell" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">4G/5G通信</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/network/mesh" class="tech-menu-item">
            <q-item-section avatar><q-icon name="device_hub" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">自组网通信</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/network/select" class="tech-menu-item">
            <q-item-section avatar><q-icon name="swipe" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">网络选择</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="memory" label="算力管理" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/compute/sense" class="tech-menu-item">
            <q-item-section avatar><q-icon name="sensors" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">算力感知</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/compute/schedule" class="tech-menu-item">
            <q-item-section avatar><q-icon name="schedule" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">算力调度</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="psychology" label="无人机大模型" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/models/base" class="tech-menu-item">
            <q-item-section avatar><q-icon name="dataset" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">无人机基础模型</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/models/domain" class="tech-menu-item">
            <q-item-section avatar><q-icon name="label_important" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">无人机领域模型</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="security" label="无人机安全" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/security/auth" class="tech-menu-item">
            <q-item-section avatar><q-icon name="verified_user" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">身份认证</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/security/comm" class="tech-menu-item">
            <q-item-section avatar><q-icon name="vpn_lock" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">通信安全</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/security/info" class="tech-menu-item">
            <q-item-section avatar><q-icon name="shield" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">信息安全</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/security/func" class="tech-menu-item">
            <q-item-section avatar><q-icon name="fact_check" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">功能安全</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/security/model" class="tech-menu-item">
            <q-item-section avatar><q-icon name="account_tree" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">模型安全</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="view_in_ar" label="无人孪生平台" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/twin" class="tech-menu-item">
            <q-item-section avatar><q-icon name="view_in_ar" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">无人孪生平台</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-expansion-item icon="storage" label="数据管理" header-class="tech-text" expand-separator>
          <q-item clickable v-ripple to="/data" class="tech-menu-item">
            <q-item-section avatar><q-icon name="storage" class="tech-icon" /></q-item-section>
            <q-item-section class="tech-text">数据管理</q-item-section>
          </q-item>
        </q-expansion-item>
      </q-list>
    </q-drawer>

    <!-- 页面主体 -->
    <q-page-container class="tech-page-container">
      <router-view/>
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref } from 'vue'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useDroneStore } from 'stores/drone'
import { useAuthStore } from 'stores/auth'

const drawer = ref(true)
const router = useRouter()
const $q = useQuasar()
const droneStore = useDroneStore()
const authStore = useAuthStore()

onMounted(() => {
  if (authStore.isAuthenticated) {
    droneStore.connectWebSocket()
  }
})

// 跳转到设置页面
function goToSettings() {
  router.push('/settings')
}

// 显示用户信息
function showUserInfo() {
  $q.dialog({
    title: '用户信息',
    message: `当前用户: ${authStore.username || '未知'}`,
    ok: {
      label: '确定',
      color: 'primary'
    }
  })
}

// 退出登录
function handleLogout() {
  $q.dialog({
    title: '确认退出',
    message: '确定要退出登录吗？',
    cancel: {
      label: '取消',
      color: 'grey',
      flat: true
    },
    ok: {
      label: '退出',
      color: 'negative'
    },
    persistent: true
  }).onOk(() => {
    authStore.logout()
    router.push('/login')
    $q.notify({
      type: 'positive',
      message: '已成功退出登录',
      position: 'top'
    })
  })
}
</script>

<style scoped>
.tech-layout {
  background: #080d12;
}

.tech-header {
  background: #0b131a;
  border-bottom: 1px solid rgba(51, 214, 232, .5);
  box-shadow: 0 6px 24px rgba(0, 0, 0, .44);
}

.tech-toolbar {
  min-height: 72px;
  padding: 0 22px 0 14px;
  background: linear-gradient(90deg, #0b141b, #101b22 58%, #0b1319);
  position: relative;
}

.tech-toolbar::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: linear-gradient(90deg, #33d6e8 0 25%, rgba(51, 214, 232, .2) 25% 72%, #f5b84b 72% 79%, transparent 79%);
  opacity: .85;
}

.brand-lockup { display: flex; align-items: center; gap: 12px; margin-left: 12px; }
.brand-mark { width: 40px; height: 40px; display: grid; place-items: center; color: #071319; background: #33d6e8; border: 1px solid #a6f4fb; border-radius: 2px; box-shadow: 0 0 16px rgba(51, 214, 232, .22); transform: skewX(-7deg); }
.brand-mark .q-icon { transform: skewX(7deg); }
.brand-title { color: #f3fbfb; font-size: 21px; line-height: 1.1; font-weight: 700; letter-spacing: .08em; white-space: nowrap; }
.brand-subtitle { color: #91adb7; margin-top: 4px; font-family: 'Roboto Mono', Consolas, monospace; font-size: 9px; letter-spacing: .2em; white-space: nowrap; }
.brand-dot { display: inline-block; width: 5px; height: 5px; margin: 0 6px 1px; border-radius: 50%; background: #36e7a4; box-shadow: 0 0 8px #36e7a4; }
.header-status { display: flex; align-items: center; gap: 8px; margin-left: 28px; padding: 7px 10px; color: #d4e2e5; font-family: 'Roboto Mono', Consolas, monospace; font-size: 10px; letter-spacing: .08em; white-space: nowrap; background: #091116; border: 1px solid rgba(116,169,190,.26); }
.status-pulse { width: 7px; height: 7px; border-radius: 50%; background: #36e7a4; box-shadow: 0 0 0 4px rgba(54, 231, 164, .12), 0 0 12px #36e7a4; }
.status-divider { height: 16px; width: 1px; background: rgba(126, 180, 210, .3); margin: 0 3px; }
.status-time { color: #6f91aa; font-size: 10px; letter-spacing: .14em; }
.menu-btn { margin-right: 2px; }
@media (max-width: 760px) {
  .tech-toolbar { padding-right: 10px; }
  .brand-title { font-size: 16px; letter-spacing: .04em; }
  .brand-subtitle, .header-status { display: none; }
  .brand-mark { width: 34px; height: 34px; }
}

.tech-btn {
  color: #19c8ff;
  text-shadow: 0 0 8px rgba(25, 200, 255, .38);
}

.tech-btn:hover {
  background: rgba(25, 200, 255, .13);
  box-shadow: 0 0 14px rgba(25, 200, 255, .26);
}

.tech-text {
  color: #e8f4ff;
  text-shadow: 0 0 6px rgba(25, 200, 255, .12);
}

.tech-drawer {
  background: linear-gradient(180deg, #101a21 0%, #0a1117 100%);
  border-right: 1px solid rgba(116, 169, 190, .3);
  box-shadow: 4px 0 24px rgba(0, 0, 0, .32);
}

.tech-menu {
  background: transparent;
}

.tech-menu-item {
  background: rgba(16, 29, 37, .72);
  border-radius: 2px;
  margin: 4px 8px;
  transition: all 0.3s ease;
  border: 1px solid rgba(116, 169, 190, .14);
}

.tech-menu-item:hover {
  background: rgba(25, 200, 255, .1);
  box-shadow: 0 4px 15px rgba(25, 200, 255, .14);
  transform: translateX(2px);
}

.tech-menu-item.router-link-active {
  background: linear-gradient(90deg, rgba(25, 200, 255, .17), rgba(25, 200, 255, .04));
  border-left: 3px solid #19c8ff;
  box-shadow: 0 4px 15px rgba(25, 200, 255, .2);
}

.tech-icon {
  color: #19c8ff;
  text-shadow: 0 0 8px rgba(25, 200, 255, .4);
}

.tech-page-container {
  background: transparent;
}
</style>
