from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from app.agent.base import BaseAgent


class FlowType(str, Enum):
    """流程类型枚举"""
    SCHEDULER = "scheduler"


class BaseFlow(ABC, BaseModel):
    """流程基类"""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    agents: Dict[str, BaseAgent] = Field(default_factory=dict)
    primary_agent: Optional[BaseAgent] = None

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # 标准化代理
        normalized_agents = self._normalize_agents(agents)
        
        # 调用父类的初始化
        super().__init__(agents=normalized_agents, **data)
        
        # 设置主代理
        self.primary_agent = self._get_primary_agent()

    def _normalize_agents(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]]
    ) -> Dict[str, BaseAgent]:
        """将代理标准化为字典格式"""
        if isinstance(agents, BaseAgent):
            return {agents.name: agents}
        elif isinstance(agents, list):
            return {agent.name: agent for agent in agents}
        elif isinstance(agents, dict):
            return agents
        else:
            raise ValueError("不支持的代理类型")

    def _get_primary_agent(self) -> Optional[BaseAgent]:
        """获取主代理"""
        if not self.agents:
            return None
        return next(iter(self.agents.values()))

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """执行流程"""
        pass


class PlanStepStatus(str, Enum):
    """Enum class defining possible statuses of a plan step"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

    @classmethod
    def get_all_statuses(cls) -> list[str]:
        """Return a list of all possible step status values"""
        return [status.value for status in cls]

    @classmethod
    def get_active_statuses(cls) -> list[str]:
        """Return a list of values representing active statuses (not started or in progress)"""
        return [cls.NOT_STARTED.value, cls.IN_PROGRESS.value]

    @classmethod
    def get_status_marks(cls) -> Dict[str, str]:
        """Return a mapping of statuses to their marker symbols"""
        return {
            cls.COMPLETED.value: "[✓]",
            cls.IN_PROGRESS.value: "[→]",
            cls.BLOCKED.value: "[!]",
            cls.NOT_STARTED.value: "[ ]",
        }
