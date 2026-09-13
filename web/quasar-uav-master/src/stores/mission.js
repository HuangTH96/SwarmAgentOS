import { defineStore } from 'pinia'
import { api } from 'src/boot/axios'

export const useMissionStore = defineStore('mission', {
  state: () => ({
    currentMission: null,      // 当前任务数据
    missionList: [],           // 任务列表
    isLoading: false,          // 加载状态
    lastSavedMissionId: null,  // 最后保存的任务 ID
    currentConversations: []   // 当前任务的对话历史
  }),

  getters: {
    hasMission: (state) => state.currentMission !== null,
    isSaved: (state) => state.currentMission?.mission_id !== undefined,
    hasConversations: (state) => state.currentConversations.length > 0
  },

  actions: {
    // 设置当前任务
    setCurrentMission(mission) {
      this.currentMission = mission
      this.saveToLocalStorage()
    },

    // 从 LocalStorage 加载任务
    loadFromLocalStorage() {
      const data = localStorage.getItem('currentMission')
      if (data) {
        try {
          this.currentMission = JSON.parse(data)
        } catch (e) {
          console.error('解析任务数据失败:', e)
          this.currentMission = null
        }
      }
    },

    // 保存到 LocalStorage
    saveToLocalStorage() {
      if (this.currentMission) {
        localStorage.setItem('currentMission', JSON.stringify(this.currentMission))
      }
    },

    // 保存任务到数据库
    async saveMissionToDatabase(missionData) {
      this.isLoading = true
      try {
        const response = await api.post('/api/route-planning/save', missionData)
        this.currentMission.mission_id = response.data.mission_id
        this.currentMission.saved = true
        this.lastSavedMissionId = response.data.mission_id
        this.saveToLocalStorage()
        
        // 保存后，将当前对话历史关联到任务
        if (this.currentConversations.length > 0) {
          await this.associateConversationsWithMission(response.data.mission_id)
        }
        
        return response.data
      } catch (error) {
        throw error
      } finally {
        this.isLoading = false
      }
    },

    // 将对话历史关联到任务
    async associateConversationsWithMission(missionId) {
      try {
        const conversationIds = this.currentConversations
          .filter(c => c.id)
          .map(c => c.id)
        
        if (conversationIds.length === 0) return
        
        await api.post('/api/ai-task-conversations/associate', {
          mission_id: missionId,
          conversation_ids: conversationIds
        })
      } catch (error) {
        console.error('关联对话历史失败:', error)
      }
    },

    // 加载任务的对话历史
    async loadMissionConversations(missionId) {
      this.isLoading = true
      try {
        const response = await api.get(`/api/ai-task-conversations/mission/${missionId}`)
        this.currentConversations = response.data.messages || []
        return this.currentConversations
      } catch (error) {
        console.error('加载任务对话历史失败:', error)
        this.currentConversations = []
        throw error
      } finally {
        this.isLoading = false
      }
    },

    // 设置当前对话历史
    setCurrentConversations(conversations) {
      this.currentConversations = conversations
    },

    // 添加对话消息
    addConversation(message) {
      this.currentConversations.push(message)
    },

    // 加载任务列表
    async loadMissionList() {
      this.isLoading = true
      try {
        const response = await api.get('/api/route-planning/missions')
        this.missionList = response.data.missions
        return this.missionList
      } catch (error) {
        throw error
      } finally {
        this.isLoading = false
      }
    },

    // 加载任务详情
    async loadMissionDetail(missionId) {
      this.isLoading = true
      try {
        const response = await api.get(`/api/route-planning/missions/${missionId}`)
        this.currentMission = response.data
        this.saveToLocalStorage()
        
        // 同时加载对话历史
        await this.loadMissionConversations(missionId)
        
        return response.data
      } catch (error) {
        throw error
      } finally {
        this.isLoading = false
      }
    },

    // 删除任务
    async deleteMission(missionId) {
      this.isLoading = true
      try {
        await api.delete(`/api/route-planning/missions/${missionId}`)
        this.missionList = this.missionList.filter(m => m.id !== missionId)
        if (this.currentMission?.mission_id === missionId) {
          this.clearCurrentMission()
        }
      } catch (error) {
        throw error
      } finally {
        this.isLoading = false
      }
    },

    // 清空当前任务
    clearCurrentMission() {
      this.currentMission = null
      this.currentConversations = []
      localStorage.removeItem('currentMission')
    },

    // 清空所有数据（登出时调用）
    clearAll() {
      this.currentMission = null
      this.missionList = []
      this.lastSavedMissionId = null
      this.currentConversations = []
      localStorage.removeItem('currentMission')
    }
  }
})

