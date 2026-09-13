# DJI MSDK FastAPI 接口文档

## HTTP 接口

### 1. 页面路由

#### GET `/`
- **功能**：获取主页面
- **返回**：控制页面 HTML
- **说明**：重定向到控制页面

#### GET `/control`
- **功能**：获取无人机控制界面
- **返回**：控制页面 HTML
- **说明**：提供无人机控制的 Web 界面

#### GET `/video`
- **功能**：获取视频播放界面
- **返回**：视频页面 HTML
- **说明**：提供无人机视频流播放界面

#### GET `/get-stream-url`
- **功能**：获取 HLS 视频流地址
- **返回**：JSON
  ```json
  {
    "hls_url": "http://{MEDIAMTX_HOST}:{MEDIAMTX_HLS_PORT}/{STREAM_PATH_NAME}/index.m3u8"
  }
  ```
- **说明**：返回无人机视频流的 HLS 地址

### 2. API 接口

#### GET `/api/clients`
- **功能**：获取所有连接的客户端信息
- **返回**：JSON
  ```json
  {
    "clients": [
      {
        "client_id": "string",
        "ip": "string"
      }
    ]
  }
  ```
- **说明**：列出所有当前连接的无人机客户端及其 IP 地址

#### GET `/api/telemetry/{client_id}`
- **功能**：获取指定客户端的遥测数据
- **参数**：
  - `client_id`：客户端 ID（路径参数）
- **返回**：JSON
  ```json
  {
    "client_id": "string",
    "telemetry": {
      // 遥测数据字段
    }
  }
  ```
- **错误返回**：
  ```json
  {
    "status": "error",
    "message": "Telemetry data not found for client '{client_id}'."
  }
  ```

#### POST `/api/send-command`
- **功能**：向指定客户端发送指令
- **请求体**：
  ```json
  {
    "client_id": "string",
    "command": "string"
  }
  ```
- **返回**：
  - 成功：
    ```json
    {
      "status": "success",
      "message": "Command '{command}' sent to {client_id}."
    }
    ```
  - 失败：
    ```json
    {
      "status": "error",
      "message": "Client '{client_id}' not found or communication failed."
    }
    ```

## WebSocket 接口

### 1. 无人机客户端连接
#### WS `/ws/{client_id}`
- **功能**：无人机客户端连接端点，用于接收遥测数据
- **参数**：
  - `client_id`：客户端标识（路径参数）
- **通信内容**：
  - 接收：遥测数据（JSON 格式）
  - 发送：控制命令（文本格式）
- **说明**：用于无人机客户端连接并传输遥测数据

### 2. 控制面板连接
#### WS `/ws/control`
- **功能**：控制面板前端连接端点
- **通信内容**：
  - 接收：来自后端的遥测数据和状态更新
  - 发送：控制命令和其他消息
- **说明**：用于 Web 控制面板与后端的实时通信

## 数据模型

### Command
```json
{
  "client_id": "string",  // 目标客户端的 ID
  "command": "string"     // 要发送的命令
}
```

### TelemetryData
遥测数据的具体字段需要根据实际的 `data_type.py` 文件中的 `TelemetryData` 类定义来确定。

## 注意事项
1. 所有 WebSocket 连接都支持自动重连机制
2. 遥测数据会实时推送给所有已连接的控制面板
3. 视频流使用 HLS 协议，确保低延迟和高兼容性 