import asyncio
import os
from sqlalchemy import text
from db import engine

async def migrate():
    """添加 AI API 配置字段到 users 表"""
    async with engine.begin() as conn:
        # 检查字段是否已存在
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='ai_api_provider'
        """))
        
        if result.fetchone() is None:
            print("添加 AI API 配置字段...")
            
            # 添加 ai_api_provider 字段
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN ai_api_provider VARCHAR(64)
            """))
            
            # 添加 ai_api_key 字段
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN ai_api_key VARCHAR(256)
            """))
            
            # 添加 ai_api_endpoint 字段
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN ai_api_endpoint VARCHAR(512)
            """))
            
            print("✓ AI API 配置字段添加成功")
        else:
            print("✓ AI API 配置字段已存在，跳过迁移")

if __name__ == "__main__":
    # 设置数据库 URL（如果环境变量中没有）
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://drone_admin:drone123@localhost:5432/drone"
    
    asyncio.run(migrate())
    print("\n迁移完成！")
