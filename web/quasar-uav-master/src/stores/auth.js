import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from 'src/services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || '')
  const user = ref(null)
  const meLoaded = ref(false)

  const isAuthenticated = computed(() => !!token.value)

  if (token.value) {
    api.defaults.headers.common.Authorization = `Bearer ${token.value}`
  }

  function setToken(nextToken) {
    token.value = nextToken || ''
    if (token.value) {
      localStorage.setItem('auth_token', token.value)
      api.defaults.headers.common.Authorization = `Bearer ${token.value}`
    } else {
      localStorage.removeItem('auth_token')
      delete api.defaults.headers.common.Authorization
    }
  }

  async function login(username, password) {
    const resp = await api.post('/api/auth/login', { username, password })
    setToken(resp.data.access_token)
    await fetchMe()
  }

  async function fetchMe() {
    if (!token.value) {
      user.value = null
      meLoaded.value = true
      return
    }

    const resp = await api.get('/api/auth/me')
    user.value = resp.data
    meLoaded.value = true
  }

  function logout() {
    setToken('')
    user.value = null
    meLoaded.value = false
  }

  return {
    token,
    user,
    meLoaded,
    isAuthenticated,
    login,
    fetchMe,
    logout,
  }
})
