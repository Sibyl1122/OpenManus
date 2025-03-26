from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict

from app.agent.base import BaseAgent
from app.agent.util.render_sche import render_scheduler_template
from app.flow.base import BaseFlow
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message


class SchedulerFlow(BaseFlow, BaseModel):
    """一个使用调度器模板的任务执行流程"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm: LLM = Field(default_factory=lambda: LLM())
    executor_keys: List[str] = Field(default_factory=list)
    completed_tasks: List[Dict[str, str]] = Field(default_factory=list)

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # 设置执行器键
        if "executors" in data:
            data["executor_keys"] = data.pop("executors")

        # 调用父类的初始化
        super().__init__(agents, **data)

        # 如果没有指定执行器键，使用所有代理键
        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """获取适合当前步骤的执行器代理"""
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]

        return self.primary_agent

    async def execute(self, input_text: str) -> str:
        """执行调度器流程"""
        try:
            if not self.primary_agent:
                raise ValueError("没有可用的主代理")

            result = ""
            while True:
                # 渲染调度器模板
                scheduler_prompt = render_scheduler_template(
                    user_requirement=input_text,
                    completed_tasks=self.completed_tasks
                )
                logger.info(f"调度器模板: {scheduler_prompt}")

                # 使用LLM获取下一步任务
                response = await self.llm.ask(
                    messages=[Message.user_message(scheduler_prompt)]
                )

                # 解析响应中的任务列表
                task_list = self._parse_task_list(response)
                
                #如果task_list为空，最后一次反问模型
                scheduler_prompt = scheduler_prompt + "\n\n请深度思考,真的完成用户需求了吗？"
                if not task_list:
                    response = await self.llm.ask(
                        messages=[Message.user_message(scheduler_prompt)]
                    )
                    task_list = self._parse_task_list(response)

                # 如果没有新任务，说明任务完成
                if not task_list:
                    result += "所有任务已完成。\n"
                    break

                # 执行新任务
                task = task_list[0]  # 获取唯一的新任务
                executor = self.get_executor()
                task_result = await self._execute_task(executor, task)
                
                # 记录完成的任务
                self.completed_tasks.append({
                    "description": task,
                    "status": "completed",
                    "result": task_result
                })
                
                result += f"任务完成: {task}\n结果: {task_result}\n\n"

                # 检查代理是否想要终止
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    return result

            return result
        except Exception as e:
            logger.error(f"调度器流程执行错误: {str(e)}")
            return f"执行失败: {str(e)}"

    def _parse_task_list(self, response: str) -> List[str]:
        """从响应中解析任务列表"""
        import re
        
        # 查找所有<task>标签中的内容
        tasks = re.findall(r"<task>(.*?)</task>", response, re.DOTALL)
        # 清理每个任务的内容（去除空白字符）
        return [task.strip() for task in tasks if task.strip()]

    async def _execute_task(self, executor: BaseAgent, task: str) -> str:
        """执行单个任务"""
        try:
            # 创建任务执行提示
            task_prompt = f"""
            当前任务: {task}
            
            请执行这个任务并提供详细的结果。
            """
            
            # 使用代理执行任务
            return await executor.run(task_prompt)
        except Exception as e:
            logger.error(f"任务执行错误: {str(e)}")
            return f"任务执行失败: {str(e)}" 