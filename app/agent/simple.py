from typing import Optional
import json

from pydantic import Field

from app.agent.base import BaseAgent
from app.logger import logger
from app.schema import AgentState, Message, ToolCall
from app.tool import ToolCollection


class SimpleAgent(BaseAgent):
    """一个简化的Agent，只执行一次大模型调用和一次工具调用"""

    name: str = "simple"
    description: str = "一个简化的Agent，只执行一次大模型调用和一次工具调用"
    
    # 可用工具配置
    available_tools: ToolCollection = Field(default_factory=ToolCollection)
    
    # 工具调用结果
    tool_call: Optional[ToolCall] = None
    tool_result: Optional[str] = None

    async def step(self, request: Optional[str] = None) -> str:
        """执行单次步骤：调用大模型并执行工具"""
        # 1. 调用大模型获取工具调用
        response = await self.llm.ask_tool(
            messages=[Message.user_message(request)],
            system_msgs=[Message.system_message(self.system_prompt)]
            if self.system_prompt
            else None,
            tools=self.available_tools.to_params(),
            tool_choice="auto",
        )
        
        # 记录大模型响应
        logger.info(f"✨ {self.name}的思考: {response.content}")
        
        # 2. 获取工具调用
        if not response.tool_calls:
            return "错误：未获取到工具调用"
            
        self.tool_call = response.tool_calls[0]
        logger.info(f"🛠️ 准备使用工具: {self.tool_call.function.name}")
        
        # 3. 执行工具调用
        self.tool_result = await self.execute_tool(self.tool_call)
        logger.info(f"🎯 工具执行完成，结果: {self.tool_result}")
        
        # 4. 更新状态为完成
        self.state = AgentState.FINISHED
        
        return self.tool_result

    async def execute_tool(self, command: ToolCall) -> str:
        """执行单个工具调用"""
        if not command or not command.function or not command.function.name:
            return "错误：无效的命令格式"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"错误：未知的工具 '{name}'"

        try:
            # 解析参数
            args = json.loads(command.function.arguments or "{}")
            
            # 执行工具
            logger.info(f"🔧 激活工具: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)
            
            # 格式化结果
            observation = (
                f"工具 '{name}' 执行结果:\n{str(result)}"
                if result
                else f"工具 '{name}' 执行完成，无输出"
            )
            
            return observation
            
        except Exception as e:
            error_msg = f"⚠️ 工具 '{name}' 执行出错: {str(e)}"
            logger.error(error_msg)
            return f"错误: {error_msg}" 