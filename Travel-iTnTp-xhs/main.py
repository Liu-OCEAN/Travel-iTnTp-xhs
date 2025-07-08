import subprocess
import sys
import os
import time
import json
import logging
import re  # 添加re模块导入
from datetime import datetime

# 强制设置控制台编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', buffering=1)
if sys.stderr.encoding != 'utf-8':
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', errors='replace', buffering=1)

# 配置日志（使用简化格式）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("automation.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # 使用修改后的sys.stdout
    ]
)
logger = logging.getLogger('auto_publisher')

# 路径配置
DBO_IMAGE_NOTES_SCRIPT = "dbo-image-notes.py"
AUTOPUB_SCRIPT = "autopub.py"
CONTENT_RESULT_FILE = os.path.join("out", "results", "combined_result.json")

def clean_output(text):
    """清理控制台输出，移除多余换行和特殊字符"""
    if not text:
        return ""
    
    # 首先移除所有控制字符（ASCII 0-31）
    cleaned = ''.join(char for char in text if 31 < ord(char) < 127 or char == '\n')
    
    # 减少连续空行
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # 截断过长的行
    lines = []
    for line in cleaned.splitlines():
        if len(line) > 200:
            lines.append(line[:197] + "...")
        else:
            lines.append(line)
    
    return "\n".join(lines)

def run_dbo_mul(context_file=None, max_size=None, detail=None):
    """运行 dbo-image-notes.py 脚本生成文案"""
    try:
        logger.info("启动文案生成流程...")
        
        # 获取虚拟环境的Python解释器路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        venv_python = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
        
        # 检查解释器是否存在
        if not os.path.exists(venv_python):
            logger.error(f"虚拟环境Python解释器不存在: {venv_python}")
            return False
            
        cmd = [venv_python, DBO_IMAGE_NOTES_SCRIPT]
        
        # 添加可选参数
        if context_file:
            cmd.extend(["--context", context_file])
        if max_size:
            cmd.extend(["--max-size", str(max_size)])
        if detail:
            cmd.extend(["--detail", detail])
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        try:
            # 直接运行子进程，不捕获输出（让子进程自行处理日志）
            result = subprocess.run(
                cmd, 
                check=True,
                text=True,
                encoding='utf-8'
            )
            
            # 检查结果文件
            if not os.path.exists(CONTENT_RESULT_FILE):
                logger.error("文案结果文件未生成")
                return False
            
            with open(CONTENT_RESULT_FILE, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            if result_data.get('status') != 'success':
                logger.error(f"文案生成失败: {result_data.get('error', '未知错误')}")
                return False
            
            caption = result_data['caption']
            logger.info(f"文案生成成功! 标题: {caption['title']}")
            logger.info(f"使用图片: {len(result_data['images'])}张, 标签: {', '.join(caption['tags'])}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"文案生成失败，退出码: {e.returncode}")
            return False
            
    except Exception as e:
        logger.exception("运行文案生成时发生意外错误")
        return False

def run_autopub(publish_time=None):
    """运行 autopub.py 脚本发布内容"""
    try:
        logger.info("启动内容发布流程...")
        
        # 获取虚拟环境的Python解释器路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        venv_python = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
        
        # 检查解释器是否存在
        if not os.path.exists(venv_python):
            logger.error(f"虚拟环境Python解释器不存在: {venv_python}")
            return False
            
        cmd = [venv_python, AUTOPUB_SCRIPT]
        
        # 添加可选参数
        if publish_time:
            cmd.extend(["--time", publish_time])
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        try:
            # 直接运行子进程，不捕获输出
            result = subprocess.run(
                cmd, 
                check=True,
                text=True,
                encoding='utf-8'
            )
            
            # 假设子进程返回0表示成功
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"内容发布失败，退出码: {e.returncode}")
            return False
            
    except Exception as e:
        logger.exception("运行内容发布时发生意外错误")
        return False

def main():
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="小红书内容自动化发布流程")
    
    # dbo-image-notes.py 参数
    parser.add_argument("--context", type=str, help="传递给 dbo-image-notes.py 的上下文文件路径")
    parser.add_argument("--max-size", type=int, help="最大图像尺寸(像素)")
    parser.add_argument("--detail", type=str, choices=["low", "high"], help="图像精细度控制")
    
    # autopub.py 参数
    parser.add_argument("--publish-time", type=str, 
                        help="发布时间 (格式: YYYY-MM-DD HH:MM 或 HH:MM)")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info(f"自动化流程启动 | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 步骤1: 生成文案
    logger.info(">>> 阶段1: 文案生成")
    if not run_dbo_mul(
        context_file=args.context,
        max_size=args.max_size,
        detail=args.detail
    ):
        logger.error("文案生成失败，终止流程")
        sys.exit(1)
    else:
        logger.info("✔ 文案生成成功")
    
    # 步骤2: 发布内容
    logger.info(">>> 阶段2: 内容发布")
    if not run_autopub(publish_time=args.publish_time):
        logger.error("内容发布失败")
        sys.exit(1)
    else:
        logger.info("✔ 内容发布成功")
    
    logger.info("=" * 60)
    logger.info("自动化流程成功完成!")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()