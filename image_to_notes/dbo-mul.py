import os
import sys
import json
import time
import requests
import logging
import argparse
import base64
import re
from datetime import datetime
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image, ImageFilter, ImageOps

# 配置缓存目录
CACHE_DIR = Path("D:/uv/uv_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 加载环境变量
load_dotenv()

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("travel_writer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('travel_writer')

class Config:
    """配置管理类"""
    def __init__(self):
        self.input_dir = Path("D:/train/xhs/out")
        self.output_dir = self.input_dir / "results"
        self.DOUBAO_API_BASE = os.getenv("DOUBAO_API_BASE")
        self.DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY")
        self.DOUBAO_MODEL_ID = os.getenv("DOUBAO_MODEL_ID", "doubao-seed-1-6-thinking-250615")
        self.max_retries = 5
        self.retry_base_delay = 3
        self.max_files = 50
        self.supported_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        self.max_image_size = 768
        self.image_detail_level = os.getenv("IMAGE_DETAIL_LEVEL", "low")
        self.max_image_pixels = 36000000
        self.max_image_size_mb = 10
        
        # 综合处理相关配置
        self.max_images_for_summary = 8  # 综合处理时最多使用的图片数量
        self.max_summary_tokens = 2000  # 综合文案的最大token数
        
        # 验证配置
        if not self.DOUBAO_API_BASE or not self.DOUBAO_API_KEY:
            logger.error("豆包API配置不完整，请在 .env 文件中配置 DOUBAO_API_BASE 和 DOUBAO_API_KEY")
            raise EnvironmentError("豆包API配置缺失")
            
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"配置加载完成 | API基础URL: {self.DOUBAO_API_BASE} | 模型ID: {self.DOUBAO_MODEL_ID} | 图像精细度: {self.image_detail_level}")
        logger.info(f"综合处理配置 | 最大图片数: {self.max_images_for_summary} | 最大token: {self.max_summary_tokens}")

class ImagePreprocessor:
    """图像预处理模块"""
    def __init__(self, config):
        self.config = config
        logger.info(f"图像预处理模块初始化 | 最大尺寸: {config.max_image_size}px | 精细度: {config.image_detail_level}")
    
    def sanitize_image(self, image_path):
        """安全处理图像 - 清除元数据和模糊人脸"""
        try:
            # 打开图像并清除EXIF元数据
            img = Image.open(image_path)
            
            # 检查图像尺寸限制
            total_pixels = img.width * img.height
            if total_pixels > self.config.max_image_pixels:
                ratio = (self.config.max_image_pixels / total_pixels) ** 0.5
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
                logger.warning(f"图像尺寸过大 ({total_pixels}像素)，已调整至 {new_size[0]}x{new_size[1]}")
            
            # 创建一个新图像，复制像素数据但不含元数据
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
            return clean_img
        except Exception as e:
            logger.error(f"图像安全处理失败: {str(e)}")
            return Image.open(image_path)
    
    def optimize_image(self, img):
        """优化图像大小以减少API调用成本"""
        try:
            # 检查文件大小限制
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            file_size = buffer.tell() / (1024 * 1024)  # 转换为MB
            
            if file_size > self.config.max_image_size_mb:
                # 计算需要降低的质量百分比
                quality = int(75 * (self.config.max_image_size_mb / file_size))
                if quality < 20:
                    quality = 20  # 设置最低质量限制
                
                logger.warning(f"图像过大 ({file_size:.2f}MB)，将质量降低至 {quality}%")
            else:
                quality = 75
            
            # 保持宽高比缩小图像
            if max(img.size) > self.config.max_image_size:
                ratio = self.config.max_image_size / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
                logger.debug(f"图像尺寸调整: {img.size}")
            
            # 转换为JPEG减少文件大小
            if img.format != "JPEG":
                img = img.convert("RGB")
            
            # 转换为base64
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=quality)
            b64_data = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # 记录大小信息
            size_kb = len(b64_data) // 1000
            logger.info(f"图像优化完成 | 大小: {size_kb}KB")
            
            return b64_data
            
        except Exception as e:
            logger.error(f"图像优化失败: {str(e)}")
            raise

class DoubaoMultimodalGenerator:
    """使用豆包大模型的生成引擎"""
    def __init__(self, config):
        self.config = config
        self.api_url = f"{config.DOUBAO_API_BASE.rstrip('/')}/chat/completions"
        self.api_key = config.DOUBAO_API_KEY
        self.model_id = config.DOUBAO_MODEL_ID
        
        # 深度思考模式系统提示词
        self.deep_thinking_prompt = (
            "You should first think about the reasoning process in the mind and then provide the user with the answer. "
            "The reasoning process is enclosed within <think> </think> tags, i.e. <think> reasoning process here </think>here answer"
        )
        
        # 多图综合处理提示词 - 添加字数限制要求
        self.multi_image_prompt = """
        请根据提供的多张图片创作一篇综合的小红书风格旅行文案。
        
        重要要求：
        1. 生成一个吸引人的标题（含1-2个emoji） - 标题不超过20字
        2. 正文内容不超过1000字，综合描述旅行经历
        3. 包含多个目的地特色、实用建议和个人体验
        4. 添加3-5个精准话题标签
        
        输出格式：
        【标题】您的标题（含emoji）
        
        【正文】
        综合描述旅行经历，包含：
        - 至少3个目的地特色
        - 2个实用旅行建议
        - 1-2个个人体验故事
        - 结尾添加相关标签
        
        【标签】
        #标签1 #标签2 #标签3
        """
        
        self.api_calls = 0
        self.api_success = 0
        logger.info(f"豆包大模型引擎初始化 | API端点: {self.api_url} | 模型: {self.model_id}")
    
    def generate_caption(self, content_list):
        """生成文案并结构化输出，支持图文混排"""
        self.api_calls += 1
        retry_delay = self.config.retry_base_delay  # 初始重试延迟
        
        for attempt in range(self.config.max_retries + 1):  # 0到max_retries次尝试
            try:
                # 深度思考模式专用处理
                system_content = []
                if "vision-pro" in self.model_id.lower():
                    system_content.append({"type": "text", "text": self.deep_thinking_prompt})
                
                # 构建API请求数据（符合豆包API规范）
                payload = {
                    "model": self.model_id,  # 使用配置的模型ID
                    "messages": [
                        {
                            "role": "system",
                            "content": system_content
                        } if system_content else None,
                        {
                            "role": "user",
                            "content": content_list
                        }
                    ],
                    "stream": False,  # 关闭流式响应
                    "max_tokens": self.config.max_summary_tokens,  # 使用配置的token限制
                    "temperature": 0.7,  # 控制生成随机性
                    "top_p": 0.9,  # 核采样概率阈值
                }
                # 移除空元素
                payload["messages"] = [m for m in payload["messages"] if m is not None]
                
                # 为 seed 模型添加专用参数
                if "seed" in self.model_id.lower():
                    payload["seed"] = {
                        "mode": "creative",  # 创意模式
                        "creativity": 0.8,   # 创造力级别
                        "detail_level": "high"  # 细节丰富度
                    }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # 记录请求开始时间
                start_time = time.time()
                
                # 发送请求（增加超时时间）
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=120  # 增加超时时间
                )
                
                # 记录响应时间
                response_time = time.time() - start_time
                logger.info(f"API响应时间: {response_time:.2f}s | 状态码: {response.status_code}")
                
                # 处理响应
                if response.status_code == 200:
                    result = response.json()
                    
                    # 验证API响应结构
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        
                        # 记录用量信息
                        usage = result.get("usage", {})
                        logger.info(f"API调用成功 | 输入token: {usage.get('prompt_tokens', 'N/A')} | "
                                    f"输出token: {usage.get('completion_tokens', 'N/A')} | "
                                    f"总token: {usage.get('total_tokens', 'N/A')}")
                        
                        self.api_success += 1
                        return self._parse_output(content)
                    else:
                        error_msg = f"豆包API响应格式错误: {response.text}"
                        logger.error(error_msg)
                        # 继续重试
                        raise Exception(error_msg)
                else:
                    # 截断长错误消息
                    error_text = response.text[:500] + "..." if len(response.text) > 500 else response.text
                    error_msg = f"豆包API错误: {response.status_code} - {error_text}"
                    logger.error(error_msg)
                    
                    # 400错误不需要重试（参数错误）
                    if response.status_code == 400:
                        return {
                            "error": error_msg,
                            "success": False
                        }
                    # 其他状态码重试
                    raise Exception(error_msg)
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API请求超时，尝试 {attempt+1}/{self.config.max_retries}...")
                if attempt < self.config.max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    return {
                        "error": "请求超时，重试次数用尽",
                        "success": False
                    }
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误: {str(e)}，尝试 {attempt+1}/{self.config.max_retries}...")
                if attempt < self.config.max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return {
                        "error": f"连接错误: {str(e)}",
                        "success": False
                    }
            except Exception as e:
                logger.error(f"请求失败: {str(e)}")
                # 最后一次尝试后返回错误
                if attempt == self.config.max_retries:
                    return {
                        "error": str(e),
                        "success": False
                    }
                else:
                    logger.warning(f"尝试 {attempt+1}/{self.config.max_retries}...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
    
    def get_api_stats(self):
        """获取API调用统计"""
        return {
            "total_calls": self.api_calls,
            "success_calls": self.api_success,
            "success_rate": self.api_success / self.api_calls * 100 if self.api_calls else 0
        }
    
    def _parse_output(self, text):
        """解析生成文本为结构化数据，并强制限制字数"""
        try:
            # 提取标题
            title_match = re.search(r"【标题】(.+?)\n", text)
            if title_match:
                title = title_match.group(1).strip()
            else:
                # 备用提取方法
                first_line = text.split("\n")[0].strip()
                if len(first_line) < 30:
                    title = first_line
                else:
                    title = "精彩旅行分享"
            
            # 提取正文
            body_match = re.search(r"【正文】([\s\S]*?)(\n【标签】|\Z)", text)
            if body_match:
                body = body_match.group(1).strip()
            else:
                # 提取标题之后的所有内容直到标签
                body = re.sub(r"^.*?\n", "", text, count=1) if title else text
                body = re.sub(r"【标签】.*$", "", body, flags=re.DOTALL).strip()
            
            # 提取标签
            tags_match = re.search(r"【标签】(.+)$", text)
            if tags_match:
                tags = re.findall(r"#(\w+)", tags_match.group(1))
            else:
                tags = re.findall(r"#(\w+)", text)[:5]
            
            # 强制限制字数
            title_original_length = len(title)
            body_original_length = len(body)
            
            # 标题强制限制在20字以内
            if title_original_length > 20:
                logger.warning(f"标题超过20字限制({title_original_length}字)，进行截断处理")
                title = title[:20] + "..."  # 截断并添加省略号
            
            # 正文强制限制在1000字以内
            if body_original_length > 1000:
                logger.warning(f"正文超过1000字限制({body_original_length}字)，进行截断处理")
                body = body[:1000] + "..."  # 截断并添加省略号
                
            return {
                "title": title,
                "body": body,
                "tags": tags,
                "success": True,
                "length_check": {
                    "title_original_length": title_original_length,
                    "body_original_length": body_original_length
                }
            }
                
        except Exception as e:
            logger.error(f"文案解析失败: {str(e)}")
            return {
                "raw_output": text,
                "error": str(e),
                "success": False
            }

class TravelContentCreator:
    """主控制器：处理整个工作流程（只保留综合处理功能）"""
    def __init__(self, config):
        self.config = config
        self.preprocessor = ImagePreprocessor(config)
        self.generator = DoubaoMultimodalGenerator(config)
        self.total_images = 0
        self.success_count = 0
        logger.info("旅行内容生成器初始化完成（综合处理模式）")
    
    def process(self, context_file=None):
        """将整个目录的图片综合起来生成一个文案"""
        # 获取目录下的图片文件（不超过配置的最大数量）
        files = [
            f for f in self.config.input_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in self.config.supported_extensions
        ][:self.config.max_images_for_summary]
        
        if not files:
            logger.warning(f"在目录 {self.config.input_dir} 中未找到支持的图片文件")
            return {
                "status": "failed",
                "error": "未找到支持的图片文件"
            }
        
        logger.info(f"开始综合处理，共 {len(files)} 张图片")
        
        # 读取上下文信息（如果有）
        additional_context = ""
        if context_file:
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    additional_context = f.read()
                logger.info(f"加载上下文文件: {context_file} | 长度: {len(additional_context)}字符")
            except Exception as e:
                logger.warning(f"无法读取上下文文件: {context_file} | 错误: {str(e)}")
        
        # 预处理所有图片并转换为base64
        image_base64_list = []
        processed_files = []
        for file_path in files:
            try:
                clean_img = self.preprocessor.sanitize_image(file_path)
                image_base64 = self.preprocessor.optimize_image(clean_img)
                image_base64_list.append(image_base64)
                processed_files.append(str(file_path))
                logger.info(f"图片预处理完成: {file_path.name}")
            except Exception as e:
                logger.error(f"处理图片 {file_path} 时出错: {str(e)}")
        
        if not image_base64_list:
            logger.error("没有有效的图片可供处理")
            return {
                "status": "failed",
                "error": "没有有效的图片可供处理"
            }
        
        # 构建消息内容：先添加所有图片，然后添加文本提示
        content = []
        for img_base64 in image_base64_list:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}",
                    "detail": self.config.image_detail_level
                }
            })
        
        # 添加文本提示
        content.append({
            "type": "text",
            "text": f"{self.generator.multi_image_prompt}\n\n{additional_context}"
        })
        
        # 调用生成器
        caption = self.generator.generate_caption(content)
        
        if not caption["success"]:
            logger.error(f"综合文案生成失败: {caption.get('error', '未知错误')}")
            return {
                "status": "caption_generation_failed",
                "error": caption.get("error", "未知错误")
            }
        
        # 创建结果对象
        result = {
            "images": processed_files,
            "caption": caption,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        # 保存结果
        output_file = self.config.output_dir / "combined_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"综合文案生成完成，结果已保存到: {output_file}")
        
        # 打印成功信息
        print(f"\n综合文案生成成功！共使用 {len(image_base64_list)} 张图片")
        print(f"标题: {caption['title']} (长度: {len(caption['title'])}字)")
        print(f"\n文案内容:\n{caption['body']}")
        print(f"\n内容长度: {len(caption['body'])}字")
        print(f"\n标签: {', '.join(['#' + t for t in caption['tags']])}")
        
        return result

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="旅行内容生成工具（综合处理模式）")
    parser.add_argument("--max-size", type=int, default=768, help="最大图像尺寸(像素)")
    parser.add_argument("--detail", type=str, choices=["low", "high"], help="图像精细度控制 (low/high)")
    parser.add_argument("--context", type=str, help="指定上下文文件路径")
    args = parser.parse_args()
    
    # 初始化配置
    config = Config()
    config.max_image_size = args.max_size
    
    # 如果命令行指定了精细度，则覆盖默认值
    if args.detail:
        config.image_detail_level = args.detail
        logger.info(f"使用命令行指定的图像精细度: {args.detail}")
    
    # 初始化生成器
    creator = TravelContentCreator(config)
    
    # 处理上下文文件路径
    context_path = Path(args.context) if args.context else None
    
    # 执行综合处理
    result = creator.process(context_path)
    
    if not result or result["status"] != "success":
        error = result.get("error", "未知错误") if result else "处理失败"
        print(f"\n处理失败: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
