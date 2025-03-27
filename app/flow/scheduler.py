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
    pending_tasks: List[Dict[str, str]] = Field(default_factory=list)
    input_text: str = Field(default="")

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
        """执行调度器流程，支持多任务并行和任务修改"""
        try:
            if not self.primary_agent:
                raise ValueError("没有可用的主代理")

            # 存储输入文本作为实例属性
            self.input_text = input_text
            
            result = ""
            while True:
                # 渲染调度器模板
                scheduler_prompt = render_scheduler_template(
                    user_requirement=input_text,
                    completed_tasks=self.completed_tasks,
                    pending_tasks=self.pending_tasks,
                    template_name="scheduler.jinja"
                )
                logger.info(f"调度器模板: {scheduler_prompt}")

                # 使用LLM获取任务列表
                response = await self.llm.ask(
                    messages=[Message.user_message(scheduler_prompt)]
                )

                # 解析响应中的任务操作
                task_operations = self._parse_task_operations(response)
                
                # 如果没有任务操作，再次询问模型
                if not task_operations:
                    scheduler_prompt = scheduler_prompt + "\n\n请深度思考,真的完成用户需求了吗？是否需要新增、修改或删除任务？请输出具体的任务操作。"
                    response = await self.llm.ask(
                        messages=[Message.user_message(scheduler_prompt)]
                    )
                    task_operations = self._parse_task_operations(response)

                # 处理任务操作：添加、修改或删除任务
                self._process_task_operations(task_operations)
                
                # 如果没有待处理任务，并且没有新任务被添加，说明任务全部完成
                if not self.pending_tasks:
                    result += "所有任务已完成。\n"
                    break

                # 执行待处理任务
                tasks_to_execute = self.pending_tasks.copy()
                execution_results = []
                
                for task in tasks_to_execute:
                    executor = self.get_executor(task.get("executor_type"))
                    next_step_prompt = render_scheduler_template(
                        user_requirement=input_text,
                        completed_tasks=self.completed_tasks,
                        template_name="next_step_prompt_en.jinja",
                        additional_data={"task": task["description"]}
                    )
                    task_result = await self._execute_task(executor, next_step_prompt)
                    
                    # 从待处理任务中移除
                    if task in self.pending_tasks:
                        self.pending_tasks.remove(task)
                    
                    # 记录完成的任务
                    completed_task = {
                        "description": task["description"],
                        "status": "completed",
                        "result": task_result,
                        "priority": task.get("priority", "normal")
                    }
                    self.completed_tasks.append(completed_task)
                    
                    execution_results.append(f"任务完成: {task['description']}\n结果: {task_result}")
                    
                    # 检查代理是否想要终止
                    if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                        return "\n\n".join(execution_results)

                # 添加执行结果到总结果
                result += "\n\n".join(execution_results) + "\n\n"

            return result
        except Exception as e:
            logger.error(f"调度器流程执行错误: {str(e)}")
            return f"执行失败: {str(e)}"

    def _parse_task_operations(self, response: str) -> List[Dict]:
        """从响应中解析任务操作（添加、修改、删除）"""
        import re
        
        operations = []
        
        # 解析添加任务操作
        add_tasks = re.findall(r"<add_task>(.*?)</add_task>", response, re.DOTALL)
        for task_content in add_tasks:
            # 提取任务描述
            description_match = re.search(r"<description>(.*?)</description>", task_content, re.DOTALL)
            if description_match:
                description = description_match.group(1).strip()
                
                # 提取优先级（如果有）
                priority_match = re.search(r"<priority>(.*?)</priority>", task_content, re.DOTALL)
                priority = priority_match.group(1).strip() if priority_match else "normal"
                
                # 提取执行器类型（如果有）
                executor_match = re.search(r"<executor>(.*?)</executor>", task_content, re.DOTALL)
                executor_type = executor_match.group(1).strip() if executor_match else None
                
                operations.append({
                    "operation": "add",
                    "description": description,
                    "priority": priority,
                    "executor_type": executor_type
                })
        
        # 解析修改任务操作
        modify_tasks = re.findall(r"<modify_task>(.*?)</modify_task>", response, re.DOTALL)
        for task_content in modify_tasks:
            # 提取任务ID
            id_match = re.search(r"<id>(.*?)</id>", task_content, re.DOTALL)
            # 提取新描述
            description_match = re.search(r"<description>(.*?)</description>", task_content, re.DOTALL)
            
            if id_match and description_match:
                task_id = id_match.group(1).strip()
                new_description = description_match.group(1).strip()
                
                # 提取新优先级（如果有）
                priority_match = re.search(r"<priority>(.*?)</priority>", task_content, re.DOTALL)
                new_priority = priority_match.group(1).strip() if priority_match else None
                
                # 提取新执行器类型（如果有）
                executor_match = re.search(r"<executor>(.*?)</executor>", task_content, re.DOTALL)
                new_executor_type = executor_match.group(1).strip() if executor_match else None
                
                operations.append({
                    "operation": "modify",
                    "id": task_id,
                    "description": new_description,
                    "priority": new_priority,
                    "executor_type": new_executor_type
                })
        
        # 解析删除任务操作
        delete_tasks = re.findall(r"<delete_task>(.*?)</delete_task>", response, re.DOTALL)
        for task_content in delete_tasks:
            id_match = re.search(r"<id>(.*?)</id>", task_content, re.DOTALL)
            if id_match:
                task_id = id_match.group(1).strip()
                operations.append({
                    "operation": "delete",
                    "id": task_id
                })
        
        # 解析旧格式任务（向后兼容）
        if not operations:
            tasks = re.findall(r"<task>(.*?)</task>", response, re.DOTALL)
            for task in tasks:
                if task.strip():
                    operations.append({
                        "operation": "add",
                        "description": task.strip(),
                        "priority": "normal"
                    })
        
        return operations

    def _process_task_operations(self, operations: List[Dict]) -> None:
        """处理任务操作（添加、修改、删除）"""
        for op in operations:
            operation_type = op.get("operation")
            
            if operation_type == "add":
                # 添加新任务到待处理任务列表
                self.pending_tasks.append({
                    "description": op["description"],
                    "priority": op.get("priority", "normal"),
                    "executor_type": op.get("executor_type")
                })
            
            elif operation_type == "modify":
                # 修改待处理任务
                task_id = op.get("id")
                if task_id and task_id.isdigit():
                    idx = int(task_id) - 1
                    if 0 <= idx < len(self.pending_tasks):
                        if "description" in op:
                            self.pending_tasks[idx]["description"] = op["description"]
                        if "priority" in op and op["priority"]:
                            self.pending_tasks[idx]["priority"] = op["priority"]
                        if "executor_type" in op and op["executor_type"]:
                            self.pending_tasks[idx]["executor_type"] = op["executor_type"]
            
            elif operation_type == "delete":
                # 删除待处理任务
                task_id = op.get("id")
                if task_id and task_id.isdigit():
                    idx = int(task_id) - 1
                    if 0 <= idx < len(self.pending_tasks):
                        del self.pending_tasks[idx]
        
        # 按优先级排序待处理任务
        priority_order = {"high": 0, "normal": 1, "low": 2}
        self.pending_tasks.sort(key=lambda x: priority_order.get(x.get("priority", "normal"), 1))

    async def _execute_task(self, executor: BaseAgent, task_prompt: str) -> str:
        """执行单个任务"""
        try:
            # 使用代理执行任务
            return await executor.run(task_prompt)
        except Exception as e:
            logger.error(f"任务执行错误: {str(e)}")
            return f"任务执行失败: {str(e)}"

    def _format_task_history(self) -> str:
        """格式化任务历史以便在提示中使用"""
        if not self.completed_tasks:
            return "尚无已完成的任务"
            
        history = "已完成任务概览：\n"
        for i, task in enumerate(self.completed_tasks):
            history += f"任务 {i+1}: {task['description']}\n"
            history += f"状态: {task['status']}\n"
            history += f"结果: {task['result']}\n"
            history += "----------\n"
        
        if len(self.completed_tasks) > 0:
            history += f"\n已完成任务总数: {len(self.completed_tasks)}\n"
            history += "请根据以上任务历史，避免重复工作，专注于当前任务。\n"
        
        return history 
    
    def _format_pending_tasks(self) -> str:
        """格式化待处理任务列表"""
        if not self.pending_tasks:
            return "尚无待处理任务"
            
        pending = "待处理任务列表：\n"
        for i, task in enumerate(self.pending_tasks):
            pending += f"任务 {i+1}: {task['description']}\n"
            pending += f"优先级: {task.get('priority', 'normal')}\n"
            if task.get("executor_type"):
                pending += f"执行器类型: {task['executor_type']}\n"
            pending += "----------\n"
        
        return pending 