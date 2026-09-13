# app/main.py
"""
应用主入口。
负责创建 FastAPI 应用、配置中间件、包含各个模块的路由，并管理后台UDP服务器。
"""
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware  
# 从相应模块导入路由和管理器实例
import api
import auth_router
import websocket_router
from manager import manager  # 导入共享的 manager 实例
from auth import ensure_admin_from_env
from db import SessionLocal, init_db

# --- 后台任务管理 ---
background_tasks = set()


class UDPServerProtocol(asyncio.DatagramProtocol):
    """
    处理UDP数据报的异步协议类。
    """

    def connection_made(self, transport):
        self.transport = transport
        print("UDP 服务器已启动并监听...")

    def datagram_received(self, data, addr):
        """
        当收到UDP数据报时，此方法被调用。
        """
        # <--- 修改: 不再传递 transport 对象，因为 manager 已经保存了它
        task = asyncio.create_task(manager.handle_udp_datagram(data, addr))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    def error_received(self, exc):
        print(f"UDP 服务器接收时发生错误: {exc}")

    def connection_lost(self, exc):
        print("UDP 服务器已关闭。")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器 (替代 on_event)
    """
    # Startup
    print("应用启动...")

    await init_db()
    async with SessionLocal() as db:
        await ensure_admin_from_env(db)

    loop = asyncio.get_running_loop()
    listen_port = 8081

    # 1. 启动 UDP 服务器，并捕获 transport 对象
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPServerProtocol(),
        local_addr=('0.0.0.0', listen_port)
    )

    # <--- 关键修复: 将 transport 对象保存到 manager 中
    manager.set_transport(transport)

    print(f"UDP 服务器正在监听端口 {listen_port}...")

    # 2. 启动 ConnectionManager 的后台任务
    task = asyncio.create_task(manager.run_background_tasks())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    yield  # 应用运行期间

    # Shutdown
    print("应用关闭...")
    for task in list(background_tasks):  # 使用 list 副本进行迭代
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    print("所有后台任务已清理。")


# --- 应用初始化 ---
app = FastAPI(
    title="Drone Control Center API",
    description="一个用于无人机遥测和远程控制的后端服务。",
    version="1.1.2-Lifespan",  # 更新版本号以反映变化
    lifespan=lifespan
)

# ========== 一键 CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 生产可写 ["http://101.132.172.117"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= 临时：打印所有非 WS 请求 =========
@app.middleware("http")
async def log_raw(request: Request, call_next):
    if request.url.path != "/ws/control":          # 不打印 WS 流量
        body = await request.body()
        print(f"[RAW-HTTP] {request.method} {request.url}  body={body[:100]}")
    return await call_next(request)
# ============================================

# --- 挂载静态资源和模板 (保持不变) ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- 包含路由 (保持不变) ---
app.include_router(websocket_router.router)
app.include_router(auth_router.router)
app.include_router(api.router)


# --- 页面路由 (保持不变) ---
@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def get_root(request: Request):
    return templates.TemplateResponse("single.html", {"request": request})


@app.get("/single", response_class=HTMLResponse, tags=["Pages"])
async def get_single(request: Request):
    return templates.TemplateResponse("single.html", {"request": request})


@app.get("/cluster", response_class=HTMLResponse, tags=["Pages"])
async def get_cluster(request: Request):
    return templates.TemplateResponse("cluster_control.html", {"request": request})


# --- 运行服务 ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True)

