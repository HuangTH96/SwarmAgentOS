// main.js (修改后，支持下拉框自动切换)

document.addEventListener('DOMContentLoaded', () => {
    // --- 1. 获取 DOM 元素 ---
    const clientSelector = document.getElementById('client-selector');
    const videoPlayer = document.getElementById('videoPlayer');
    const statusText = document.getElementById('status-text');
    const startPlayBtn = document.getElementById('startPlayBtn');
    const stopPlayBtn = document.getElementById('stopPlayBtn');
    const toggleVideoBtn = document.getElementById('toggleVideoBtn');
    // REMOVED: const clientIdInput = clientSelector.value; // 这一行是错误的，因为它只在加载时运行一次

    let peerConnection = null; // 用于存储 WebRTC 连接实例

    // --- 2. 辅助函数 ---
    const updateStatus = (message, type = '') => {
        if (statusText) {
            statusText.textContent = message;
            statusText.className = ''; // 重置 class
            if (type) statusText.classList.add(type);
        }
    };

    // --- 3. WebRTC 播放核心函数 (基本保持不变) ---
    const startWebRTCPlayback = async (clientId) => {
        if (!clientId) {
            updateStatus('错误: 请先从下拉框中选择一个客户端ID。', 'error');
            return;
        }

        updateStatus(`正在为 ${clientId} 建立 WebRTC 连接...`, 'loading');

        if (peerConnection) {
            peerConnection.close();
        }

        peerConnection = new RTCPeerConnection();

        peerConnection.ontrack = (event) => {
            console.log('接收到远程媒体流', event.streams[0]);
            videoPlayer.srcObject = event.streams[0];
            updateStatus(`正在播放 ${clientId} 的视频...`, 'success');
        };

        try {
            peerConnection.addTransceiver('video', { 'direction': 'recvonly' });

            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);

            const response = await fetch(`/api/webrtc-stream/${clientId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/sdp'
                },
                body: peerConnection.localDescription.sdp
            });

            if (!response.ok) {
                const errorText = await response.text();
                let detail = errorText;
                try {
                    detail = JSON.parse(errorText).detail;
                } catch(e) {}
                throw new Error(`信令服务器错误: ${response.status} - ${detail}`);
            }

            const answerSdp = await response.text();
            if (!answerSdp) {
                 throw new Error('从服务器获取的 SDP Answer 为空');
            }

            await peerConnection.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));

        } catch (error) {
            console.error('WebRTC 播放失败:', error);
            updateStatus(`播放失败: ${error.message}`, 'error');
            stopPlayback();
        }
    };

    const stopPlayback = () => {
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }
        videoPlayer.srcObject = null; // 清理 video 元素的流
        videoPlayer.src = ''; // 兼容旧浏览器
        updateStatus('播放已停止。请从下拉框选择一个无人机。', 'success');
    };

    // --- 4. 事件监听 ---

    // NEW: 添加下拉选框的 'change' 事件监听器，这是实现自动切换的核心
    clientSelector.addEventListener('change', () => {
        const selectedClientId = clientSelector.value;
        console.log(`下拉框切换，选择的客户端是: ${selectedClientId}`);

        if (selectedClientId) { // 如果选择了一个有效的客户端
            // 确保视频播放器是可见的
            if (videoPlayer.classList.contains('hidden')) {
                videoPlayer.classList.remove('hidden');
                toggleVideoBtn.textContent = '隐藏';
            }
            // 开始播放新选择的客户端视频
            startWebRTCPlayback(selectedClientId);
        } else { // 如果选择了一个空选项 (例如 "请选择...")
            // 停止播放
            stopPlayback();
        }
    });

    // MODIFIED: "播放"按钮现在的作用是播放/重连当前选中的客户端
    startPlayBtn.addEventListener('click', () => {
        console.log("手动点击播放/重连按钮");
        if (videoPlayer.classList.contains('hidden')) {
            videoPlayer.classList.remove('hidden');
            toggleVideoBtn.textContent = '隐藏';
        }
        // 获取当前下拉框选中的值并播放
        const currentSelectedClient = clientSelector.value;
        startWebRTCPlayback(currentSelectedClient);
    });

    stopPlayBtn.addEventListener('click', stopPlayback);

    toggleVideoBtn.addEventListener('click', () => {
        const isHidden = videoPlayer.classList.toggle('hidden');
        toggleVideoBtn.textContent = isHidden ? '显示' : '隐藏';
        if (isHidden) {
            stopPlayback(); // 隐藏时也停止播放
        }
    });

    // 页面卸载时清理资源
    window.addEventListener('beforeunload', stopPlayback);
});