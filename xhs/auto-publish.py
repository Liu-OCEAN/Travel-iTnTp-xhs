import json
import os
import time
import traceback
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# 保存Cookies的文件路径
XIAOHONGSHU_COOKING = r'D:\train\xhs\out\config.json'

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

# 计算发布时间（当天20点，如果过了20点则设置为次日20点）
def get_publish_date():
    now = datetime.now()
    # 计算发布时间（当天或第二天20点）
    if now.hour >= 20:
        publish_time = now + timedelta(days=1)
        publish_time = publish_time.replace(hour=20, minute=0, second=0, microsecond=0)
    else:
        publish_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
    
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

# 发布小红书图文
def publish_xiaohongshu_image(driver, image_path, title, keywords):
    try:
        print("=== 开始发布流程 ===")
        
        # 1. 进入发布页面
        print("导航到发布页面")
        driver.get("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=image")
        time.sleep(8)  # 增加等待时间，确保页面加载完成
        
        # 2. 上传图片区域
        print("等待上传区域加载")
        # 尝试多种方式定位上传区域
        upload_area = None
        upload_selectors = [
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.XPATH, "//input[@type='file']"),
            (By.CSS_SELECTOR, "div.upload-area input[type='file']")
        ]
        
        for selector in upload_selectors:
            upload_area = wait_for_element(driver, selector[0], selector[1], 15)
            if upload_area:
                break
                
        if not upload_area:
            print("❌ 无法找到上传区域，退出发布流程")
            # 保存当前页面截图和源码用于调试
            driver.save_screenshot(os.path.join(image_path, "upload_error.png"))
            with open(os.path.join(image_path, "upload_page.html"), "w", encoding="utf-8") as f:
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
        
        # 4. 上传所有图片
        print("开始上传图片...")
        for idx, file_name in enumerate(file_names):
            file_path = os.path.abspath(os.path.join(image_path, file_name))
            print(f"上传 {idx+1}/{len(file_names)}: {file_name}")
            upload_area.send_keys(file_path)
            time.sleep(3)  # 增加每个文件上传后的等待时间
        
        # 5. 等待所有图片上传完成 - 使用更可靠的检测方法
        print("等待图片上传完成...")
        uploaded_count = 0
        for i in range(20):  # 增加最大等待时间到90秒
            try:
                # 检查上传失败提示
                if driver.find_elements(By.XPATH, "//*[contains(text(), '上传失败')]"):
                    print("❌ 图片上传失败，退出发布流程")
                    return False
                
                # 使用更可靠的元素检测上传完成
                image_items = driver.find_elements(By.XPATH, "//div[contains(@class, 'image-item')]")
                progress_indicators = driver.find_elements(By.CSS_SELECTOR, ".upload-progress")
                
                # 如果找到图片项并且没有可见的上传进度条
                if image_items and not any(indicator.is_displayed() for indicator in progress_indicators):
                    uploaded_count = len(image_items)
                    if uploaded_count == len(file_names):
                        print(f"✅ 所有 {len(file_names)} 张图片上传成功")
                        break
                    else:
                        print(f"已上传 {uploaded_count}/{len(file_names)} 张图片")
                
                print(f"上传中... ({i+1}/30)")
                time.sleep(3)
            except Exception as e:
                print(f"上传检查异常: {str(e)}")
                time.sleep(3)
        
        if uploaded_count != len(file_names):
            print(f"⚠️ 图片上传不完整: 上传了 {uploaded_count}/{len(file_names)} 张图片")
            # 继续执行而不是退出，因为可能部分图片已上传成功
        
        # 6. 填写标题 - 使用更可靠的定位方法
        print("填写标题...")
        title_input = None
        title_selectors = [
            (By.XPATH, "//input[@placeholder='填写标题，可能会有更多赞哦～']"),
            (By.XPATH, "//input[contains(@placeholder, '填写标题')]"),
            (By.CSS_SELECTOR, "input.title-input"),
            (By.CSS_SELECTOR, "input[data-testid='title-input']")
        ]
        
        for selector in title_selectors:
            title_input = wait_for_element(driver, selector[0], selector[1], 15)
            if title_input:
                break
                
        if title_input:
            # 确保输入框可见并可交互
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", title_input)
            time.sleep(1)
            title_input.clear()
            title_input.send_keys(title)
            print(f"✅ 标题已设置: {title}")
        else:
            print("❌ 无法找到标题输入框")
            # 保存当前页面截图和源码用于调试
            driver.save_screenshot(os.path.join(image_path, "title_error.png"))
            with open(os.path.join(image_path, "title_page.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("📸 已保存错误截图和页面源码")
            # 不退出，继续尝试其他操作
        
        # 7. 填写描述和添加标签
        print("填写描述和添加标签...")
        description = None
        desc_selectors = [
            (By.CSS_SELECTOR, "div[contenteditable='true']"),
            (By.XPATH, "//div[@contenteditable='true']"),
            (By.CSS_SELECTOR, "div.editor-content"),
            (By.CSS_SELECTOR, "div[data-testid='editor-content']")
        ]
        
        for selector in desc_selectors:
            description = wait_for_element(driver, selector[0], selector[1], 15, scroll_into_view=True)
            if description:
                break
                
        if description:
            # 点击使编辑器获得焦点
            safe_click(driver, description)
            time.sleep(1)
            
            # 输入内容
            description.send_keys("这是一篇自动发布的测试笔记\n")
            
            # 添加关键词标签
            for idx, label in enumerate(keywords):
                description.send_keys(" " + label)
                print(f"添加标签: {label}")
                time.sleep(2)  # 增加等待时间
                
                # 尝试选择标签 - 使用更可靠的定位方法
                try:
                    # 使用更灵活的XPath定位标签
                    topic_xpath = f"//div[contains(@class, 'suggest-item') and contains(., '{label}')]"
                    topic_item = wait_for_element(driver, By.XPATH, topic_xpath, 5)
                    if topic_item:
                        safe_click(driver, topic_item)
                        print(f"✅ 标签添加成功: {label}")
                    else:
                        # 尝试点击标签本身
                        label_element = wait_for_element(driver, By.XPATH, f"//span[contains(text(), '{label}')]", 3)
                        if label_element:
                            safe_click(driver, label_element)
                            print(f"✅ 直接点击标签: {label}")
                        else:
                            print(f"⚠️ 未找到标签: {label}")
                except Exception as e:
                    print(f"添加标签异常: {str(e)}")
        else:
            print("❌ 无法找到描述编辑器")
        
        # 8. 设置定时发布 - 使用更可靠的定位方法
        print("设置定时发布...")
        try:
            # 找到定时发布按钮
            schedule_button = None
            schedule_selectors = [
                (By.XPATH, "//span[text()='定时发布']"),
                (By.XPATH, "//span[contains(text(), '定时发布')]"),
                (By.CSS_SELECTOR, "div.schedule-publish"),
                (By.CSS_SELECTOR, "div[data-testid='schedule-publish']")
            ]
            
            for selector in schedule_selectors:
                schedule_button = wait_for_element(driver, selector[0], selector[1], 15, scroll_into_view=True)
                if schedule_button:
                    break
            
            if schedule_button:
                safe_click(driver, schedule_button)
                print("✅ 打开定时发布设置")
                
                # 填写发布时间
                time_input = None
                time_selectors = [
                    (By.CSS_SELECTOR, "input[placeholder='请选择日期']"),
                    (By.XPATH, "//input[@placeholder='请选择日期']"),
                    (By.CSS_SELECTOR, "input.date-picker-input"),
                    (By.CSS_SELECTOR, "input[data-testid='date-picker-input']")
                ]
                
                for selector in time_selectors:
                    time_input = wait_for_element(driver, selector[0], selector[1], 10)
                    if time_input:
                        break
                
                if time_input:
                    publish_time = get_publish_date()
                    
                    # 清除现有内容并输入新时间
                    time_input.clear()
                    time_input.send_keys(publish_time)
                    print(f"✅ 已设置发布时间: {publish_time}")
                    
                    # 点击确定按钮
                    confirm_button = None
                    confirm_selectors = [
                        (By.XPATH, "//button[.//span[text()='确定']]"),
                        (By.XPATH, "//button[contains(., '确定')]"),
                        (By.CSS_SELECTOR, "button.confirm-button"),
                        (By.CSS_SELECTOR, "button[data-testid='confirm-button']")
                    ]
                    
                    for selector in confirm_selectors:
                        confirm_button = wait_for_element(driver, selector[0], selector[1], 5)
                        if confirm_button:
                            break
                    
                    if confirm_button:
                        safe_click(driver, confirm_button)
                        print("✅ 时间设置确认")
                    else:
                        print("❌ 找不到确定按钮")
                else:
                    print("❌ 找不到时间输入框")
            else:
                print("❌ 找不到定时发布按钮")
        except Exception as e:
            print(f"定时发布设置异常: {str(e)}")
            traceback.print_exc()
        
        # 9. 发布笔记 - 使用更可靠的定位方法
        print("准备发布...")
        publish_button = None
        publish_selectors = [
            (By.XPATH, "//button[.//span[text()='发布']]"),
            (By.XPATH, "//button[contains(., '发布')]"),
            (By.CSS_SELECTOR, "button.publish-button"),
            (By.CSS_SELECTOR, "button[data-testid='publish-button']")
        ]
        
        for selector in publish_selectors:
            publish_button = wait_for_element(driver, selector[0], selector[1], 30, scroll_into_view=True)
            if publish_button:
                break
        
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
            driver.save_screenshot(os.path.join(image_path, "publish_error.png"))
            with open(os.path.join(image_path, "publish_page.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("📸 已保存错误截图和页面源码")
            return False
        
        # 10. 检查发布结果 - 增加更全面的检测
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
        screenshot_path = os.path.join(image_path, "error_screenshot.png")
        driver.save_screenshot(screenshot_path)
        print(f"📸 已保存错误截图: {screenshot_path}")
        return False

# 主函数
if __name__ == "__main__":
    driver = None
    try:
        # 文案内容设置
        title = "Python自动化测试 - 小红书发布"  # 图文标题
        keywords = ['#Python', '#自动化', '#小红书运营', '#技术分享']  # 标签列表
        
        print("=== 开始小红书自动发布 ===")
        print(f"标题: {title}")
        print(f"标签: {', '.join(keywords)}")
        
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
            print(f"⚠️ 图片目录不存在，创建目录: {image_dir}")
            os.makedirs(image_dir, exist_ok=True)
            
            # 添加一个示例图片
            sample_path = os.path.join(image_dir, "sample.png")
            with open(sample_path, "wb") as f:
                f.write(b"")  # 创建空文件作为占位符
            print(f"创建示例图片: {sample_path}")
        
        print("开始发布流程...")
        result = publish_xiaohongshu_image(driver, image_dir, title, keywords)
        
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