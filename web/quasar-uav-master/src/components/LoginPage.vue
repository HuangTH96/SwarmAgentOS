<template>
  <q-page class="row items-center justify-center">
    <div style="width: 360px; max-width: 90vw;">
      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6">登录</div>
          <div class="text-caption text-grey-7">无人机集群操作系统</div>
        </q-card-section>

        <q-separator />

        <q-card-section>
          <q-form @submit.prevent="onSubmit">
            <q-input
              v-model="username"
              label="用户名"
              outlined
              dense
              autocomplete="username"
              :disable="loading"
              class="q-mb-md"
            />
            <q-input
              v-model="password"
              label="密码"
              type="password"
              outlined
              dense
              autocomplete="current-password"
              :disable="loading"
              class="q-mb-md"
            />

            <q-btn
              type="submit"
              color="primary"
              label="登录"
              unelevated
              class="full-width"
              :loading="loading"
            />
          </q-form>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'

const $q = useQuasar()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function onSubmit () {
  if (!username.value || !password.value) {
    $q.notify({ type: 'negative', message: '请输入用户名和密码' })
    return
  }

  loading.value = true
  try {
    await auth.login(username.value, password.value)
    const redirect = route.query.redirect || '/'
    router.replace(redirect)
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '登录失败'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    loading.value = false
  }
}
</script>

