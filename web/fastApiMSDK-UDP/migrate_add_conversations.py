#!/usr/bin/env python3
"""
数据库迁移脚本：为 ai_task_conversations 表添加 mission_id 字段

运行方式：
  python migrate_add_mission_to_conversations.py
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def migrate():
    """执行数据库迁移"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误: 未设置 DATABASE_URL 环境变量")
        sys.exit(1)

    print(f"连接到数据库: {database_url.split('@')[1] if '@' in database_url else database_url}")
    
    engine = create_async_engine(database_url, pool_pre_ping=True)

    try:
        async with engine.begin() as conn:
            # 检查列是否已存在
            print("检查 mission_id 列是否已存在...")
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='ai_task_conversations' 
                AND column_name='mission_id'
            """))
            
            if result.fetchone():
                print("✓ mission_id 列已存在，跳过迁移")
                return

            # 添加 mission_id 列
            print("添加 mission_id 列...")
            await conn.execute(text("""
                ALTER TABLE ai_task_conversations 
                ADD COLUMN mission_id INTEGER
            """))
            print("✓ mission_id 列添加成功")

            # 创建索引
            print("创建索引...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversations_mission_id 
                ON ai_task_conversations(mission_id)
            """))
            print("✓ 索引创建成功")

            # 添加外键约束（可选，如果需要严格的引用完整性）
            print("添加外键约束...")
            try:
                await conn.execute(text("""
                    ALTER TABLE ai_task_conversations 
                    ADD CONSTRAINT fk_conversations_mission 
                    FOREIGN KEY (mission_id) 
                    REFERENCES missions(id) 
                    ON DELETE CASCADE
                """))
                print("✓ 外键约束添加成功")
            except Exception as e:
                print(f"⚠ 外键约束添加失败（可能已存在）: {e}")

        print("\n✅ 数据库迁移完成！")

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("AI 任务对话记录迁移脚本")
    print("为 ai_task_conversations 表添加 mission_id 字段")
    print("=" * 60)
    print()
    
    asyncio.run(migrate())

