from typing import Dict, List, Union

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, FlowType
from app.flow.scheduler import SchedulerFlow


class FlowFactory:
    """创建不同类型流程的工厂类"""

    @staticmethod
    def create_flow(
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs,
    ) -> BaseFlow:
        flows = {
            FlowType.SCHEDULER: SchedulerFlow,
        }

        flow_class = flows.get(flow_type)
        if not flow_class:
            raise ValueError(f"未知的流程类型: {flow_type}")

        return flow_class(agents, **kwargs)
