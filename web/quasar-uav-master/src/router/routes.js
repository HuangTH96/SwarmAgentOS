const routes = [
  {
    path: '/login',
    component: () => import('layouts/AuthLayout.vue'),
    children: [
      { path: '', component: () => import('pages/LoginPage.vue') }
    ]
  },
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', component: () => import('pages/IndexPage.vue') },
      // 集群管理
      { path: '/cluster/ingress', component: () => import('pages/cluster/IngressPage.vue') },
      { path: '/cluster/auth', component: () => import('pages/cluster/AuthPage.vue') },
      { path: '/cluster/status', component: () => import('pages/cluster/StatusPage.vue') },

      // 单机控制
      { path: '/single/flight', component: () => import('pages/single/FlightControlPage.vue') },
      { path: '/single/avoidance', component: () => import('pages/single/AvoidancePage.vue') },
      { path: '/single/path-planning', component: () => import('pages/single/PathPlanningPage.vue') },
      { path: '/single/vln', component: () => import('pages/single/VisionLanguageNavPage.vue') },


      // 集群控制
      { path: '/swarm/control', component: () => import('pages/swarm/CooperativeControlPage.vue') },
      { path: '/swarm/formation', component: () => import('pages/swarm/FormationPage.vue') },
      { path: '/swarm/avoidance', component: () => import('pages/swarm/CooperativeAvoidancePage.vue') },
      { path: '/swarm/vision-voice', component: () => import('pages/swarm/VisionVoiceNavPage.vue') },

      // 任务指控
      { path: '/mission/scene', component: () => import('pages/mission/SceneSetupPage.vue') },
      { path: '/mission/task', component: () => import('pages/mission/MissionSetupPage.vue') },
      { path: '/mission/ai-planning', component: () => import('pages/mission/AiTaskPlanningPage.vue') },

      // 集群图传
      { path: '/stream/video', component: () => import('pages/stream/VideoStreamPage.vue') },
      { path: '/stream/semantic', component: () => import('pages/stream/SemanticStreamPage.vue') },

      // 网络管理
      { path: '/network/topology', component: () => import('pages/network/NetworkTopologyPage.vue') },
      { path: '/network/cellular', component: () => import('pages/network/CellularCommPage.vue') },
      { path: '/network/mesh', component: () => import('pages/network/MeshCommPage.vue') },
      { path: '/network/select', component: () => import('pages/network/NetworkSelectPage.vue') },

      // 算力管理
      { path: '/compute/sense', component: () => import('pages/compute/ComputeSensePage.vue') },
      { path: '/compute/schedule', component: () => import('pages/compute/ComputeSchedulePage.vue') },

      // 无人机大模型
      { path: '/models/base', component: () => import('pages/models/UavBaseModelPage.vue') },
      { path: '/models/domain', component: () => import('pages/models/UavDomainModelPage.vue') },

      // 无人机安全
      { path: '/security/auth', component: () => import('pages/security/IdentityAuthPage.vue') },
      { path: '/security/comm', component: () => import('pages/security/CommSecurityPage.vue') },
      { path: '/security/info', component: () => import('pages/security/InfoSecurityPage.vue') },
      { path: '/security/func', component: () => import('pages/security/FuncSecurityPage.vue') },
      { path: '/security/model', component: () => import('pages/security/ModelSecurityPage.vue') },

      // 无人孪生平台
      { path: '/twin', component: () => import('pages/twin/TwinPlatformPage.vue') },

      // 数据管理
      { path: '/data', component: () => import('pages/data/DataManagementPage.vue') },
      
      // 系统设置
      { path: '/settings', component: () => import('pages/SettingsPage.vue') },
    ]
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes


