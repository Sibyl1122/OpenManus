import os
import platform
import json
import psutil

import aiofiles

from app.tool.base import BaseTool, ToolResult


class SystemInfoSaver(BaseTool):
    """A tool for retrieving system information and saving it to a file."""

    name: str = "system_info_saver"
    description: str = """获取系统信息并直接保存到文件。
此工具会根据当前操作系统类型自动调整文件路径格式和保存位置。
可以获取特定类型的系统信息（操作系统、CPU、内存、磁盘）或全部信息。
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
            "file_name": {
                "type": "string",
                "description": "文件名，包括扩展名。例如：'system_info.txt'、'system_info.json'等。",
                "default": "system_info.txt",
            },
            "format": {
                "type": "string",
                "description": "保存信息的格式，可选值为：'text'（文本格式）、'json'（JSON格式）",
                "enum": ["text", "json"],
                "default": "text",
            },
            "windows_path": {
                "type": "string",
                "description": "(可选) Windows系统下的保存路径。如果不指定，将使用默认路径。",
            },
            "macos_path": {
                "type": "string",
                "description": "(可选) macOS系统下的保存路径。如果不指定，将使用默认路径。",
            },
            "linux_path": {
                "type": "string",
                "description": "(可选) Linux系统下的保存路径。如果不指定，将使用默认路径。",
            },
        },
        "required": ["info_type"],
    }

    async def execute(
        self,
        info_type: str = "all",
        file_name: str = "system_info.txt",
        format: str = "text",
        windows_path: str = None,
        macos_path: str = None,
        linux_path: str = None,
        **kwargs,
    ) -> ToolResult:
        """
        获取系统信息并保存到文件。

        Args:
            info_type (str): 要获取的信息类型，可选值为：'os'、'cpu'、'memory'、'disk'、'all'
            file_name (str): 文件名，包括扩展名
            format (str): 保存信息的格式，可选值为：'text'、'json'
            windows_path (str, optional): Windows系统下的保存路径
            macos_path (str, optional): macOS系统下的保存路径
            linux_path (str, optional): Linux系统下的保存路径

        Returns:
            ToolResult: 包含操作结果的信息
        """
        try:
            # 获取系统信息
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
            
            # 根据格式生成内容
            if format == "json":
                content = json.dumps(info, indent=2, ensure_ascii=False)
                if not file_name.endswith('.json'):
                    file_name += '.json'
            else:
                # 文本格式
                content = ""
                
                if "os" in info:
                    content += "操作系统信息:\n"
                    content += f"  系统: {info['os']['system']}\n"
                    content += f"  发行版: {info['os']['release']}\n"
                    content += f"  版本: {info['os']['version']}\n"
                    content += f"  架构: {info['os']['machine']}\n"
                    content += f"  处理器: {info['os']['processor']}\n"
                    content += f"  平台: {info['os']['platform']}\n"
                    content += f"  节点名: {info['os']['node']}\n\n"
                
                if "cpu" in info:
                    content += "CPU信息:\n"
                    content += f"  物理核心数: {info['cpu']['physical_cores']}\n"
                    content += f"  逻辑核心数: {info['cpu']['total_cores']}\n"
                    content += f"  CPU使用率: {info['cpu']['cpu_percent']}%\n"
                    if info['cpu']['cpu_freq']['current']:
                        content += f"  当前频率: {info['cpu']['cpu_freq']['current']} MHz\n"
                    if info['cpu']['cpu_freq']['min']:
                        content += f"  最小频率: {info['cpu']['cpu_freq']['min']} MHz\n"
                    if info['cpu']['cpu_freq']['max']:
                        content += f"  最大频率: {info['cpu']['cpu_freq']['max']} MHz\n\n"
                
                if "memory" in info:
                    content += "内存信息:\n"
                    content += f"  总内存: {self._format_bytes(info['memory']['total'])}\n"
                    content += f"  可用内存: {self._format_bytes(info['memory']['available'])}\n"
                    content += f"  已用内存: {self._format_bytes(info['memory']['used'])}\n"
                    content += f"  内存使用率: {info['memory']['percent']}%\n\n"
                
                if "disk" in info:
                    content += "磁盘信息:\n"
                    content += f"  总空间: {self._format_bytes(info['disk']['total'])}\n"
                    content += f"  已用空间: {self._format_bytes(info['disk']['used'])}\n"
                    content += f"  可用空间: {self._format_bytes(info['disk']['free'])}\n"
                    content += f"  磁盘使用率: {info['disk']['percent']}%\n"
                
                if not file_name.endswith('.txt'):
                    file_name += '.txt'
            
            # 获取当前操作系统类型
            current_os = platform.system()
            
            # 根据操作系统类型选择保存路径
            if current_os == "Windows":
                base_path = windows_path or os.path.join(os.path.expanduser("~"), "Documents")
            elif current_os == "Darwin":  # macOS
                base_path = macos_path or os.path.join(os.path.expanduser("~"), "Documents")
            elif current_os == "Linux":
                base_path = linux_path or os.path.join(os.path.expanduser("~"), "Documents")
            else:
                # 未知操作系统，使用当前目录
                base_path = "."
            
            # 构建完整的文件路径
            file_path = os.path.join(base_path, file_name)
            
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # 写入文件
            async with aiofiles.open(file_path, "w", encoding="utf-8") as file:
                await file.write(content)
            
            return ToolResult(output=f"系统信息已成功保存到 {file_path}（操作系统：{current_os}）")
        except Exception as e:
            return ToolResult(error=f"获取或保存系统信息时出错: {str(e)}")
    
    def _format_bytes(self, bytes_value):
        """将字节数格式化为人类可读的形式"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB" 