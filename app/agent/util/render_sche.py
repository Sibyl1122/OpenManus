from typing import List, Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader

def render_scheduler_template(
    user_requirement: str,
    completed_tasks: List[Dict[str, Any]],
    template_name: str = "scheduler_cn.jinja",
    pending_tasks: Optional[List[Dict[str, Any]]] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    渲染调度器模板
    
    Args:
        user_requirement: 用户需求
        completed_tasks: 已完成任务列表，每个任务包含description、status和result字段
        template_name: 模板文件名称，默认为"scheduler_cn.jinja"
        pending_tasks: 待处理任务列表，每个任务包含description、priority等字段
        additional_data: 额外的模板数据，可选
        
    Returns:
        渲染后的模板字符串
    """
    # 创建Jinja2环境
    env = Environment(
        loader=FileSystemLoader("app/prompt/library")
    )
    
    # 加载模板
    template = env.get_template(template_name)
    
    # 准备模板数据
    template_data = {
        "user_requirement": user_requirement,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks or []
    }
    
    # 合并额外的模板数据（如果有）
    if additional_data:
        template_data.update(additional_data)
    
    # 渲染模板
    return template.render(**template_data)
