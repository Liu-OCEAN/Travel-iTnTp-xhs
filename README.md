# 小红书自动化发布系统

## 项目概述
这是一个自动化小红书图文内容生成与发布的系统，集成了豆包大模型生成文案和Selenium自动化发布功能。系统包含三个核心组件：

1. **文案生成引擎** - 使用豆包大模型分析图片生成高质量小红书文案  
2. **自动化发布工具** - 通过浏览器自动化实现一键发布  
3. **工作流集成** - 将文案生成和发布无缝衔接  

## 核心功能

- **多图智能分析**：自动识别图片内容并生成符合小红书风格的文案  
- **定时发布**：支持设置未来1小时到14天内的发布时间  
- **安全处理**：自动清除图片元数据和模糊人脸  
- **错误处理**：完善的错误日志和截图功能  
- **API集成**：与豆包大模型深度集成  

## 环境配置

### 系统要求
- Windows 10/11  
- Python 3.9+  
- Microsoft Edge浏览器  

### 环境变量配置
创建`.env`文件并配置以下参数：
```env
DOUBAO_API_BASE=豆包API地址
DOUBAO_API_KEY=豆包API密钥
DOUBAO_MODEL_ID=模型ID(可选)
```

## 安装步骤

1. 克隆项目仓库：
```bash
git clone https://github.com/Liu-OCEAN/Travel-iTnTp-xhs.git
cd Travel-iTnTp-xhs
```

2. 创建并激活虚拟环境：
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 文件结构
```
└── Travel-iTnTp-xhs
    ├── LICENSE
    ├── README.md
    ├── src
        ├── autopub.py
        ├── dbo-image-notes.py
        ├── main.py
        ├── pyproject.toml
        ├── README.md
        ├── requirements.txt
        ├── uv.lock
        └── out
        │   ├── 1.jpg
        │   ├── 2.jpg
        │   ├── 3.jpg
        │   ├── 4.jpg
        │   ├── config.json
        │   ├── results
        │       ├── combined_result.json
        │       └── processing_report.json
        │   └── cookies
        │       └── config.json
    └── .git

```

## 首次运行准备
1. 在`src/out/`目录放入需要发布的图片（建议1-9张）
2. 运行主程序并扫码登录小红书账号

## 使用说明

### 分步进行

#### 1. 生成文案
```bash
python dbo-image-notes.py --max-size 768 --detail high --context my_context.txt
```

#### 2. 手动发布
```bash
python autopub.py
```

### 自动化进行

```bash
python main.py
```

### 参数说明
| 参数 | 描述 | 示例 |
|------|------|------|
| `--max-size` | 图像最大尺寸(像素) | `--max-size 1024` |
| `--detail` | 图像处理精细度 | `--detail high` |
| `--context` | 额外上下文文件 | `--context notes.txt` |

## 注意事项

1. **账号安全**
   - 首次使用需要手机号+验证码登录小红书账号（扫码登录无法存储cookies）
   - 登录成功后自动保存cookies到`out/cookies/config.json`  
   - **不要分享`out/cookies/config.json`文件**  

2. **图片要求**
   - 支持JPG/PNG格式  
   - 建议尺寸800x1200  
   - 单张图片不超过10MB    

3. **时间限制**
   - 发布时间必须设置在1小时后
   - 最远可设置14天后的时间
   - 默认发布时间为当天20:00  

4. **错误处理**
   - 错误截图保存在`out/error_screenshots`目录  
   - 详细日志查看`automation.log`文件  

## 自定义提示词

修改`dbo-image-notes.py`中的`multi_image_prompt`变量来自定义提示词：
```python
self.multi_image_prompt = """
请根据提供的多张图片创作一篇综合的小红书风格旅行文案。

要求：
1. 生成一个吸引人的标题- 标题不超过16字
2. 300-500字正文，正文内容不超过800字,综合描述旅行经历
3. 包含多个目的地特色、实用建议和个人体验
4. 添加3-5个精准话题标签

[可添加您的个性化要求]
"""
```

## 贡献指南

欢迎通过Pull Request贡献代码：
1. Fork项目仓库  
2. 创建特性分支 (`git checkout -b feature/new-feature`)  
3. 提交修改 (`git commit -am 'Add new feature'`)  
4. 推送到分支 (`git push origin feature/new-feature`)  
5. 创建Pull Request  

## 许可证
本项目采用 Apache-2.0 License