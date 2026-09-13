#!/usr/bin/env python3
"""
数据库迁移脚本：添加航迹规划相关表
"""
import asyncio
import os
from sqlalchemy import text
from db import engine

async def migrate():
    """添加航迹规划相关表"""
    async with engine.begin() as conn:
        # 检查 missions 表是否已存在
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='missions'
        """))
        
        if result.fetchone() is None:
            print("创建航迹规划相关表...")
            
            # 创建 missions 表
            await conn.execute(text("""
                CREATE TABLE missions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(256) NOT NULL,
                    start_point_lat VARCHAR(32) NOT NULL,
                    start_point_lng VARCHAR(32) NOT NULL,
                    start_point_name VARCHAR(256),
                    end_point_lat VARCHAR(32) NOT NULL,
                    end_point_lng VARCHAR(32) NOT NULL,
                    end_point_name VARCHAR(256),
                    num_uavs INTEGER NOT NULL DEFAULT 1,
                    mission_type VARCHAR(64) NOT NULL DEFAULT 'patrol',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))
            await conn.execute(text("CREATE INDEX idx_missions_user_id ON missions(user_id)"))
            print("✓ missions 表创建成功")
            
            # 创建 mission_nofly_zones 表
            await conn.execute(text("""
                CREATE TABLE mission_nofly_zones (
                    id SERIAL PRIMARY KEY,
                    mission_id INTEGER NOT NULL,
                    center_lat VARCHAR(32) NOT NULL,
                    center_lng VARCHAR(32) NOT NULL,
                    radius INTEGER NOT NULL,
                    name VARCHAR(256)
                )
            """))
            await conn.execute(text("CREATE INDEX idx_mission_nofly_zones_mission_id ON mission_nofly_zones(mission_id)"))
            print("✓ mission_nofly_zones 表创建成功")
            
            # 创建 mission_waypoints 表
            await conn.execute(text("""
                CREATE TABLE mission_waypoints (
                    id SERIAL PRIMARY KEY,
                    mission_id INTEGER NOT NULL,
                    lat VARCHAR(32) NOT NULL,
                    lng VARCHAR(32) NOT NULL,
                    name VARCHAR(256),
                    sequence INTEGER NOT NULL
                )
            """))
            await conn.execute(text("CREATE INDEX idx_mission_waypoints_mission_id ON mission_waypoints(mission_id)"))
            print("✓ mission_waypoints 表创建成功")
            
            # 创建 mission_routes 表
            await conn.execute(text("""
                CREATE TABLE mission_routes (
                    id SERIAL PRIMARY KEY,
                    mission_id INTEGER NOT NULL,
                    uav_index INTEGER NOT NULL,
                    waypoints TEXT NOT NULL,
                    distance INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))
            await conn.execute(text("CREATE INDEX idx_mission_routes_mission_id ON mission_routes(mission_id)"))
            print("✓ mission_routes 表创建成功")
            
            print("✓ 所有航迹规划表创建成功")
        else:
            print("✓ 航迹规划表已存在，跳过迁移")

if __name__ == "__main__":
    # 设置数据库 URL（如果环境变量中没有）
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://drone_admin:drone123@localhost:5432/drone"
    
    asyncio.run(migrate())
    print("\n迁移完成！")

