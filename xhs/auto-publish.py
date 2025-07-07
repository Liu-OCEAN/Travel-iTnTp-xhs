import json
import os
import time
import traceback
from datetime import datetime, timedelta
import argparse  # 新增：用于命令行参数解析

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# 保存Cookies的文件路径
XIAOHONGSHU_COOKING = r'D:\train\xhs\out\cookies\config.json'
# 文案结果文件路径
CONTENT_RESULT_FILE = r'D:\train\xhs\out\results\combined_result.json'

# 获取浏览器驱动
def get_driver():
    options = webdriver.EdgeOptions()
    # 添加用户代理，避免被识别为自动化工具
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0')
    # 禁用自动化标志
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # 最大化窗口
    options.add_argument("--start-maximized")
    # 忽略SSL错误
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    driver = webdriver.Edge(options=options)
    return driver

# 小红书登录功能
def xiaohongshu_login(driver):
    # 检查Cookies文件是否存在
    if os.path.exists(XIAOHONGSHU_COOKING):
        print("cookies存在")
        try:
            with open(XIAOHONGSHU_COOKING) as f:
                cookies = json.loads(f.read())
                # 访问小红书创作者平台
                driver.get("https://creator.xiaohongshu.com/creator/post")
                time.sleep(2)  # 等待页面加载
                
                # 删除所有现有Cookies
                driver.delete_all_cookies()
                
                print("加载cookie")
                # 添加保存的Cookies
                for cookie in cookies:
                    # 过滤掉可能过期的cookie
                    if 'expiry' in cookie:
                        expiry_timestamp = cookie['expiry']
                        current_time = time.time()
                        if current_time > expiry_timestamp:
                            print(f"跳过过期cookie: {cookie['name']}")
                            continue
                    
                    try:
                        # 添加cookie前确保域名匹配
                        if "xiaohongshu.com" in cookie.get("domain", ""):
                            driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"添加cookie失败: {str(e)}")
                
                # 刷新页面
                print("刷新页面")
                driver.refresh()
                time.sleep(5)
                
                # 检查登录状态 - 通过页面标题判断
                try:
                    # 使用更宽松的标题检测
                    WebDriverWait(driver, 15).until(
                        EC.title_contains("小红书创作")
                    )
                    print("✅ 登录成功（检测到标题）")
                    return True
                except TimeoutException:
                    # 检查当前标题
                    current_title = driver.title
                    print(f"❌ 标题检测失败: 当前标题='{current_title}'，期望包含'小红书创作'")
                    
                    # 添加诊断信息
                    print("= 页面标题诊断信息 =")
                    print(f"当前URL: {driver.current_url}")
                    print("页面源码前500字符:")
                    print(driver.page_source[:500])
                    print("=")
                    return False
        except Exception as e:
            print(f"❌ 加载cookies失败: {str(e)}")
            traceback.print_exc()
            return False
    else:
        print("cookies不存在")
        return False

# 手动登录
def manual_login(driver):
    print("请手动登录小红书")
    driver.get('https://creator.xiaohongshu.com/creator/post')
    
    # 等待用户手动登录 - 通过页面标题判断
    try:
        # 使用更宽松的标题检测
        WebDriverWait(driver, 120).until(
            EC.title_contains("小红书创作")
        )
        print("✅ 登录成功（检测到标题）")
        
        # 保存Cookies
        cookies = driver.get_cookies()
        with open(XIAOHONGSHU_COOKING, 'w') as f:
            f.write(json.dumps(cookies))
        print("📦 Cookies已保存")
        return True
    except TimeoutException:
        # 检查当前标题
        current_title = driver.title
        print(f"❌ 登录超时: 当前标题='{current_title}'，期望包含'小红书创作'")
        
        # 添加诊断信息
        print("= 页面标题诊断信息 =")
        print(f"当前URL: {driver.current_url}")
        print("页面源码前500字符:")
        print(driver.page_source[:500])
        print("=")
        return False

# 计算发布时间（当天20点，如果过了20点则设置为次日20点），并添加时间范围校验
def get_publish_date(user_time=None):
    # 定义时间范围限制（单位：秒）
    MIN_DELAY = 3600  # 1小时
    MAX_DELAY = 14 * 24 * 3600  # 14天
    
    now = datetime.now()
    
    # 尝试解析用户输入的时间
    if user_time:
        try:
            # 支持多种格式：YYYY-MM-DD HH:MM 或 HH:MM
            if len(user_time) == 5:  # HH:MM
                hour, minute = map(int, user_time.split(':'))
                publish_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # 如果时间已过，则设置为第二天
                if publish_time <= now:
                    publish_time += timedelta(days=1)
            else:  # YYYY-MM-DD HH:MM
                publish_time = datetime.strptime(user_time, "%Y-%m-%d %H:%M")
            
            # 校验时间范围
            time_diff = (publish_time - now).total_seconds()
            if time_diff < MIN_DELAY:
                print(f"⚠️ 发布时间太近（需至少1小时后），自动调整为默认时间")
                user_time = None  # 触发使用默认时间
            elif time_diff > MAX_DELAY:
                print(f"⚠️ 发布时间太远（需在14天内），自动调整为默认时间")
                user_time = None  # 触发使用默认时间
            else:
                return publish_time.strftime("%Y-%m-%d %H:%M")
                
        except ValueError:
            print(f"⚠️ 无法解析时间格式: {user_time}，将使用默认时间")
    
    # 默认时间逻辑（确保在1小时-14天内）
    # 计算当天的20点
    today_20 = now.replace(hour=20, minute=0, second=0, microsecond=0)
    # 计算明天的20点
    tomorrow_20 = today_20 + timedelta(days=1)
    
    # 如果当前时间比当天的20点提前至少1小时
    if (today_20 - now).total_seconds() >= MIN_DELAY:
        publish_time = today_20
    # 如果明天20点仍在14天内
    elif (tomorrow_20 - now).total_seconds() <= MAX_DELAY:
        publish_time = tomorrow_20
    else:
        # 否则使用当前时间+1小时（确保在范围内）
        publish_time = now + timedelta(seconds=MIN_DELAY)
    
    # 格式化为字符串 "YYYY-MM-DD HH:MM"
    return publish_time.strftime("%Y-%m-%d %H:%M")

# 等待页面元素加载
def wait_for_element(driver, by, value, timeout=30, scroll_into_view=False):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        
        # 如果需要，滚动元素到可见区域
        if scroll_into_view:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
            
        return element
    except TimeoutException:
        print(f"❌ 等待元素超时: {value}")
        return None

# 点击元素并处理可能的异常
def safe_click(driver, element, timeout=10):
    try:
        # 先滚动元素到可见区域
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)
        
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(element)
        ).click()
        return True
    except (TimeoutException, ElementClickInterceptedException) as e:
        print(f"❌ 点击元素失败: {str(e)}")
        # 尝试使用JavaScript点击
        try:
            driver.execute_script("arguments[0].click();", element)
            print("✅ 使用JS点击成功")
            return True
        except Exception as js_e:
            print(f"❌ JS点击失败: {str(js_e)}")
            return False

# 改进的图片上传检测方法 - 使用新的检测逻辑
def upload_images(driver, image_path, file_names):
    """上传所有图片并等待每张图片上传完成"""
    uploaded_count = 0
    total_files = len(file_names)
    
    # 上传所有图片（不等待）
    print("批量上传所有图片...")
    file_paths = [os.path.abspath(os.path.join(image_path, f)) for f in file_names]
    upload_area = wait_for_element(driver, By.CSS_SELECTOR, "input[type='file']", 10)
    if upload_area:
        upload_area.send_keys("\n".join(file_paths))
    else:
        print("❌ 无法找到上传区域")
        return 0
    
    # 等待所有图片上传完成
    print(f"等待所有 {total_files} 张图片上传完成...")
    start_time = time.time()
    
    # 使用新的检测逻辑 - 检查所有图片容器是否加载完成
    while time.time() - start_time < 30:  # 最多等待30秒
        try:
            # 检查上传失败提示
            if driver.find_elements(By.XPATH, "//*[contains(text(), '上传失败')]"):
                print("❌ 图片上传失败")
                return uploaded_count
            
            # 获取所有图片容器（使用新的选择器）
            image_containers = driver.find_elements(By.CSS_SELECTOR, "div.img-container")
            
            # 检查是否所有图片都已加载（检查图片元素是否可见）
            loaded_count = 0
            for container in image_containers:
                try:
                    # 检查容器内是否有图片元素
                    img_element = container.find_element(By.CSS_SELECTOR, "img.preview")
                    if img_element.is_displayed():
                        loaded_count += 1
                except NoSuchElementException:
                    continue
            
            # 如果所有图片都已加载完成
            if loaded_count == total_files:
                uploaded_count = loaded_count
                print(f"✅ 所有 {total_files} 张图片上传成功")
                return uploaded_count
            else:
                print(f"上传进度: {loaded_count}/{total_files} 张图片")
            
            time.sleep(1)
        except Exception as e:
            print(f"上传检查异常: {str(e)}")
            time.sleep(1)
    
    # 最终检查
    image_containers = driver.find_elements(By.CSS_SELECTOR, "div.img-container")
    loaded_count = 0
    for container in image_containers:
        try:
            img_element = container.find_element(By.CSS_SELECTOR, "img.preview")
            if img_element.is_displayed():
                loaded_count += 1
        except NoSuchElementException:
            continue
    
    if loaded_count == total_files:
        print(f"✅ 所有 {total_files} 张图片上传成功")
    else:
        print(f"⚠️ 图片上传不完整: 上传了 {loaded_count}/{total_files} 张图片")
    
    return loaded_count

# 改进的定时发布功能（添加用户指定时间参数）
def set_schedule_publish(driver, user_time=None):
    try:
        print("设置定时发布...")
        
        # 找到定时发布选项
        schedule_option = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'el-radio__label') and text()='定时发布']"))
        )
        
        # 检查是否已选中
        if "is-checked" not in schedule_option.find_element(By.XPATH, "./ancestor::label").get_attribute("class"):
            safe_click(driver, schedule_option)
            print("✅ 打开定时发布设置")
            
            # 等待时间输入框出现
            time.sleep(1)  # 短暂等待弹出层出现
            
            # 更可靠的时间输入框定位方式
            time_input = None
            time_selectors = [
                (By.CSS_SELECTOR, "input.el-input__inner[placeholder='选择日期和时间']"),
                (By.XPATH, "//input[@placeholder='选择日期和时间']"),
                (By.CSS_SELECTOR, "input[placeholder='请选择日期']"),
                (By.CSS_SELECTOR, "input.date-picker-input")
            ]
            
            for selector in time_selectors:
                try:
                    time_input = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(selector)
                    )
                    if time_input:
                        print(f"✅ 使用定位方式 {selector} 找到时间输入框")
                        break
                except:
                    continue
            
            if time_input:
                publish_time = get_publish_date(user_time)
                
                # 清除现有内容并输入新时间
                time_input.clear()
                for char in publish_time:
                    time_input.send_keys(char)
                    time.sleep(0.05)  # 模拟真实输入
                print(f"✅ 已设置发布时间: {publish_time}")
                
                # 点击确定按钮 - 使用更可靠的定位方式
                confirm_button = None
                confirm_selectors = [
                    (By.XPATH, "//button[.//span[text()='确定']]"),
                    (By.XPATH, "//button[contains(., '确定')]"),
                    (By.CSS_SELECTOR, "button.confirm-button")
                ]
                
                for selector in confirm_selectors:
                    try:
                        confirm_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable(selector)
                        )
                        if confirm_button:
                            print(f"✅ 使用定位方式 {selector} 找到确定按钮")
                            break
                    except:
                        continue
                
                if confirm_button:
                    safe_click(driver, confirm_button)
                    print("✅ 时间设置确认")
                    return True
                else:
                    print("❌ 找不到确定按钮")
            else:
                print("❌ 找不到时间输入框")
        else:
            print("✅ 定时发布已选中")
            return True
    except TimeoutException:
        print("❌ 定时发布设置超时")
    except Exception as e:
        print(f"定时发布设置异常: {str(e)}")
        traceback.print_exc()
    
    return False

# 发布小红书图文 - 使用从JSON文件中获取的内容
def publish_xiaohongshu_image(driver, image_path, content_data, user_time=None):
    try:
        print("=== 开始发布流程 ===")
        
        # 从JSON数据中提取内容
        title = content_data["caption"]["title"]
        body = content_data["caption"]["body"]
        tags = content_data["caption"]["tags"]
        
        print(f"标题: {title}")
        print(f"正文长度: {len(body)} 字符")
        print(f"标签: {', '.join(tags)}")
        
        # 1. 进入发布页面
        print("导航到发布页面")
        driver.get("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=image")
        time.sleep(5)  # 等待页面加载
        
        # 2. 上传图片区域
        print("等待上传区域加载")
        upload_area = wait_for_element(driver, By.CSS_SELECTOR, "input[type='file']", 30)
        if not upload_area:
            print("❌ 无法找到上传区域，退出发布流程")
            # 保存当前页面截图和源码用于调试
            driver.save_screenshot(os.path.join(image_path, "error", "upload_error.png"))
            with open(os.path.join(image_path, "error", "upload_page.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("📸 已保存错误截图和页面源码")
            return False
        
        # 3. 获取所有图片文件
        print("扫描图片目录")
        file_names = [f for f in os.listdir(image_path) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if not file_names:
            print("❌ 没有找到图片文件，退出发布流程")
            return False
        
        print(f"找到 {len(file_names)} 张图片")
        
        # 4. 上传所有图片 - 使用改进的上传函数
        print("开始上传图片...")
        uploaded_count = upload_images(driver, image_path, file_names)
        
        if uploaded_count < len(file_names):
            print(f"⚠️ 图片上传不完整: 上传了 {uploaded_count}/{len(file_names)} 张图片")
            # 继续执行而不是退出，因为可能部分图片已上传成功
        
        # 5. 填写标题 - 优化后的输入方法（使用新定位器）
        print("填写标题...")
        title_input = None
        for attempt in range(3):
            # 使用新的CSS选择器定位标题输入框（根据提供的HTML结构）
            title_input = wait_for_element(
                driver, 
                By.CSS_SELECTOR, 
                "input.d-text[placeholder*='填写标题']", 
                10, 
                scroll_into_view=True
            )
            
            if title_input:
                # 确保输入框可见并可交互
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", title_input)
                time.sleep(0.5)
                
                # 点击聚焦输入框
                safe_click(driver, title_input)
                time.sleep(0.5)
                
                # 清除现有内容（使用组合键全选删除）
                title_input.send_keys(Keys.CONTROL + "a")
                title_input.send_keys(Keys.DELETE)
                time.sleep(0.3)
                
                # 分段输入标题，模拟真人输入
                print(f"输入标题: {title}")
                for char in title:
                    title_input.send_keys(char)
                    time.sleep(0.03)  # 模拟真实输入速度
                
                # 验证标题是否成功输入
                entered_title = title_input.get_attribute("value")
                if entered_title == title:
                    print(f"✅ 标题已设置: {title}")
                    break
                else:
                    print(f"⚠️ 标题验证失败: 预期='{title}'，实际='{entered_title}'")
                    # 重试前等待
                    time.sleep(1)
            else:
                print(f"❌ 第 {attempt+1} 次尝试: 无法找到标题输入框")
                time.sleep(2)
        else:
            print("❌ 多次尝试后仍无法找到标题输入框")
            # 保存当前页面截图和源码用于调试
            driver.save_screenshot(os.path.join(image_path, "error", "title_error.png"))
            with open(os.path.join(image_path, "error", "title_page.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("📸 已保存错误截图和页面源码")
            # 不退出，继续尝试其他操作
        
        # 6. 填写描述和添加标签
        print("填写描述和添加标签...")
        description = wait_for_element(driver, By.CSS_SELECTOR, "div[contenteditable='true']", 15, scroll_into_view=True)
        if description:
            # 点击使编辑器获得焦点
            safe_click(driver, description)
            time.sleep(1)
            
            # 输入正文内容
            print("输入正文内容...")
            for char in body:
                description.send_keys(char)
                time.sleep(0.01)  # 模拟真实输入速度
            
            print("✅ 正文内容已输入")
            
            # 添加关键词标签
            for idx, label in enumerate(tags):
                # 确保标签以#开头
                if not label.startswith("#"):
                    label = "#" + label
                
                # 在输入标签前添加一个空格
                description.send_keys(" " + label)
                print(f"添加标签: {label}")
                time.sleep(1)  # 等待标签建议出现
                
                # 尝试选择标签
                try:
                    # 使用更灵活的XPath定位标签
                    topic_xpath = f"//div[contains(@class, 'suggest-item') and contains(., '{label}')]"
                    topic_item = wait_for_element(driver, By.XPATH, topic_xpath, 2)
                    if topic_item:
                        safe_click(driver, topic_item)
                        print(f"✅ 标签添加成功: {label}")
                    else:
                        # 尝试点击标签本身
                        label_element = wait_for_element(driver, By.XPATH, f"//span[contains(text(), '{label}')]", 1)
                        if label_element:
                            safe_click(driver, label_element)
                            print(f"✅ 直接点击标签: {label}")
                        else:
                            print(f"⚠️ 未找到标签: {label}")
                except Exception as e:
                    print(f"添加标签异常: {str(e)}")
        else:
            print("❌ 无法找到描述编辑器")
        
        # 7. 设置定时发布（使用用户指定的时间）
        set_schedule_publish(driver, user_time)
        
        # 8. 发布笔记
        print("准备发布...")
        
        # 尝试多种定位方式
        publish_button = None
        publish_selectors = [
            (By.XPATH, "//button[.//span[text()='发布']]"),
            (By.XPATH, "//button[contains(., '发布')]"),
            (By.CSS_SELECTOR, "button.publish-button"),
            (By.CSS_SELECTOR, "button[data-testid='publish-button']"),
            (By.XPATH, "//button[contains(@class, 'publish-button')]")
        ]
        
        for selector in publish_selectors:
            try:
                publish_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(selector)
                )
                if publish_button:
                    print(f"✅ 使用定位方式 {selector} 找到发布按钮")
                    break
            except:
                continue
        
        if publish_button:
            # 确保按钮可见
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", publish_button)
            time.sleep(1)
            
            # 尝试点击
            if safe_click(driver, publish_button):
                print("✅ 已点击发布按钮")
            else:
                # 如果点击失败，使用JS点击
                driver.execute_script("arguments[0].click();", publish_button)
                print("✅ 使用JS点击发布按钮")
        else:
            print("❌ 找不到发布按钮")
            # 保存当前页面截图和源码用于调试
            driver.save_screenshot(os.path.join(image_path, "error", "publish_error.png"))
            with open(os.path.join(image_path, "error", "publish_page.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("📸 已保存错误截图和页面源码")
            return False
        
        # 9. 检查发布结果
        print("等待发布结果...")
        result = False
        try:
            # 等待发布成功提示
            success_element = WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), '发布成功')]"))
            )
            print("🎉 发布成功！")
            result = True
        except TimeoutException:
            # 检查各种可能的结果
            if driver.find_elements(By.XPATH, "//*[contains(text(), '已有类似内容')]"):
                print("⚠️ 发布失败: 已有类似内容")
            elif driver.find_elements(By.XPATH, "//*[contains(text(), '发布失败')]"):
                print("⚠️ 发布失败")
            elif driver.find_elements(By.XPATH, "//*[contains(text(), '审核中')]"):
                print("⚠️ 笔记已提交，正在审核中")
                result = True
            else:
                print("⚠️ 发布成功提示未出现，但可能已成功发布")
                result = True
        except Exception as e:
            print(f"发布结果检查异常: {str(e)}")
            traceback.print_exc()
        
        return result
    
    except Exception as e:
        print(f"❌ 发布过程中出错: {str(e)}")
        traceback.print_exc()
        # 尝试截图保存错误信息
        screenshot_path = os.path.join(image_path, "error", "error_screenshot.png")
        driver.save_screenshot(screenshot_path)
        print(f"📸 已保存错误截图: {screenshot_path}")
        return False

# 加载文案内容
def load_content_data():
    try:
        if not os.path.exists(CONTENT_RESULT_FILE):
            print(f"❌ 文案结果文件不存在: {CONTENT_RESULT_FILE}")
            return None
        
        with open(CONTENT_RESULT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if data.get('status') != 'success':
            print(f"❌ 文案生成失败: {data.get('error', '未知错误')}")
            return None
        
        # 确保标签格式正确
        tags = data['caption']['tags']
        processed_tags = []
        for tag in tags:
            # 移除可能的#号前缀
            if tag.startswith('#'):
                tag = tag[1:]
            processed_tags.append(tag)
        
        # 更新标签列表
        data['caption']['tags'] = processed_tags
        
        print(f"✅ 成功加载文案内容")
        print(f"标题: {data['caption']['title']}")
        print(f"标签: {', '.join(processed_tags)}")
        print(f"图片数量: {len(data['images'])}")
        
        return data
    except Exception as e:
        print(f"❌ 加载文案内容失败: {str(e)}")
        traceback.print_exc()
        return None

# 主函数
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="小红书自动发布工具")
    parser.add_argument("--time", type=str, help="手动指定发布时间 (格式: YYYY-MM-DD HH:MM 或 HH:MM)", default=None)
    args = parser.parse_args()
    
    driver = None
    try:
        print("=== 开始小红书自动发布 ===")
        
        # 加载文案内容
        content_data = load_content_data()
        if not content_data:
            print("❌ 无法加载文案内容，程序退出")
            exit(1)
        
        # 初始化浏览器
        print("启动浏览器...")
        driver = get_driver()
        
        # 尝试使用cookies登录
        print("尝试使用Cookies登录...")
        if xiaohongshu_login(driver):
            print("✅ Cookies登录成功")
        else:
            print("Cookies登录失败，尝试手动登录")
            if manual_login(driver):
                print("✅ 手动登录成功")
            else:
                print("❌ 登录失败，程序退出")
                exit(1)
        
        # 发布图文
        image_dir = r"D:\train\xhs\out"
        print(f"图片目录: {image_dir}")
        
        # 检查图片目录是否存在
        if not os.path.exists(image_dir):
            print(f"❌ 图片目录不存在: {image_dir}")
            exit(1)
        
        # 检查图片文件是否存在
        image_files = []
        for img_path in content_data["images"]:
            if os.path.exists(img_path):
                image_files.append(os.path.basename(img_path))
            else:
                print(f"⚠️ 图片不存在: {img_path}")
        
        if not image_files:
            print("❌ 没有有效的图片文件，程序退出")
            exit(1)
        
        print(f"找到 {len(image_files)} 张有效图片")
        print("开始发布流程...")
        
        # 执行发布
        result = publish_xiaohongshu_image(driver, image_dir, content_data, args.time)
        
        if result:
            print("✅ 发布流程完成")
        else:
            print("❌ 发布流程失败")
        
    except Exception as e:
        print(f"❌ 主程序出错: {str(e)}")
        traceback.print_exc()
    finally:
        if driver:
            print("关闭浏览器...")
            # 关闭浏览器前等待一下
            time.sleep(10)  # 增加等待时间，确保发布完成
            driver.quit()
            print("浏览器已关闭")
        print("=== 程序结束 ===")
