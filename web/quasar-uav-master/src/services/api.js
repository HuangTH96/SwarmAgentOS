import axios from 'axios'

export const api = axios.create({
  baseURL: ''
})

// 网络拓扑 - 获取网络指标
export async function getNetworkMetrics() {
  try {
    const response = await api.get('/api/network-metrics')
    return response.data
  } catch (error) {
    console.error('获取网络指标失败:', error)
    throw error
  }
}

