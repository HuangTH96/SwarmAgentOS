// src/stores/drone.js
import {defineStore} from 'pinia'
import {ref, computed} from 'vue'
import {api} from 'src/services/api'

// WebSocket 地址 - 与 single.html 保持一致
const WS_BASE_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`

export const useDroneStore = defineStore('drone', () => {
  // --- State ---
  const droneList = ref([])
  const selectedDroneId = ref(null)
  const selectedDroneIds = ref([])
  const multiSelectMode = ref(false)
  const rawTelemetry = ref({})
  const acceptedClients = ref({})
  const logMessages = ref([])
  let websocket = null

  // --- 新增：路径规划状态 ---
  const isPathPlanning = ref(false) // 是否处于路径规划模式
  const plannedPath = ref([])      // 存储规划的路径点数组

  // --- 新增：轮询相关 ---
  let clientPollingInterval = null; // 用于存储定时器的ID

  // --- Getters (Computed Properties) ---

  const selectedDrone = computed(() => {
    // ... (此部分无变化)
    if (!selectedDroneId.value || droneList.value.length === 0) {
      return null
    }
    return droneList.value.find(d => d.id === selectedDroneId.value)
  })

  const droneStatus = computed(() => {
    // ... (此部分无变化)
    const telemetry = selectedDroneId.value ? rawTelemetry.value[selectedDroneId.value] : null;
    if (!selectedDrone.value || !telemetry) {
      return {
        flystate: 0,
        isConnected: false,
        isFlying: false,
        battery: {percent: 0},
        altitude: 0,
        latitude: 0,
        longitude: 0,
        speed: 0,
        heading: 0,
        longtitude: 0,
        height: 0,
        head: 0,
      }
    }
    return {
      isConnected: true,
      isFlying: telemetry.flystate != 0,
      battery: telemetry.battery_info?.batteries?.[0] || {percent: 0},
      altitude: telemetry.height || 0,
      latitude: telemetry.latitude || 0,
      longitude: telemetry.longtitude || 0,
      speed: telemetry.speed || 0,
      heading: telemetry.head || 0,
      ...telemetry,
    }
  })

  const isConnected = computed(() => !!selectedDrone.value)
  const batteryLevel = computed(() => droneStatus.value.battery?.percent.toFixed(2) || 0)

  // --- Actions (Methods) ---

  function addLog(message, type = 'info') {
    // ... (此部分无变化)
    const timestamp = new Date().toLocaleTimeString();
    logMessages.value.unshift(`[${timestamp}] ${message}`);
    if (logMessages.value.length > 100) {
      logMessages.value.pop();
    }
    console.log(`[${type.toUpperCase()}] ${message}`);
  }

  // --- 修改：WebSocket 连接与轮询 ---
  function connectWebSocket() {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      addLog("WebSocket 已连接，无需重复连接。", 'warn');
      return;
    }

     const token = localStorage.getItem('auth_token')
     if (!token) {
       addLog('未检测到登录信息，WebSocket 不连接。', 'warn')
       return
     }

     const wsUrl = `${WS_BASE_URL}/ws/control?token=${encodeURIComponent(token)}`

    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      addLog("WebSocket 连接成功。", 'success');
      // 连接成功后，立即请求一次无人机列表
      fetchClients();
      // 并开始定时轮询
      startPollingClients();
    };

    websocket.onmessage = (event) => {
        // ... (onmessage 内部逻辑无变化)
        try {
            const message = JSON.parse(event.data);
            const clientId = message.client_id;
            if (message.type === "telemetry_update") {
                const isAccepted = acceptedClients.value[clientId] !== false
                if (!isAccepted) return
                rawTelemetry.value = {...rawTelemetry.value, [clientId]: {...rawTelemetry.value[clientId], ...message.telemetry}}
            } else if (message.type === "battery_update") {
                const isAccepted = acceptedClients.value[clientId] !== false
                if (!isAccepted) return
                rawTelemetry.value = {...rawTelemetry.value, [clientId]: {...rawTelemetry.value[clientId], battery_info: message.battery_info}}
            } else if (message.type === "client_update") {
                addLog("收到客户端列表更新通知，正在刷新...");
                fetchClients();
            }
        } catch (error) {
            addLog(`解析 WebSocket 消息失败: ${error}`, 'error');
        }
    };

    websocket.onerror = (event) => {
      addLog("WebSocket 发生错误。", 'error');
      // 发生错误时停止轮询
      stopPollingClients();
    };

    websocket.onclose = (event) => {
      addLog(`WebSocket 连接已关闭。代码: ${event.code}`, 'warn');
      websocket = null;
      // 连接关闭时停止轮询
      stopPollingClients();
      // 5秒后尝试重连
      setTimeout(connectWebSocket, 5000);
    };
  }

  // --- 新增：开始和停止轮询无人机列表的函数 ---
  /**
   * @description 启动一个定时器，每5秒获取一次无人机列表
   */
  function startPollingClients() {
    // 先清除可能存在的旧定时器，防止重复执行
    stopPollingClients();
    addLog("已启动无人机列表自动刷新（5秒/次）。");
    clientPollingInterval = setInterval(fetchClients, 5000);
  }

  /**
   * @description 停止轮询无人机列表
   */
  function stopPollingClients() {
    if (clientPollingInterval) {
      clearInterval(clientPollingInterval);
      clientPollingInterval = null;
      addLog("已停止无人机列表自动刷新。");
    }
  }


  async function fetchClients() {
    try {
      const response = await api.get('/api/clients');
      const newClients = response.data.clients || [];
      // 只有在列表内容发生变化时才打印日志，避免刷屏
      if (JSON.stringify(droneList.value) !== JSON.stringify(newClients)) {
          addLog("成功获取并更新无人机列表。");
          droneList.value = newClients;
      }

      const nextAccepted = { ...acceptedClients.value }
      droneList.value.forEach(c => {
        if (typeof nextAccepted[c.id] === 'undefined') {
          nextAccepted[c.id] = true
        }
      })
      acceptedClients.value = nextAccepted
      if (droneList.value.length > 0 && !selectedDroneId.value) {
        selectedDroneId.value = droneList.value[0].id;
      }
      if (droneList.value.length === 0) {
        selectedDroneId.value = null;
      }
    } catch (error) {
      addLog(`获取无人机列表失败: ${error.message}`, 'error');
      droneList.value = [];
      selectedDroneId.value = null;
    }
  }

  async function sendCommand(command, payload = {}) {
    // ... (此部分无变化)
    console.log("发送控制指令", command, payload);
    let targetDroneIds = [];
    if (multiSelectMode.value && selectedDroneIds.value.length > 0) {
      targetDroneIds = selectedDroneIds.value;
    } else if (selectedDroneId.value) {
      targetDroneIds = [selectedDroneId.value];
    }
    if (targetDroneIds.length === 0) {
      addLog("错误: 请先选择一个或多个无人机！", 'error');
      return;
    }
    const promises = targetDroneIds.map(droneId => {
      addLog(`向 ${droneId} 发送 '${command}' 指令...`);
      console.log("Payload:", payload);
      return api.post('/api/send-command', {
        client_id: droneId,
        command: command,
        ...payload
      });
    });
    try {
      const responses = await Promise.all(promises);
      addLog(`指令成功发送到 ${targetDroneIds.length} 架无人机`, 'success');
      return responses;
    } catch (error) {
      const errorMessage = error.response?.data?.message || error.message;
      addLog(`指令失败: ${errorMessage}`, 'error');
      throw error;
    }
  }
    async function sendWaypointMission() {
    // 【修正】直接使用 plannedPath.value，而不是 useDroneStore.plannedPath
    if (plannedPath.value.length === 0) {
      addLog("路径为空，无法发送任务。", 'warn');
      return false; // 返回 false 表示没有发送
    }

    addLog(`准备发送包含 ${plannedPath.value.length} 个航点的任务...`);

    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      addLog("WebSocket 未连接，无法发送任务。", 'error');
      return false; // 返回 false 表示发送失败
    }

    let targetDroneIds = [];
    if (multiSelectMode.value && selectedDroneIds.value.length > 0) {
      targetDroneIds = selectedDroneIds.value;
    } else if (selectedDroneId.value) {
      targetDroneIds = [selectedDroneId.value];
    }

    if (targetDroneIds.length === 0) {
      addLog("未选择目标无人机，无法发送任务。", 'warn');
      return false; // 返回 false
    }

    // 【修正】后端 server.cpp 期望的 JSON 格式可能不同
    // 我们之前约定 server.cpp 接收的是一个包含 command 和 path 的顶层对象
    // 而不是嵌套在 payload 中
    targetDroneIds.forEach(droneId => {
      const message = {
        client_id: droneId,
        payload: {
          command: "execute_path", // 'command' 键直接放在顶层
          path: plannedPath.value  // 'path' 键也放在顶层
        },
      };
      addLog(`向 ${droneId} 发送航线任务...`);
      console.log("Sending mission payload:", JSON.stringify(message, null, 2));
      websocket.send(JSON.stringify(message));
    });

    return true; // 表示发送操作已成功启动
  }

  function sendJsonCommand(command_name,data) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
    let targetDroneIds = [];
    if (multiSelectMode.value && selectedDroneIds.value.length > 0) {
      targetDroneIds = selectedDroneIds.value;
    } else if (selectedDroneId.value) {
      targetDroneIds = [selectedDroneId.value];
    }
    if (targetDroneIds.length === 0) return;
    targetDroneIds.forEach(droneId => {
      const message = { client_id: droneId, payload: { command: command_name, data: data }};
      websocket.send(JSON.stringify(message));
    });
  }
  // ... (sendJoystickData, sendPosition, selectDrone 等函数无变化)
  let stopFlag = false;
  function sendJoystickData(data) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
    let targetDroneIds = [];
    if (multiSelectMode.value && selectedDroneIds.value.length > 0) {
      targetDroneIds = selectedDroneIds.value;
    } else if (selectedDroneId.value) {
      targetDroneIds = [selectedDroneId.value];
    }
    if (targetDroneIds.length === 0) return;
    targetDroneIds.forEach(droneId => {
      const message = { client_id: droneId, payload: { command: "vstick", data: data }};
      if (message.payload.data.left_stick_x != 0 || message.payload.data.left_stick_y != 0 || message.payload.data.right_stick_x != 0 || message.payload.data.right_stick_y != 0) {
        websocket.send(JSON.stringify(message));
        stopFlag = true
      } else {
        if (stopFlag) {
          websocket.send(JSON.stringify(message));
          stopFlag = false
        }
      }
    });
  }
  function sendPosition(data) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
    let targetDroneIds = [];
    if (multiSelectMode.value && selectedDroneIds.value.length > 0) {
      targetDroneIds = selectedDroneIds.value;
    } else if (selectedDroneId.value) {
      targetDroneIds = [selectedDroneId.value];
    }
    if (targetDroneIds.length === 0) return;
    targetDroneIds.forEach(droneId => {
      const positionData = { client_id: droneId, payload: { type: 'position_control', x: parseFloat(data.x), y: parseFloat(data.y), z: parseFloat(data.z), yaw: parseFloat(data.yaw) }};
      websocket.send(JSON.stringify(positionData));
    });
  }
  function selectDrone(droneId) {
    selectedDroneId.value = droneId;
    addLog(`已选择无人机: ${droneId}`);
  }
  function toggleMultiSelectMode() {
    multiSelectMode.value = !multiSelectMode.value;
    if (!multiSelectMode.value) {
      selectedDroneIds.value = [];
    }
    addLog(`多选模式: ${multiSelectMode.value ? '开启' : '关闭'}`);
  }
  function toggleDroneSelection(droneId) {
    if (!multiSelectMode.value) return;
    const index = selectedDroneIds.value.indexOf(droneId);
    if (index > -1) {
      selectedDroneIds.value.splice(index, 1);
    } else {
      selectedDroneIds.value.push(droneId);
    }
    addLog(`多选状态更新: ${selectedDroneIds.value.length} 架无人机已选中`);
  }
  function clearMultiSelection() {
    selectedDroneIds.value = [];
    addLog('已清空多选');
  }
  function selectAllDrones() {
    if (!multiSelectMode.value) return;
    selectedDroneIds.value = droneList.value.filter(d => isClientAccepted(d.id)).map(d => d.id);
    addLog(`已全选 ${selectedDroneIds.value.length} 架无人机`);
  }
  function setClientAccepted(clientId, accepted) {
    acceptedClients.value = { ...acceptedClients.value, [clientId]: !!accepted };
    if (!accepted) {
      const next = { ...rawTelemetry.value };
      delete next[clientId];
      rawTelemetry.value = next;
    }
  }
  function toggleClientAccepted(clientId) {
    const curr = acceptedClients.value[clientId] !== false;
    setClientAccepted(clientId, !curr);
  }
  function isClientAccepted(clientId) {
    return acceptedClients.value[clientId] !== false;
  }

  const lastCalculatedPosition = ref({x: '', y: '', lat: '', lng: ''})
  const originPosition = ref({lat: '', lng: ''})

  function sendOrigin(data) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
    if (!selectedDroneId.value) return;
    if (data == '' || data.lat == '' || data.lng == '') return;
    const message = { client_id: 'all', payload: { command: 'set_ros_origin', lat: parseFloat(data.lat), lon: parseFloat(data.lng) }};
    console.log(message)
    websocket.send(JSON.stringify(message));
  }
  function sendTarget(data) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
    if (!selectedDroneId.value) return;
    const message = { client_id: selectedDroneId.value, payload: { command: 'set_ros_target', x: parseFloat(data.y), y: parseFloat(data.x), z: 0, }};
    console.log(message)
    websocket.send(JSON.stringify(message));
  }

  // 路径规划 Actions ---

  /**
   * @description 开始路径规划
   */
  function startPathPlanning() {
    isPathPlanning.value = true;
    plannedPath.value = []; // 清空之前的路径
    addLog("路径规划已开始，请在地图上点击选择航点。");
  }

  /**
   * @description 向当前规划的路径中添加一个航点
   * @param {{lat: number, lng: number, height: number, heading: number}} waypoint
   */
  function addWaypoint(waypoint) {
    if (isPathPlanning.value) {
      plannedPath.value.push(waypoint);
    }
  }

  /**
   * @description 取消路径规划，并清空数据
   */
  function cancelPathPlanning() {
    isPathPlanning.value = false;
    plannedPath.value = [];
    addLog("路径规划已取消。");
  }

  async function finalizePath() {
      addLog("正在完成路径规划并发送任务...");
      isPathPlanning.value = false; // 退出规划模式

      const success = await sendWaypointMission();

      if (success) {
        addLog("航线任务已成功发送。路径已在地图上保留以供查看。", 'success');
        // 【重要】不再清空 plannedPath.value = []
        // 路径数据被保留，直到下一次 startPathPlanning 或 clearPlannedPath 被调用
        return plannedPath.value; // 返回发送的路径数据，供UI确认
      } else {
        addLog("航线任务发送失败，路径已保留，请检查连接或选择无人机后重试。", 'error');
        isPathPlanning.value = true; // 发送失败，允许用户重试
        return null; // 返回 null 表示失败
      }
    }
  /**
   * @description 显式清除已规划或已发送的路径数据。
   */
  function clearPlannedPath() {
      if (plannedPath.value.length > 0) {
          plannedPath.value = [];
          addLog("已清除上一次规划的路径数据。");
      }
  }
  return {
    // State
    droneList,
    selectedDroneId,
    selectedDroneIds,
    multiSelectMode,
    rawTelemetry,
    logMessages,
    lastCalculatedPosition,
    originPosition,
    acceptedClients,
    isPathPlanning,       // 新增
    plannedPath,          // 新增

    // Getters
    selectedDrone,
    droneStatus,
    isConnected,
    batteryLevel,

    // Actions
    addLog,
    connectWebSocket,
    fetchClients,
    sendCommand,
    sendJoystickData,
    selectDrone,
    sendPosition,
    sendOrigin,
    sendTarget,
    setClientAccepted,
    toggleClientAccepted,
    isClientAccepted,
    toggleMultiSelectMode,
    toggleDroneSelection,
    clearMultiSelection,
    selectAllDrones,
    startPathPlanning,    // 新增
    addWaypoint,          // 新增
    finalizePath,         // 新增
    cancelPathPlanning,   // 新增
    sendJsonCommand,
    clearPlannedPath, // 【新增】导出新函数
  }
})
