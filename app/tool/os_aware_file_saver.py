import os
import platform

import aiofiles

from app.tool.base import BaseTool


class OSAwareFileSaver(BaseTool):
    name: str = "os_aware_file_saver"
    description: str = """根据操作系统类型保存内容到本地文件。
此工具会根据当前操作系统类型自动调整文件路径格式和保存位置。
可以指定不同操作系统下的保存路径，或使用默认路径。
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "(必填) 要保存到文件的内容。",
            },
            "file_name": {
                "type": "string",
                "description": "(必填) 文件名，包括扩展名。例如：'data.txt'、'script.py'等。",
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
            "mode": {
                "type": "string",
                "description": "(可选) 文件打开模式。默认为'w'表示写入。使用'a'表示追加。",
                "enum": ["w", "a"],
                "default": "w",
            },
        },
        "required": ["content", "file_name"],
    }

    async def execute(
        self, 
        content: str, 
        file_name: str, 
        windows_path: str = None, 
        macos_path: str = None, 
        linux_path: str = None, 
        mode: str = "w"
    ) -> str:
        """
        根据操作系统类型保存内容到文件。

        Args:
            content (str): 要保存的内容。
            file_name (str): 文件名，包括扩展名。
            windows_path (str, optional): Windows系统下的保存路径。
            macos_path (str, optional): macOS系统下的保存路径。
            linux_path (str, optional): Linux系统下的保存路径。
            mode (str, optional): 文件打开模式。默认为'w'表示写入。使用'a'表示追加。

        Returns:
            str: 表示操作结果的消息。
        """
        try:
            # 获取当前操作系统类型
            current_os = platform.system()
            
            # 根据操作系统类型选择保存路径
            if current_os == "Windows":
                base_path = windows_path or os.path.join(os.path.expanduser("~"), "Documents")
                path_separator = "\\"
            elif current_os == "Darwin":  # macOS
                base_path = macos_path or os.path.join(os.path.expanduser("~"), "Documents")
                path_separator = "/"
            elif current_os == "Linux":
                base_path = linux_path or os.path.join(os.path.expanduser("~"), "Documents")
                path_separator = "/"
            else:
                # 未知操作系统，使用当前目录
                base_path = "."
                path_separator = os.path.sep
            
            # 构建完整的文件路径
            file_path = os.path.join(base_path, file_name)
            
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # 写入文件
            async with aiofiles.open(file_path, mode, encoding="utf-8") as file:
                await file.write(content)
            
            return f"内容已成功保存到 {file_path}（操作系统：{current_os}）"
        except Exception as e:
            return f"保存文件时出错: {str(e)}" 