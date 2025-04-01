import base64
import os
from typing import Optional, Dict, Any, Union
import io
from PIL import Image  # 需要添加pillow依赖
import shutil

from app.config import config, WORKSPACE_ROOT
from app.llm import LLM
from app.logger import logger
from app.tool.base import BaseTool, ToolResult

# 检查是否安装了tesseract
TESSERACT_PATH = "/opt/homebrew/bin/tesseract"  # Homebrew 安装的默认路径
TESSERACT_AVAILABLE = os.path.exists(TESSERACT_PATH) or bool(shutil.which("tesseract"))

# OCR配置
OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "chi_sim+eng")  # 默认优先简体中文，然后英文
OCR_CONFIG = os.getenv("OCR_CONFIG", "--psm 11 --oem 3")  # 默认OCR配置

# 如果已安装tesseract，则导入pytesseract
if TESSERACT_AVAILABLE:
    try:
        import pytesseract
        # 显式设置 Tesseract 命令的路径
        if os.path.exists(TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        logger.info(f"Tesseract OCR 已启用，路径: {pytesseract.pytesseract.tesseract_cmd}")
    except ImportError:
        TESSERACT_AVAILABLE = False
        logger.warning("无法导入pytesseract模块，OCR功能已禁用")
else:
    logger.warning("系统中未安装Tesseract OCR，OCR功能已禁用")


class ImageUnderstanding(BaseTool):
    name: str = "image_understanding"
    description: str = """
工具通过OCR分析图像文本内容生成文本描述。支持本地图像文件路径或Base64编码的图像数据。
功能包括:
- 提取并分析图像中的文本内容
- 基于提取的文本回答问题
- 分析文档、截图中的文本信息
- 根据具体需求解释图像中的文本内容
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
                "description": "分析图像的具体目标，如'解析文档内容'、'提取文本'、'回答问题'等",
            },
            "model_name": {
                "type": "string",
                "description": "要使用的模型名称，默认使用配置中的默认模型",
            },
        },
        "anyOf": [
            {"required": ["image_path", "goal"]},
            {"required": ["base64_image", "goal"]},
        ],
    }

    def _extract_text_from_image(self, image_data: bytes) -> str:
        """
        从图像中提取文本

        Args:
            image_data: 图像数据

        Returns:
            提取的文本
        """
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract OCR 未安装或未启用，无法执行OCR")
            return ""

        try:
            # 将二进制数据转换为图像
            image = Image.open(io.BytesIO(image_data))

            # 使用pytesseract进行OCR
            logger.info(f"使用语言: {OCR_LANGUAGE}, 配置: {OCR_CONFIG}")
            extracted_text = pytesseract.image_to_string(
                image,
                lang=OCR_LANGUAGE,
                config=OCR_CONFIG
            )

            # 清理文本
            extracted_text = extracted_text.strip()
            if extracted_text:
                logger.info(f"OCR成功提取文本，长度: {len(extracted_text)}")

            return extracted_text
        except Exception as e:
            logger.error(f"OCR提取文本失败: {str(e)}")
            return ""

    def _compress_image(self, base64_img: str, max_size_mb: float = 4.5) -> str:
        """
        压缩图像以确保不超过指定的大小限制

        Args:
            base64_img: Base64编码的图像
            max_size_mb: 最大文件大小（MB）

        Returns:
            压缩后的Base64编码图像
        """
        # 检查当前图像大小
        current_size_mb = len(base64_img) * 3 / 4 / (1024 * 1024)  # Base64编码大约增加33%的大小

        if current_size_mb <= max_size_mb:
            logger.info(f"图像大小为 {current_size_mb:.2f}MB，无需压缩")
            return base64_img

        logger.info(f"图像大小为 {current_size_mb:.2f}MB，超过限制 {max_size_mb}MB，开始压缩")

        # 解码Base64图像
        img_data = base64.b64decode(base64_img)
        img = Image.open(io.BytesIO(img_data))

        # 设置初始质量
        quality = 95
        # 设置初始尺寸缩放比例
        scale = 1.0

        compressed_base64 = base64_img

        # 逐步降低质量和尺寸直到满足大小要求
        while current_size_mb > max_size_mb and (quality >= 30 or scale >= 0.3):
            # 先尝试降低质量
            if quality >= 30:
                quality -= 5
            # 如果质量已经很低，则尝试缩小尺寸
            elif scale >= 0.3:
                scale -= 0.1

            # 调整图像尺寸
            if scale < 1.0:
                new_width = int(img.width * scale)
                new_height = int(img.height * scale)
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            else:
                resized_img = img

            # 保存为JPEG格式
            buffer = io.BytesIO()
            resized_img.save(buffer, format="JPEG", quality=quality, optimize=True)

            # 转换为Base64
            compressed_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # 计算新大小
            current_size_mb = len(compressed_base64) * 3 / 4 / (1024 * 1024)

            logger.info(f"压缩后大小: {current_size_mb:.2f}MB (质量: {quality}, 缩放: {scale:.1f})")

        # 如果压缩后仍然超过限制，记录警告
        if current_size_mb > max_size_mb:
            logger.warning(f"图像压缩后仍超过大小限制: {current_size_mb:.2f}MB > {max_size_mb}MB")

        return compressed_base64

    def _get_config_value(self, config_obj: Any, key: str, default: Any = None) -> Any:
        """
        安全地从配置中获取值，支持字典和对象两种格式

        Args:
            config_obj: 配置对象或字典
            key: 要获取的键名
            default: 如果未找到键时的默认值

        Returns:
            找到的值或默认值
        """
        if isinstance(config_obj, dict):
            return config_obj.get(key, default)
        elif hasattr(config_obj, key):
            return getattr(config_obj, key)
        return default

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
            model_name: 要使用的模型名称

        Returns:
            包含图像理解结果的ToolResult
        """
        if not image_path and not base64_image:
            return ToolResult(
                error="必须提供图像路径或Base64编码的图像数据"
            )

        try:
            # 处理图像数据
            image_binary = None
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

                # 读取图像文件
                logger.info(f"正在读取图像文件: {full_path}")
                with open(full_path, "rb") as image_file:
                    image_binary = image_file.read()
                    base64_image = base64.b64encode(image_binary).decode("utf-8")
            else:
                # 使用提供的Base64编码图像
                image_binary = base64.b64decode(base64_image)

            # 压缩图像确保不超过5MB
            base64_image = self._compress_image(base64_image)

            # 使用OCR提取文本
            logger.info("使用OCR提取图像中的文本")
            ocr_text = self._extract_text_from_image(image_binary)

            if ocr_text:
                logger.info(f"成功提取图像中的文本，长度：{len(ocr_text)}")
                # 构建包含OCR文本的提示词
                prompt = f"""
请基于以下从图像中提取的文本，{goal}。

提取的文本内容：
{ocr_text}

请提供详细的与用户请求有关的分析结果。
<用户请求>
{goal}
</用户请求>
"""
            else:
                logger.warning("未能从图像中提取到文本")
                prompt = f"""
我尝试从一张图像中提取文本，但未能成功提取到任何文本内容。
这可能是因为图像中没有文本，或OCR系统未能正确识别。
请针对这种情况，{goal}。
"""

            # 使用默认LLM进行处理
            logger.info("使用文本模型处理OCR提取的文本")

            # 初始化LLM实例，使用与base.py相同的方式
            config_name = "default"
            llm = LLM(config_name=config_name)

            # 如果用户指定了模型，覆盖默认模型
            if model_name:
                llm.model = model_name
                logger.info(f"使用指定模型: {model_name}")

            try:
                # 使用正确的 ask 方法格式，参照 app/agent/cot.py
                user_message = {"role": "user", "content": prompt}

                # 使用参考中的格式调用 ask 方法
                response = await llm.ask(
                    messages=[user_message],
                    system_msgs=None  # 不使用系统提示
                )

                logger.info("文本分析完成")
                response_content = response
            except AttributeError as ae:
                logger.error(f"LLM对象属性错误: {str(ae)}")
                response_content = f"模型配置错误: {str(ae)}"
            except Exception as e:
                logger.error(f"调用LLM时出错: {str(e)}")
                response_content = f"无法处理图像文本: {str(e)}"

            # 返回结果
            return ToolResult(
                output=response_content,
                base64_image=base64_image,  # 返回图像数据以便在对话中显示
                ocr_text=ocr_text  # 额外返回OCR提取的文本，可用于调试或前端展示
            )

        except Exception as e:
            logger.error(f"图像理解过程中出错: {str(e)}")
            return ToolResult(
                error=f"图像理解失败: {str(e)}"
            )
