"""
计划代理（PlanningAgent）模块

这个模块实现了一个能够创建和管理任务计划的智能代理。
它使用计划工具来创建和管理结构化的计划，并通过各个步骤跟踪进度直到任务完成。
"""

import time
from typing import Dict, List, Literal, Optional

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt.planning import NEXT_STEP_PROMPT, PLANNING_SYSTEM_PROMPT
from app.schema import Message, ToolCall
from app.tool import PlanningTool, Terminate, ToolCollection


class PlanningAgent(ToolCallAgent):
    """
    计划代理类，用于创建和管理任务计划

    这个代理使用计划工具来创建和管理结构化的计划，
    并通过各个步骤跟踪进度直到任务完成。
    """

    name: str = "planning"
    description: str = "一个能够创建和管理任务计划的代理"

    system_prompt: str = PLANNING_SYSTEM_PROMPT  # 系统提示词
    next_step_prompt: str = NEXT_STEP_PROMPT     # 下一步提示词

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(PlanningTool(), Terminate())
    )
    tool_choices: Literal["none", "auto", "required"] = "auto"
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    active_plan_id: Optional[str] = Field(default=None)

    # 用于跟踪每个工具调用的步骤状态的字典
    step_execution_tracker: Dict[str, Dict] = Field(default_factory=dict)
    current_step_index: Optional[int] = None

    max_steps: int = 20  # 最大步骤数限制

    @model_validator(mode="after")
    def initialize_plan_and_verify_tools(self) -> "PlanningAgent":
        """初始化代理，设置默认计划ID并验证必需的工具"""
        self.active_plan_id = f"plan_{int(time.time())}"

        if "planning" not in self.available_tools.tool_map:
            self.available_tools.add_tool(PlanningTool())

        return self

    async def think(self) -> bool:
        """根据计划状态决定下一步行动"""
        prompt = (
            f"CURRENT PLAN STATUS:\n{await self.get_plan()}\n\n{self.next_step_prompt}"
            if self.active_plan_id
            else self.next_step_prompt
        )
        self.messages.append(Message.user_message(prompt))

        # 在思考前获取当前步骤索引
        self.current_step_index = await self._get_current_step_index()

        result = await super().think()

        # 思考后，如果决定执行工具且不是计划工具或特殊工具，
        # 将其与当前步骤关联以进行跟踪
        if result and self.tool_calls:
            latest_tool_call = self.tool_calls[0]  # 获取最新的工具调用
            if (
                latest_tool_call.function.name != "planning"
                and latest_tool_call.function.name not in self.special_tool_names
                and self.current_step_index is not None
            ):
                self.step_execution_tracker[latest_tool_call.id] = {
                    "step_index": self.current_step_index,
                    "tool_name": latest_tool_call.function.name,
                    "status": "pending",  # 将在执行后更新
                }

        return result

    async def act(self) -> str:
        """执行步骤并跟踪其完成状态"""
        result = await super().act()

        # 执行工具后，更新计划状态
        if self.tool_calls:
            latest_tool_call = self.tool_calls[0]

            # 更新执行状态为已完成
            if latest_tool_call.id in self.step_execution_tracker:
                self.step_execution_tracker[latest_tool_call.id]["status"] = "completed"
                self.step_execution_tracker[latest_tool_call.id]["result"] = result

                # 如果这是非计划、非特殊工具，更新计划状态
                if (
                    latest_tool_call.function.name != "planning"
                    and latest_tool_call.function.name not in self.special_tool_names
                ):
                    await self.update_plan_status(latest_tool_call.id)

        return result

    async def get_plan(self) -> str:
        """获取当前计划状态"""
        if not self.active_plan_id:
            return "没有活动计划。请先创建一个计划。"

        result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id},
        )
        return result.output if hasattr(result, "output") else str(result)

    async def run(self, request: Optional[str] = None) -> str:
        """运行代理，可选择性地提供初始请求"""
        if request:
            await self.create_initial_plan(request)
        return await super().run()

    async def update_plan_status(self, tool_call_id: str) -> None:
        """
        根据已完成的工具执行更新当前计划进度
        仅当关联的工具成功执行后才将步骤标记为已完成
        """
        if not self.active_plan_id:
            return

        if tool_call_id not in self.step_execution_tracker:
            logger.warning(f"未找到工具调用 {tool_call_id} 的步骤跟踪")
            return

        tracker = self.step_execution_tracker[tool_call_id]
        if tracker["status"] != "completed":
            logger.warning(f"工具调用 {tool_call_id} 尚未成功完成")
            return

        step_index = tracker["step_index"]

        try:
            # 将步骤标记为已完成
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "mark_step",
                    "plan_id": self.active_plan_id,
                    "step_index": step_index,
                    "step_status": "completed",
                },
            )
            logger.info(
                f"在计划 {self.active_plan_id} 中将步骤 {step_index} 标记为已完成"
            )
        except Exception as e:
            logger.warning(f"更新计划状态失败: {e}")

    async def _get_current_step_index(self) -> Optional[int]:
        """
        解析当前计划以识别第一个未完成步骤的索引
        如果未找到活动步骤，则返回 None
        """
        if not self.active_plan_id:
            return None

        plan = await self.get_plan()

        try:
            plan_lines = plan.splitlines()
            steps_index = -1

            # 查找 "Steps:" 行的索引
            for i, line in enumerate(plan_lines):
                if line.strip() == "Steps:":
                    steps_index = i
                    break

            if steps_index == -1:
                return None

            # 查找第一个未完成的步骤
            for i, line in enumerate(plan_lines[steps_index + 1 :], start=0):
                if "[ ]" in line or "[→]" in line:  # 未开始或进行中
                    # 将当前步骤标记为进行中
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": i,
                            "step_status": "in_progress",
                        },
                    )
                    return i

            return None  # 未找到活动步骤
        except Exception as e:
            logger.warning(f"查找当前步骤索引时出错: {e}")
            return None

    async def create_initial_plan(self, request: str) -> None:
        """根据请求创建初始计划"""
        logger.info(f"创建初始计划，ID: {self.active_plan_id}")

        messages = [
            Message.user_message(
                f"分析请求并创建ID为 {self.active_plan_id} 的计划: {request}"
            )
        ]
        self.memory.add_messages(messages)
        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice="required",
        )
        assistant_msg = Message.from_tool_calls(
            content=response.content, tool_calls=response.tool_calls
        )

        self.memory.add_message(assistant_msg)

        plan_created = False
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                result = await self.execute_tool(tool_call)
                logger.info(
                    f"执行工具 {tool_call.function.name}，结果: {result}"
                )

                # 将工具响应添加到内存中
                tool_msg = Message.tool_message(
                    content=result,
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                )
                self.memory.add_message(tool_msg)
                plan_created = True
                break

        if not plan_created:
            logger.warning("初始请求未创建计划")
            tool_msg = Message.assistant_message(
                "错误: 命令 create 需要参数 `plan_id`"
            )
            self.memory.add_message(tool_msg)


async def main():
    # 配置并运行代理
    agent = PlanningAgent(available_tools=ToolCollection(PlanningTool(), Terminate()))
    result = await agent.run("Help me plan a trip to the moon")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
