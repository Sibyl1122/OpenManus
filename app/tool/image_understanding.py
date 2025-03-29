import base64
import os
from typing import Optional, Dict

from app.config import config, WORKSPACE_ROOT
from app.llm import LLM, MULTIMODAL_MODELS
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class ImageUnderstanding(BaseTool):
    name: str = "image_understanding"
    description: str = """
工具通过分析图像内容生成文本描述。支持本地图像文件路径或Base64编码的图像数据。
功能包括:
- 分析网页截图中的内容和结构
- 识别并描述图像中的物体、文本和场景
- 提取图像中的可读文本
- 根据具体需求解释图像内容
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "图像文件路径，可以是相对于工作区的路径或绝对路径",
            },
            "base64_image": {
                "type": "string",
                "description": "Base64编码的图像数据，与image_path二选一",
            },
            "goal": {
                "type": "string",
                "description": "分析图像的具体目标，如'描述网页内容'、'提取文本'、'识别界面元素'等",
            },
            "model_name": {
                "type": "string",
                "description": f"要使用的多模态模型名称，默认使用配置中的模型。支持的模型: {', '.join(MULTIMODAL_MODELS)}",
            },
        },
        "anyOf": [
            {"required": ["image_path", "goal"]},
            {"required": ["base64_image", "goal"]},
        ],
    }

    async def execute(
        self,
        goal: str,
        image_path: Optional[str] = None,
        base64_image: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        分析图像并生成文本描述。

        Args:
            goal: 分析图像的具体目标
            image_path: 图像文件路径
            base64_image: Base64编码的图像数据
            model_name: 要使用的多模态模型名称

        Returns:
            包含图像理解结果的ToolResult
        """
        if not image_path and not base64_image:
            return ToolResult(
                error="必须提供图像路径或Base64编码的图像数据"
            )

        # 确定使用的模型
        model = model_name or self._get_default_multimodal_model()
        if model not in MULTIMODAL_MODELS:
            return ToolResult(
                error=f"模型 {model} 不支持图像理解。请使用以下模型之一: {', '.join(MULTIMODAL_MODELS)}"
            )

        try:
            # 处理图像数据
            if image_path:
                # 解析图像路径
                if os.path.isabs(image_path):
                    full_path = image_path
                else:
                    full_path = os.path.join(WORKSPACE_ROOT, image_path)

                # 检查文件是否存在
                if not os.path.exists(full_path):
                    return ToolResult(
                        error=f"图像文件不存在: {full_path}"
                    )

                # 读取并编码图像
                logger.info(f"正在读取图像文件: {full_path}")
                with open(full_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            # 准备提示词
            prompt = f"""
请分析以下图像，{goal}。
请提供详细的分析结果，包括你看到的所有相关信息。
"""

            # 使用LLM进行图像分析
            logger.info(f"使用模型 {model} 分析图像")
            llm = LLM(llm_config=self._get_llm_config(model))
            response = await llm.ask_with_images(
                messages=[{"role": "user", "content": prompt}],
                images=[{"url": f"data:image/jpeg;base64,{base64_image}"}],
                stream=False
            )

            logger.info("图像分析完成")
            return ToolResult(
                content=response,
                base64_image=base64_image  # 返回图像数据以便在对话中显示
            )

        except Exception as e:
            logger.error(f"图像理解过程中出错: {str(e)}")
            return ToolResult(
                error=f"图像理解失败: {str(e)}"
            )

    def _get_default_multimodal_model(self) -> str:
        """获取默认的多模态模型"""
        # 检查配置中的当前模型是否支持多模态
        current_model = config.llm.get("vision_model").model
        if current_model in MULTIMODAL_MODELS:
            return current_model

        # 否则使用第一个支持的模型
        return MULTIMODAL_MODELS[0]

    def _get_llm_config(self, model_name: str) -> Dict:
        """基于现有配置创建新的LLM配置"""
        # 复制默认配置
        llm_config = dict(config.llm)

        # 修改模型名称
        default_config = llm_config.get("vision_model", {})
        model_config = default_config.copy()
        model_config.model = model_name

        # 添加到配置中
        llm_config["image_model"] = model_config

        return llm_config
