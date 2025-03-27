from app.agent.util.render_sche import render_scheduler_template

# 测试数据
user_requirement = "帮我创建一个简单的网站"
completed_tasks = [
    {
        "description": "设计网站首页布局",
        "status": "completed",
        "result": "已完成首页布局设计，包括导航栏、主要内容区和页脚"
    },
    {
        "description": "实现网站导航功能",
        "status": "completed",
        "result": "已实现导航栏，包括首页、关于我们、服务和联系我们四个链接"
    }
]

# 渲染模板
result = render_scheduler_template(user_requirement, completed_tasks)

# 打印结果
print(result) 