"""
作业引擎工具注册器
用于将作业引擎功能注册为工具，供 OpenManus MCP 服务器使用
"""

import logging
from typing import Dict, Any, Optional, List

from app.db.job_engine import job_engine
from app.db.job_runner import job_runner
from app.tool.job_tool import JobTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册器，用于管理作业引擎工具"""

    def __init__(self):
        """初始化工具注册器"""
        self._tools = {}
        self._initialized = False

    def init_tools(self) -> None:
        """初始化所有工具"""
        if self._initialized:
            return

        # 创建作业工具
        self._tools["job"] = JobTool()

        self._initialized = True
        logger.info("作业引擎工具已初始化")

    def get_tool(self, name: str) -> Optional[Any]:
        """获取指定工具"""
        if not self._initialized:
            self.init_tools()

        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有可用工具"""
        if not self._initialized:
            self.init_tools()

        return list(self._tools.keys())

    def register_with_server(self, server) -> None:
        """将工具注册到 MCP 服务器"""
        if not self._initialized:
            self.init_tools()

        for name, tool in self._tools.items():
            if name not in server.tools:
                server.tools[name] = tool
                logger.info(f"注册工具 {name} 到 MCP 服务器")
            else:
                logger.warning(f"工具 {name} 已存在于 MCP 服务器中")


# 全局工具注册器实例
tool_registry = ToolRegistry()
