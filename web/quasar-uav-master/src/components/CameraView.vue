<template>
  <q-card flat class="tech-camera-card">
    <div class="camera-header tech-text">视频图传 (来源: {{ ip || 'N/A' }})</div>
    <div class="camera-container">
      <video
        ref="videoPlayer"
        class="tech-camera-feed"
        autoplay
        muted
        playsinline
        controls
      ></video>
    </div>
  </q-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";

// --- 配置 ---
// 修改为你的 MediaMTX 服务器的实际 IP 地址
//const MEDIAMTX_SERVER_IP = '172.24.8.229';
const MEDIAMTX_SERVER_IP = window.location.hostname;
// MediaMTX WebRTC (WHEP) API 默认端口，通常是 8889
const MEDIAMTX_WEBRTC_PORT = '8889';
// 这个前缀需要和你 ffmpeg 推流脚本中的路径前缀保持一致 (例如 "live/")
const STREAM_PREFIX = 'live';
// --- 配置结束 ---


const props = defineProps({
  id: String,
});

const videoPlayer = ref(null);
let peerConnection = null;

const streamPath = computed(() => {
  if (!props.id) {
    return null;
  }
  // 将 IP 地址中的 '.' 替换为 '_' 来创建唯一的流名称
  // 例如: "192.168.1.101" -> "192_168_1_101"
  const streamName = props.id.replace(/\./g, '_');
  console.log(props);
  // 拼接成完整的路径: "live/192_168_1_101"
  return `${STREAM_PREFIX}/${streamName}`;
});

const startWebRTCStream = async (path) => {
  if (!path) {
    console.log("Stream path is not defined for IP:", props.id);
    return;
  }

  if (peerConnection) {
    peerConnection.close();
  }

  peerConnection = new RTCPeerConnection();

  peerConnection.ontrack = (event) => {
    if (videoPlayer.value) {
      console.log(`[${props.id}] Received remote stream, attaching to video element.`);
      videoPlayer.value.srcObject = event.streams[0];
    }
  };

  peerConnection.addTransceiver("video", { direction: "recvonly" });
  // 如果你的流有音频, 取消注释下面这行
  // peerConnection.addTransceiver('audio', { direction: 'recvonly' });

  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);

  // [修改点 2] 使用配置变量动态构建 API URL
  const apiUrl = `http://${MEDIAMTX_SERVER_IP}:${MEDIAMTX_WEBRTC_PORT}/${path}/whep`;
  console.log(`Connecting to WHEP endpoint: ${apiUrl}`);

  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/sdp",
      },
      body: peerConnection.localDescription.sdp,
    });

    if (!response.ok) {
        throw new Error(`Server responded with status ${response.status} ${response.statusText}`);
    }

    const answerSdp = await response.text();
    await peerConnection.setRemoteDescription(
      new RTCSessionDescription({ type: "answer", sdp: answerSdp })
    );
    console.log(`[${props.id}] WebRTC connection established for path: ${path}`);

  } catch (error) {
    console.error(`[${props.id}] Failed to start WebRTC stream for path ${path}:`, error);
    // 可选：在这里更新UI，显示连接失败
    if (videoPlayer.value) {
        videoPlayer.value.srcObject = null; // 清空视频
    }
  }
};

onMounted(() => {
  console.log(`[${props.id}] Component mounted. Attempting to start stream.`);
  startWebRTCStream(streamPath.value);
});

onUnmounted(() => {
  if (peerConnection) {
    console.log(`[${props.id}] Component unmounted. Closing WebRTC connection.`);
    peerConnection.close();
    peerConnection = null;
  }
});

watch(() => props.id, (newIp, oldIp) => {
    console.log(`[${oldIp} -> ${newIp}] IP prop changed. Reconnecting stream...`);
    // streamPath 是计算属性, 会自动更新, 我们只需用新路径重新调用函数
    startWebRTCStream(streamPath.value);
}, { immediate: false }); // immediate: false 避免 onMounted 时重复执行

</script>

<style scoped>
/* 您的样式代码保持不变，可以完美复用 */
.tech-camera-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(245, 248, 250, 0.95) 100%);
  border: 1px solid #4A90E2;
  border-radius: 12px;
  box-shadow:
    0 8px 32px rgba(74, 144, 226, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  overflow: hidden;
  position: relative;
}

.camera-header {
  background: rgba(74, 144, 226, 0.1);
  padding: 8px 12px;
  font-size: 14px;
  font-weight: bold;
  border-bottom: 1px solid rgba(74, 144, 226, 0.3);
  color: #2C3E50;
  text-shadow: 0 0 2px rgba(44, 62, 80, 0.1);
}

.camera-container {
  position: relative;
  padding: 8px;
}

.tech-camera-feed {
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid rgba(74, 144, 226, 0.3);
  box-shadow: 0 4px 15px rgba(74, 144, 226, 0.2);
  background-color: #000; /* 给video标签一个黑色背景，加载时更好看 */
}

.tech-text {
  color: #2C3E50;
  text-shadow: 0 0 2px rgba(44, 62, 80, 0.1);
}

.tech-text-secondary {
  color: #4A90E2;
  text-shadow: 0 0 5px rgba(74, 144, 226, 0.2);
}
</style>
