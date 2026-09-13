import { defineStore, acceptHMRUpdate } from 'pinia'

export const useLayoutStore = defineStore('layout', {
  state: () => ({
    controlPanelShow: false
  }),

  getters: {

  },

  actions: {
    increment() {
      this.counter++
    }
  }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useLayoutStore, import.meta.hot))
}
