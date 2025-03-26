from typing import List, Dict, Any

from jinja2 import Environment, FileSystemLoader

def render_scheduler_template(
    user_requirement: str,
    completed_tasks: List[Dict[str, Any]]
) -> str:
    """
    渲染调度器模板
    
    Args:
        user_requirement: 用户需求
        completed_tasks: 已完成任务列表，每个任务包含description、status和result字段
        
    Returns:
        渲染后的模板字符串
    """
    # 创建Jinja2环境
    env = Environment(
        loader=FileSystemLoader("app/prompt/library")
    )
    
    # 加载模板
    template = env.get_template("scheduler.jinja")
    
    # 准备模板数据
    template_data = {
        "user_requirement": user_requirement,
        "completed_tasks": completed_tasks
    }
    
    # 渲染模板
    return template.render(**template_data)
