import os
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")


engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

# 兼容旧版本 SQLAlchemy
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # AI API 配置字段
    ai_api_provider = Column(String(64), nullable=True)  # OpenAI, 通义千问, etc.
    ai_api_key = Column(String(256), nullable=True)  # 加密存储的 API Key
    ai_api_endpoint = Column(String(512), nullable=True)  # 自定义端点


class AiTaskConversation(Base):
    __tablename__ = "ai_task_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    task_plan = Column(Text, nullable=True)  # JSON string
    mission_id = Column(Integer, nullable=True, index=True)  # 关联的任务 ID
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    start_point_lat = Column(String(32), nullable=False)
    start_point_lng = Column(String(32), nullable=False)
    start_point_name = Column(String(256), nullable=True)
    end_point_lat = Column(String(32), nullable=False)
    end_point_lng = Column(String(32), nullable=False)
    end_point_name = Column(String(256), nullable=True)
    num_uavs = Column(Integer, nullable=False, default=1)
    mission_type = Column(String(64), nullable=False, default='patrol')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MissionNoFlyZone(Base):
    __tablename__ = "mission_nofly_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(Integer, nullable=False, index=True)
    center_lat = Column(String(32), nullable=False)
    center_lng = Column(String(32), nullable=False)
    radius = Column(Integer, nullable=False)  # meters
    name = Column(String(256), nullable=True)


class MissionWaypoint(Base):
    __tablename__ = "mission_waypoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(Integer, nullable=False, index=True)
    lat = Column(String(32), nullable=False)
    lng = Column(String(32), nullable=False)
    name = Column(String(256), nullable=True)
    sequence = Column(Integer, nullable=False)


class MissionRoute(Base):
    __tablename__ = "mission_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(Integer, nullable=False, index=True)
    uav_index = Column(Integer, nullable=False)
    waypoints = Column(Text, nullable=False)  # JSON array of waypoints
    distance = Column(Integer, nullable=True)  # meters
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

