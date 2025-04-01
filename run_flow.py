import asyncio
import time
import os

from app.agent.manus import Manus
from app.flow.flow_factory import FlowFactory, FlowType
from app.logger import logger
from app.tool.job_tool import JobTool


async def run_flow():
    agents = {
        "manus": Manus(),
    }

    try:
        prompt = input("Enter your prompt: ")

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        # 确保数据目录存在（保留这一步，因为可能还需要保存其他数据）
        os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

        # 初始化一个job
        job_tool = JobTool()
        job_id_result = await job_tool.create_job(prompt)
        job_id = job_id_result["job_id"]

        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning("Processing your request...")

        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                flow.execute(prompt, job_id),
                timeout=3600,  # 60 minute timeout for the entire execution
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_flow())
