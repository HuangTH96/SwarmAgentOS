import { boot } from 'quasar/wrappers'
import axios from 'axios'
import { useAuthStore } from 'stores/auth'
import { api } from 'src/services/api'

export default boot(({ app, router, store }) => {
  // for use inside Vue files (Options API) through this.$axios and this.$api
  app.config.globalProperties.$axios = axios
  app.config.globalProperties.$api = api

  const auth = useAuthStore(store)

  api.interceptors.request.use((config) => {
    const token = auth.token || localStorage.getItem('auth_token')
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  api.interceptors.response.use(
    (resp) => resp,
    async (error) => {
      const status = error?.response?.status
      const url = error?.config?.url || ''
      if (status === 401 && !url.includes('/api/auth/login')) {
        auth.logout()
        const current = router?.currentRoute?.value
        if (current?.path !== '/login') {
          await router.replace({
            path: '/login',
            query: { redirect: current?.fullPath || '/' }
          })
        }
      }
      return Promise.reject(error)
    }
  )
})

export { api }


