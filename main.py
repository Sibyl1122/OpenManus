import asyncio

from app.agent.custom import CustomAgent
from app.flow.flow_factory import FlowFactory
from app.flow.base import FlowType
from app.logger import logger


async def main():
    # 创建Manus代理
    agent = CustomAgent(
        name="custom",
        description="一个能够使用多种工具解决各种任务的代理"
    )
    
    # 创建调度器流
    flow = FlowFactory.create_flow(
        flow_type=FlowType.SCHEDULER,
        agents=agent
    )
    
    while True:
        try:
            prompt = input("请输入你的需求 (输入'exit'或'quit'退出): ")
            prompt_lower = prompt.lower()
            if prompt_lower in ["exit", "quit"]:
                logger.info("再见！")
                break
            if not prompt.strip():
                logger.warning("跳过空输入。")
                continue
                
            logger.warning("正在处理你的需求...")
            # 使用调度器流执行任务
            result = await flow.execute(prompt)
            print("\n执行结果:")
            print(result)
            print("\n" + "="*50 + "\n")
            
        except KeyboardInterrupt:
            logger.warning("再见！")
            break
        except Exception as e:
            logger.error(f"执行出错: {str(e)}")
            print(f"\n错误: {str(e)}\n")


if __name__ == "__main__":
    asyncio.run(main())
