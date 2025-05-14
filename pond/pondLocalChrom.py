import time
import threading
import concurrent.futures
import random
import pyperclip
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
import requests
import subprocess
import socket
from datetime import datetime
import os
import platform
import concurrent.futures

evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"
file_lock = threading.Lock()


# 打开浏览器
def __get_page(evm_id):
    if platform.system().lower() == "windows":
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_paths(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
            .set_user_data_path(r"f:\tmp\rarible\0" + evm_id)
            .add_extension(r"C:\Users\liulei\Desktop\fsdownload\signma")
            .set_local_port(54443)
            .headless(on_off=False))
    else:
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_paths(r"/usr/bin/google-chrome")
            .add_extension(f"/home/lm/extensions/signma")
            .set_user_data_path(f"/home/lm/task/chrome_data/{evm_id}")
            .set_proxy(f"192.168.3.107:7890")
            .set_local_port(int(evm_id[-4:]) + 21000)
            .headless(on_off=False))
        page.set.window.max()
    if platform.system().lower() == "windows":
        time.sleep(1)
        __start_wallet(page=page)
    return page


def __start_wallet(page):
    if platform.system().lower() == "windows":
        set_page = page.new_tab(f'chrome://extensions/')
        els = (set_page.ele("x://html/body/extensions-manager").shadow_root.ele('x://*[@id="viewManager"]')
               .ele('x://*[@id="items-list"]')
               .shadow_root.ele(f'x://*[@id="{evm_ext_id}"]')
               .shadow_root.ele('x://cr-toggle[@id="enableToggle"]'))
        if els and els.attr('aria-pressed') == 'false':
            with file_lock:
                els.click()
                time.sleep(1)
                import pyautogui
                pyautogui.press('enter')
        set_page.close()


# 获取剪切板数据
def __get_click_clipboard(page, xpath, loop: int = 5, must: bool = False):
    pyperclip.copy('')
    time.sleep(1)
    __click_ele(page=page, xpath=xpath, loop=loop, must=must)
    time.sleep(1)
    clipboard_text = pyperclip.paste().strip()
    logger.info(f"输出剪切板结果：{clipboard_text}")
    return clipboard_text


# 登录钱包
def __login_wallet(page, evm_id):
    time.sleep(3)
    wallet_url = f"chrome-extension://{evm_ext_id}/tab.html#/onboarding"
    xpath = "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
    if len(page.get_tabs(title="Signma")) > 0 and page.tabs_count >= 2:
        time.sleep(3)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for pop_tab in all_tabs:
            # logger.info(f"网页地址：{pop_tab.url}")
            if pop_tab.url == wallet_url:
                if __input_ele_value(page=pop_tab, xpath=xpath, value=evm_id):
                    time.sleep(1)
                    __click_ele(page=pop_tab, xpath="tag:button@@id=existingWallet")
    else:
        wallet_tab = page.new_tab(url=wallet_url)
        __input_ele_value(page=wallet_tab, xpath=xpath, value=evm_id)
        __click_ele(page=wallet_tab, xpath="tag:button@@id=existingWallet")
        time.sleep(1)


# 获取元素
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False):
    loop_count = 1
    while True:
        # logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            # logger.info(f'点击按钮{xpath}:{loop_count}')
            txt = page.ele(locator=xpath)
            if txt:
                return page.ele(locator=xpath)
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return None
        loop_count += 1


# 获取元素内容
def __get_ele_value(page, xpath: str = '', loop: int = 5, must: bool = False):
    try:
        # logger.info(f'获取元素{xpath}')
        _ele = __get_ele(page=page, xpath=xpath, loop=loop, must=must)
        if _ele is not None:
            if _ele:
                return _ele.text
    except Exception as e:
        error = e
        pass
    return None


# 点击元素
def __click_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
                by_js: bool = False,
                find_all: bool = False,
                index: int = -1) -> bool:
    loop_count = 1
    while True:
        # logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                if by_js:
                    page.ele(locator=xpath).click()
                else:
                    page.ele(locator=xpath).click(by_js=None)
            else:
                page.eles(locator=xpath)[index].click(by_js=None)
            # logger.info(f'点击按钮{xpath}:{loop_count}')
            return True
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return False
        loop_count += 1


def __click_verify_ele(page, window, xpath: str = '', loop: int = 5, must: bool = False, by_jd: bool = True,
                       find_all: bool = False,
                       index: int = -1) -> int:
    loop_count = 1
    while True:
        logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                # logger.info(f'点击按钮{xpath}:{loop_count}')
                page.ele(locator=xpath).click(by_js=None)
            else:
                page.eles(locator=xpath)[index].click(by_js=None)
            break
        except Exception as e:
            error = e
            pass

        try:
            logger.info(f'点击{xpath}:{loop_count}')
            cf_verify(page, 789 + random.randint(1, 6), 531 + random.randint(1, 6), window)
            # cf_verify(page, 543 + random.randint(1, 6), 649 + random.randint(1, 6), window)
        except Exception as e:
            error = e
            pass

        if loop_count >= loop:
            # logger.info(f'---> {xpath} 无法找到元素。。。', str(error)[:100])
            if must:
                # page.quit()
                raise Exception(f'未找到元素:{xpath}')
            return 0
        loop_count += 1
        # time.sleep(1)
    return 1


def cf_verify(window_page, x, y, window):
    with file_lock:
        logger.info(f'窗口 {window} xdotool 开始')
        if platform.system().lower() != "windows":
            display = f':{window}'
            os.environ['DISPLAY'] = display
            import pyautogui
            pyautogui.moveTo(x, y)  # 需要你先手动量好按钮在屏幕上的位置
            pyautogui.click()
        else:
            import pyautogui
            pyautogui.moveTo(x, y)  # 需要你先手动量好按钮在屏幕上的位置
            pyautogui.click()
        logger.info(f'点击{window}:cf结束')
        # env = os.environ.copy()
        # env['DISPLAY'] = f':{window}'
        # logger.info(f'窗口 {window} xdotool 执行')
        # subprocess.run(
        #     ['xdotool', 'mousemove', '--sync', str(x), str(y), 'click', '1'],
        #     env=env,
        #     check=True
        # )
        # logger.info(f'窗口 {window} xdotool 点击完成')
    time.sleep(5)

# 输入值
def __input_ele_value(page, xpath: str = '', value: str = '', loop: int = 5, must: bool = False,
                      find_all: bool = False,
                      index: int = -1) -> bool:
    loop_count = 0
    while True:
        try:
            if not find_all:
                # logger.info(f'输入{value}')
                page.ele(locator=xpath).input(value, clear=True)
            else:
                page.eles(locator=xpath)[index].input(value, clear=True)
            return True
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return False
        loop_count += 1


# 窗口管理   __handle_signma_popup(page=page, count=2, timeout=30)
def __handle_signma_popup(page, count: int = 1, timeout: int = 15, must: bool = False):
    """处理 Signma 弹窗，遍历所有 tab 页签"""
    start_time = time.time()
    _count = 0
    while time.time() - start_time < timeout:
        time.sleep(2)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for tab in all_tabs:
            if '/popup.html?page=%2Fdapp-permission' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(page=tab, xpath='x://button[@id="grantPermission"]')
                time.sleep(2)

            elif '/notification.html#connect' in tab.url:
                __click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                __click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                time.sleep(2)

            elif '/notification.html#confirmation' in tab.url:
                __click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                time.sleep(2)
                __click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                time.sleep(2)

            elif '/notification.html#confirm-transaction' in tab.url:
                __click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                time.sleep(2)

            elif '/popup.html?page=%2Fsign-transaction' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)

            elif '/popup.html?page=%2Fsign-data' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)

            elif 'popup.html?page=%2Fpersonal-sign' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)

            elif ('&tab=%2Fadd-evm-chain' in tab.url) or ('/popup.html?requestId=' in tab.url):
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(page=tab, xpath='x://button[@id="addNewChain"]')
                time.sleep(2)

            elif 'popout.html?windowId=backpack' in tab.url:
                __click_ele(page=tab, xpath='x://div/span[text()="确认"]')
                time.sleep(2)
            elif f'{evm_ext_id}' in tab.url:
                tab.close()  # 关闭符合条件的 tab 页签
            # 如果处理了足够数量的 tab，则退出
            if _count >= count:
                return True
    # 如果处理的 tab 数量小于指定数量且 must 为 True，则抛出异常
    if _count < count and must:
        raise Exception(f'未处理指定数量的窗口')
    return False


# 获取邮箱 验证码code
def __get_email_code(page, xpath):
    email_page = page.new_tab(url='https://mail.dmail.ai/inbox')
    # 通过小狐狸钱包打开狗头钱包
    if __click_ele(page=email_page, xpath='x://span[text()="MetaMask"]', loop=20):
        __handle_signma_popup(page=page, count=1, timeout=15)
    code = None
    loop_count = 0

    # 首次进入邮箱
    if __click_ele(page=email_page, xpath='x://a[text()="Next step"]', loop=2):
        __click_ele(page=email_page, xpath='x://a[text()="Launch"]')
        __click_ele(page=email_page, xpath='x://div[@data-title="Setting"]')
    if __click_ele(page=email_page, xpath='x://a[text()="Next"]', loop=2):
        __click_ele(page=email_page, xpath='x://a[text()="Finish"]')

    # 多尝试几次
    while True:
        try:
            __click_ele(email_page, xpath='x://div[contains(@class, "icon-refresh")]', loop=20)
            __click_ele(email_page, xpath='x://div[contains(@class,"sc-eDPEul")]//ul/li[1]', loop=40)
            # 读取验证码
            code = __get_ele_value(page=email_page, xpath=xpath, loop=20)
            # 删除读取到的验证邮箱
            if code is not None:
                __click_ele(email_page, xpath='x://div[@data-title="trash"]')
                time.sleep(3)
        except Exception as e:
            logger.error(f'error ==> {e}')
        if loop_count >= 5:
            break
        if code is None:
            loop_count += 1
            continue  # 跳到下一次循环
        else:
            break
    # 关闭邮箱页面
    email_page.close()
    return code


# 读取txt文件
def read_data_list_file(file_path, check_exists=True):
    # 如果需要检查文件是否存在，且文件不存在，则创建文件
    if check_exists and not os.path.exists(file_path):
        with open(file_path, 'w'):  # 创建文件并关闭
            pass  # 创建空文件
    with open(file_path, "r") as file:
        questions = file.readlines()
    # 过滤掉空白行并去除每行末尾的换行符
    return [question.strip() for question in questions if question.strip()]


# 文件追加
def append_date_to_file(file_path, data_str):
    with open(file_path, 'a') as file:
        file.write(data_str + '\n')


# 添加消息
def add_log(message: str, task_name: str, index: str, node_name: str, server_url: str):
    url = "{}/service_route?service_name=signma_log&&task={}&&chain_id={}&&index={}&&msg={}"
    logger.info(url.format(server_url, task_name, node_name, index, message))
    requests.get(url.format(server_url, task_name, node_name, index, message), verify=False)


# 通过端口杀掉浏览器
def kill_edge_port(port):
    # 使用 lsof 查找指定端口的进程
    try:
        # 查找使用指定端口的进程 ID（PID）
        command = f"lsof -i :{port} -t"
        pid = subprocess.check_output(command, shell=True).decode().strip()

        if pid:
            # 杀掉进程
            kill_command = f"kill -9 {pid}"
            subprocess.run(kill_command, shell=True)
            print(f"已终止端口 {port} 上的进程，PID: {pid}")
        else:
            print(f"没有找到占用端口 {port} 的进程")
    except subprocess.CalledProcessError as e:
        print(f"执行命令时出错: {e}")


# 启动任务
def __do_task(data_list, window: int = 0):
    if len(data_list) <= 0:
        return

    # 设置指定端口
    logger.info(f'运行窗口{window}:{len(data_list)}')

    for acc in data_list:
        page = None
        status = False
        try:
            evm_id = acc['evm_id']
            email_address = acc['email_address']
            password = acc['password']

            with file_lock:
                if platform.system().lower() != "windows":
                    display = f':{window}'
                    os.environ['DISPLAY'] = display
                    logger.info(f'执行账号{window}:{evm_id}')
                page = __get_page(evm_id=evm_id)

            pond_url = 'https://cryptopond.xyz/points?tab=idea'
            pond_page = page.new_tab(url=pond_url)
            __handle_signma_popup(page=page, count=0)
            if __get_ele(page=pond_page, xpath='x://button[text()="Sign in"]', loop=2):
                if password is None or password == "" or password == "None" or password == "000000":
                    logger.info(f"登录钱包{evm_id}")
                    __login_wallet(page=page, evm_id=evm_id)

                    if password == '000000':
                        __click_ele(page=pond_page, xpath='x://button[text()="Sign in"]')
                        __click_ele(page=pond_page, xpath='x://p[text()="Forgot?"]')
                        __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter email"]',
                                          value=email_address)
                        __click_verify_ele(page=pond_page, window=window,
                                           xpath='x://button[text()="Send email" and contains(@class, "chakra-button css-16ek3z6") and not(@disabled)]',
                                           loop=10)
                    else:
                        __click_ele(page=pond_page, xpath='x://button[text()="Sign up"]')
                        __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter email"]',
                                          value=email_address)
                        __click_ele(page=pond_page, xpath='x://span[contains(@class, "chakra-checkbox__control")]')
                        __click_verify_ele(page=pond_page, window=window,
                                           xpath='x://button[text()="Sign up" and contains(@class, "chakra-button css-16ek3z6") and not(@disabled)]',
                                           loop=10)
                        # 判断邮箱是否已经注册 再次通过修改密码
                        already = __get_ele(page=pond_page, xpath='x://div[text()="Email already registered"]', loop=3)
                        if already is not None:
                            pond_page.get(url=pond_url)
                            __click_ele(page=pond_page, xpath='x://button[text()="Sign in"]')
                            __click_ele(page=pond_page, xpath='x://p[text()="Forgot?"]')
                            __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter email"]',
                                              value=email_address)
                            __click_verify_ele(page=pond_page, window=window,
                                               xpath='x://button[text()="Send email" and not(@disabled)]',
                                               loop=10)

                    data = __get_email_code(page, 'x://p[contains(text(),"Your verification code is: ")]')
                    if data is not None:
                        code = data.split(':')[-1].strip()
                        __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter code"]', value=code)
                        __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter password"]',
                                          value="yhy023r@23h34a7")
                        if password == '000000':
                            logger.info("重置密码成功")
                            __click_ele(page=pond_page, xpath='x://button[text()="Reset password"]')
                        else:
                            print("注册成功")
                            __click_ele(page=pond_page, xpath='x://button[text()="Join Pond"]')
                        password = "yhy023r@23h34a7"
                    else:
                        logger.info('有效错误')
                    pond_page.get(url=pond_url)

                if __click_ele(page=pond_page, xpath='x://button[text()="Sign in"]', loop=2):
                    __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter email"]',
                                      value=email_address)
                    __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter password"]', value=password)
                    __click_verify_ele(page=pond_page, window=window,
                                       xpath='x://button[text()="Sign in" and contains(@class, "chakra-button css-16ek3z6") and not(@disabled)]',
                                       loop=10)
                    if __click_ele(page=pond_page, xpath='x://button[text()=" Continue"]', loop=2):
                        __click_ele(page=pond_page, xpath='x://button[text()=" Continue"]', loop=3)
                        __click_ele(page=pond_page, xpath='x://button[text()="Got It"]', loop=3)

            # 开始任务

            # 任务1   Common
            __click_ele(page=pond_page, xpath='x://p[text()="Common"]', must=True)
            if __click_ele(page=pond_page,
                           xpath='x://span[text()="Complete Profile Information"]/ancestor::div[2]/following-sibling::div//button',
                           loop=1):
                __click_ele(page=pond_page, xpath='x://button[text()="Save"]')

            if __click_ele(page=pond_page,
                           xpath='x://span[text()="Add Profile Picture"]/ancestor::div[2]/following-sibling::div//button', loop=1):
                # 随机设置要上传的文件路径
                time.sleep(5)
                pond_page.set.upload_files(random.choice(image_files))
                # 点击触发文件选择框按钮
                div_element = pond_page.ele('x://button[contains(normalize-space(.), "Upload new image")]')
                if div_element:
                    div_element.click()
                    # 等待路径填入
                    pond_page.wait.upload_paths_inputted()
                    time.sleep(2)
                    __click_ele(page=pond_page, xpath='x://button[text()="Save"]')

                time.sleep(3)
                pond_page.get(url=pond_url)

            # 任务 2  idea Propose an Idea
            __click_ele(page=pond_page, xpath='x://p[text()="Idea"]')
            go_in = pond_page.ele('x://span[text()="Propose an Idea"]/ancestor::div[2]/following-sibling::div//button')
            if go_in:
                __click_ele(page=pond_page,
                            xpath='x://span[text()="Propose an Idea"]/ancestor::div[2]/following-sibling::div//button')
                __input_ele_value(page=pond_page, xpath='x://input[@placeholder="Enter the title of your model idea"]',
                                  value="SmartFormAI: AI-Powered Intelligent Form Autofill and Data Extraction")
                __input_ele_value(page=pond_page,
                                  xpath='x://textarea[@placeholder="Enter a brief summary of your model idea"]',
                                  value="SmartFormAI is an AI model designed to automate form-filling processes and extract structured data from various document types. Leveraging natural language processing (NLP) and computer vision, this model can understand and interpret input fields, extract relevant user information, and accurately populate forms across web and desktop applications. The model is particularly useful for automating repetitive form submissions, enhancing data entry efficiency, and integrating with enterprise-level workflows.")
                __click_ele(page=pond_page, xpath='x://div[@class="ProseMirror bn-editor bn-default-styles"]')
                pond_page.actions.type(
                    "SmartFormAI is an AI model that combines OCR (Optical Character Recognition), NLP, and deep learning-based entity recognition to automatically fill out forms and extract structured information. The model follows these key steps:")
                pond_page.actions.type("Document and Form Detection:")
                pond_page.actions.type(
                    "Uses computer vision to identify form structures in images, PDFs, or digital forms.")
                pond_page.actions.type(
                    "Recognizes input fields, labels, and section titles using OCR and layout analysis.")
                pond_page.actions.type("Data Extraction and Interpretation:")
                pond_page.actions.type(
                    "Analyzes provided text (e.g., user profile, ID cards, invoices) to extract relevant details.")
                pond_page.actions.type(
                    "Uses NLP-based Named Entity Recognition (NER) to classify fields (e.g., name, address, email, etc.).")
                pond_page.actions.type("Intelligent Form-Filling:")
                pond_page.actions.type("Maps extracted data to corresponding fields using contextual understanding.")
                pond_page.actions.type("Auto-fills fields dynamically, ensuring accuracy and format compliance.")
                pond_page.actions.type("Supports learning from user interactions to improve accuracy over time.")
                pond_page.actions.type("Integration & Automation:")
                __click_ele(page=pond_page, xpath='x://button[text()="Save"]')
                time.sleep(6)
                pond_page.get(url=pond_url)

            # 任务3  idea Propose an Idea
            __click_ele(page=pond_page, xpath='x://p[text()="Idea"]')
            if __click_ele(page=pond_page,
                           xpath='x://span[text()="Vote on an Idea"]/ancestor::div[2]/following-sibling::div//button',
                           loop=1):
                index = random.randint(2, 7)
                pond_page.get(url=f"https://cryptopond.xyz/ideas?page={index}")
                __click_ele(page=pond_page, xpath='x://div[contains(@class, "css-1mfyor6")]', loop=10)
                pond_page.get(url=pond_url)

            # 获取积分
            time.sleep(5)
            integral = __get_ele_value(page=pond_page,
                                       xpath='x://p[contains(@class, "chakra-text") and contains(@class, "css-c1o5sq")]')
            if integral is not None:
                add_log(message=integral, task_name='pond', index=evm_id, node_name=local_ip,
                        server_url="http://192.168.0.16:8082")
                with file_lock:
                    append_date_to_file(ex_date_file, evm_id)
        except Exception as e:
            logger.info(f"未知异常 {acc['evm_id']} ：{e}")
        finally:
            if page is not None:
                try:
                    page.quit()
                except Exception as pge:
                    logger.info(f"错误")


# 启动容器
def run(data, max_workers: int = 3):
    # 将数据分配给 max_workers 个进程
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:

        # 动态计算每个进程应该处理的数据量
        chunk_size = len(data) // max_workers
        remainder = len(data) % max_workers  # 计算余数，分配到前面的进程中

        # 创建任务，每个进程处理不同的数据部分
        start_idx = 0
        futures = []

        for i in range(max_workers):
            end_idx = start_idx + chunk_size + (1 if i < remainder else 0)  # 余数分配到前面进程
            sub_data = data[start_idx:end_idx]

            # 提交任务，注意 ProcessPoolExecutor 提交的是进程，而不是线程
            futures.append(executor.submit(__do_task, sub_data, i + 1))

            start_idx = end_idx

        # 等待所有任务完成
        concurrent.futures.wait(futures)

    print("所有任务完成")


def get_date_as_string():
    # 获取当前日期和时间
    now = datetime.now()
    # 将日期格式化为字符串 年-月-日
    date_string = now.strftime("%Y-%m-%d")
    return date_string


# 获取文件名称
def get_all_files_in_directory(directory):
    file_list = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            # Add the full path of the file to the list
            file_list.append(os.path.join(root, file))

    return file_list


def get_local_ip():
    # 获取主机名
    hostname = socket.gethostname()
    # 获取主机的IP地址
    ip_address = socket.gethostbyname(hostname)
    return '192.168.3.137'


if __name__ == '__main__':
    while True:
        ex_date_file = f"./log/ex_account_{get_date_as_string()}.txt"
        local_ip = get_local_ip()
        ex_list = read_data_list_file(ex_date_file, check_exists=True)
        account_list = read_data_list_file("./account.txt")
        # 上传图片文件夹
        image_files = get_all_files_in_directory("/home/lm/shared/avatar/img")
        account_data = []
        for account in account_list:
            parts = account.split(",")
            if len(ex_list) > 0 and parts[0] in ex_list:
                logger.info(f'跳过账号：{parts[0]}')
                continue
            account_data.append({
                "evm_id": parts[0],
                "email_address": parts[1],
                "password": parts[2],
            })
        # 启动
        if len(account_data) > 0:
            run(data=account_data, max_workers=15)

        logger.info('等待一小时')
        time.sleep(3600)
