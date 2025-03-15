import platform
import os
import psutil
import json
from typing import Dict, Optional

from app.tool.base import BaseTool, ToolResult


class SystemInfoTool(BaseTool):
    """A tool for retrieving system information."""

    name: str = "system_info"
    description: str = """获取系统信息，包括操作系统、CPU、内存、磁盘等信息。
可以获取特定类型的信息或全部系统信息。
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "info_type": {
                "type": "string",
                "description": "要获取的信息类型，可选值为：'os'（操作系统信息）、'cpu'（CPU信息）、'memory'（内存信息）、'disk'（磁盘信息）、'all'（所有信息）",
                "enum": ["os", "cpu", "memory", "disk", "all"],
                "default": "all",
            },
            "format": {
                "type": "string",
                "description": "返回信息的格式，可选值为：'text'（文本格式）、'json'（JSON格式）",
                "enum": ["text", "json"],
                "default": "text",
            },
        },
        "required": ["info_type"],
    }

    async def execute(
        self,
        info_type: str = "all",
        format: str = "text",
        **kwargs,
    ) -> ToolResult:
        """
        获取系统信息。

        Args:
            info_type (str): 要获取的信息类型，可选值为：'os'、'cpu'、'memory'、'disk'、'all'
            format (str): 返回信息的格式，可选值为：'text'、'json'

        Returns:
            ToolResult: 包含系统信息的结果
        """
        try:
            info = {}
            
            # 获取操作系统信息
            if info_type in ["os", "all"]:
                info["os"] = {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "platform": platform.platform(),
                    "node": platform.node(),
                }
            
            # 获取CPU信息
            if info_type in ["cpu", "all"]:
                info["cpu"] = {
                    "physical_cores": psutil.cpu_count(logical=False),
                    "total_cores": psutil.cpu_count(logical=True),
                    "cpu_percent": psutil.cpu_percent(),
                    "cpu_freq": {
                        "current": getattr(psutil.cpu_freq(), "current", None),
                        "min": getattr(psutil.cpu_freq(), "min", None),
                        "max": getattr(psutil.cpu_freq(), "max", None),
                    },
                }
            
            # 获取内存信息
            if info_type in ["memory", "all"]:
                mem = psutil.virtual_memory()
                info["memory"] = {
                    "total": mem.total,
                    "available": mem.available,
                    "used": mem.used,
                    "percent": mem.percent,
                }
            
            # 获取磁盘信息
            if info_type in ["disk", "all"]:
                disk = psutil.disk_usage('/')
                info["disk"] = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                }
            
            # 根据格式返回结果
            if format == "json":
                return ToolResult(output=json.dumps(info, indent=2, ensure_ascii=False))
            else:
                # 文本格式
                text_result = ""
                
                if "os" in info:
                    text_result += "操作系统信息:\n"
                    text_result += f"  系统: {info['os']['system']}\n"
                    text_result += f"  发行版: {info['os']['release']}\n"
                    text_result += f"  版本: {info['os']['version']}\n"
                    text_result += f"  架构: {info['os']['machine']}\n"
                    text_result += f"  处理器: {info['os']['processor']}\n"
                    text_result += f"  平台: {info['os']['platform']}\n"
                    text_result += f"  节点名: {info['os']['node']}\n\n"
                
                if "cpu" in info:
                    text_result += "CPU信息:\n"
                    text_result += f"  物理核心数: {info['cpu']['physical_cores']}\n"
                    text_result += f"  逻辑核心数: {info['cpu']['total_cores']}\n"
                    text_result += f"  CPU使用率: {info['cpu']['cpu_percent']}%\n"
                    if info['cpu']['cpu_freq']['current']:
                        text_result += f"  当前频率: {info['cpu']['cpu_freq']['current']} MHz\n"
                    if info['cpu']['cpu_freq']['min']:
                        text_result += f"  最小频率: {info['cpu']['cpu_freq']['min']} MHz\n"
                    if info['cpu']['cpu_freq']['max']:
                        text_result += f"  最大频率: {info['cpu']['cpu_freq']['max']} MHz\n\n"
                
                if "memory" in info:
                    text_result += "内存信息:\n"
                    text_result += f"  总内存: {self._format_bytes(info['memory']['total'])}\n"
                    text_result += f"  可用内存: {self._format_bytes(info['memory']['available'])}\n"
                    text_result += f"  已用内存: {self._format_bytes(info['memory']['used'])}\n"
                    text_result += f"  内存使用率: {info['memory']['percent']}%\n\n"
                
                if "disk" in info:
                    text_result += "磁盘信息:\n"
                    text_result += f"  总空间: {self._format_bytes(info['disk']['total'])}\n"
                    text_result += f"  已用空间: {self._format_bytes(info['disk']['used'])}\n"
                    text_result += f"  可用空间: {self._format_bytes(info['disk']['free'])}\n"
                    text_result += f"  磁盘使用率: {info['disk']['percent']}%\n"
                
                return ToolResult(output=text_result)
                
        except Exception as e:
            return ToolResult(error=f"获取系统信息时出错: {str(e)}")
    
    def _format_bytes(self, bytes_value):
        """将字节数格式化为人类可读的形式"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB" 