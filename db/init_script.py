import json
import asyncio
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

# 1. 从你的 database 模块导入异步引擎和初始化工具
from db.database import engine, create_db_and_tables
# 2. 导入你的模型类 (请确保路径正确)
from models.Plan_Exercise_Model import BaseExercise


async def init_base_library(json_file_path: str):
    # 第一步：确保数据库表已创建
    # 它会调用 SQLModel.metadata.create_all 的异步版本
    print("正在检查并创建表结构...")
    await create_db_and_tables()

    # 第二步：读取 JSON 文件内容
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {json_file_path}")
        return

    # 第三步：开启异步会话录入数据
    async with AsyncSession(engine) as session:
        print(f"开始录入数据，共 {len(data)} 条动作...")

        for item in data:
            # 异步查询是否已存在记录
            statement = select(BaseExercise).where(BaseExercise.id == item['id'])
            # 在异步 Session 中，使用 execute 代替 exec
            result = await session.execute(statement)
            # 获取第一个结果（scalar 代表获取对象本身，而不是元组）
            existing = result.scalars().first()

            if not existing:
                # 建立新对象，注意字段映射
                new_ex = BaseExercise(
                    id=item['id'],
                    name=item['name'],
                    force=item.get('force'),
                    level=item.get('level'),
                    mechanic=item.get('mechanic'),
                    equipment=item.get('equipment'),
                    category=item.get('category'),
                    primary_muscles=item.get('primaryMuscles', []),
                    secondary_muscles=item.get('secondaryMuscles', []),
                    instructions=item.get('instructions', []),
                    images=item.get('images', [])
                )
                session.add(new_ex)

        # 异步提交事务
        await session.commit()
        print("✅ 标准动作库录入完成！")


if __name__ == "__main__":
    # 异步程序的启动入口
    asyncio.run(init_base_library("exercise.json"))