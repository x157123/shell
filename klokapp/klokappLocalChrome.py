import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import pyperclip
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
import requests
import subprocess
import os
import socket
from datetime import datetime

evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"
file_lock = threading.Lock()
# 打开浏览器
def __get_page(index, user, retry: int = 0):
    if retry > 0:
        port = 7890
        pass_list = ''
    else:
        mod_value = int(index) % 2300
        port = 51000 + (2300 if mod_value == 0 else mod_value)
        pass_list = "--proxy-bypass-list=localhost;127.0.0.1;192.168.0.0/16;10.0.0.0/8;172.16.0.0/12"
    page = ChromiumPage(
        addr_or_opts=ChromiumOptions()
        .set_browser_path(path=r"/usr/bin/microsoft-edge")
        .add_extension(f"/home/{user}/extensions/signma")
        .set_proxy(f"192.168.3.107:{port}")
        .set_user_data_path(f"/home/{user}/task/edge_data/{index}")
        .set_argument(f'{pass_list}')
        .auto_port()
        .headless(on_off=False))

    page.set.window.max()
    return page

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


# 读取第一行
def read_data_first_file(file_path):
    try:
        with open(file_path, "r") as file:
            # 只读取第一行
            question = file.readline().strip()
        # 返回读取的第一行（如果有内容）
        return question if question else None
    except FileNotFoundError:
        # 如果文件不存在，捕获异常并返回 None
        print(f"文件 {file_path} 不存在")
        return None

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
def __do_task(acc, retry: int = 0):
    page = None
    status = False
    try:
        evm_id = acc['evm_id']
        page = __get_page(index=evm_id, user='lm', retry= retry)

        logger.info(f"登录钱包{evm_id},第{retry}次尝试访问")
        __login_wallet(page=page, evm_id=evm_id)

        url = 'https://klokapp.ai/'
        # if invite_url is not None and invite_url != '':
        #     url = invite_url
        hyperbolic_page = page.new_tab(url=url)
        # 关联钱包
        if __click_ele(page=hyperbolic_page, xpath='x://button[span[text()="More sign-in options"]]', loop=2):
            if __click_ele(page=hyperbolic_page, xpath='x://button[text()="Connect Wallet"]', loop=2):
                __click_ele(page=hyperbolic_page, xpath='x://button//span[contains(text(), "Signma")]', loop=5)
                __handle_signma_popup(page=page, count=1, timeout=15)
        if __click_ele(page=hyperbolic_page, xpath='x://button[text()="Sign in"]', loop=2):
            __handle_signma_popup(page=page, count=1, timeout=15)
        __click_ele(page=hyperbolic_page, xpath='x://button[@aria-label="Close modal"]', loop=2)

        # if invite_url:
        #     logger.info('已有邀请码，不再拷贝')
        # else:
        #     获取邀请码
            # clipboard_text = __get_click_clipboard(page=hyperbolic_page, xpath='x://button[text()="Copy Referral Link"]')
            # if clipboard_text is not None and clipboard_text != '':
            #     文件为空，写入字符串
                # with open('./inviteUrl.txt', 'a', encoding='utf-8') as file:
                #     file.write(clipboard_text)

        __get_ele(page=hyperbolic_page,
                  xpath='x://div[contains(text(), "Total Mira Points")]/following-sibling::div', loop=2, must=True)

        # 提问
        for i in range(12):
            status = __dialogue(page=hyperbolic_page, value=random.choice(questions))
            if status:
                # 已达到次数
                break
        # 获取积分
        integral = __get_ele_value(page=hyperbolic_page,
                                   xpath='x://div[contains(text(), "Total Mira Points")]/following-sibling::div')
        if integral is not None:
            add_log(message=integral, task_name='klokapp', index=evm_id, node_name=local_ip, server_url="http://192.168.0.16:8082")
            with file_lock:
                append_date_to_file(ex_date_file, evm_id)
            status = True
    except Exception as e:
        logger.info(f"未知异常 {acc['evm_id']} ：{e}")
    finally:
        if page is not None:
            try:
                page.quit()
            except Exception as pge:
                logger.info(f"错误")
    return status

def __dialogue(page, value):
    loop_count = 0
    while True:
        try:
            ele = page.ele(locator='x://div[@class="style_loadingDots__NNnij"]')
            if ele:
                time.sleep(2)
            else:
                # 已满次数
                _input = page.ele('x://textarea[@name="message" and @disabled]')
                if _input:
                    return True
                __input_ele_value(page=page, xpath='x://textarea[@name="message"]', value=value)
                __click_ele(page=page, xpath='x://button//img[@alt="Send message"]', loop=1)
                return False
        except Exception as e:
            error = e
            pass
        if loop_count >= 15:
            return False
        loop_count += 1



# 启动容器
def run(accounts, max_workers:int = 5, max_retry:int = 2):
    retry_counts = {acc['evm_id']: 0 for acc in accounts}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        # 提交所有任务，不需要等待每个任务完成
        for acc in accounts:
            future = executor.submit(__do_task, acc, retry_counts[acc['evm_id']])
            futures.append(future)

        # 处理任务结果
        for future in as_completed(futures):
            acc = accounts[futures.index(future)]  # 找到对应的账号
            try:
                success = future.result()
                if not success:
                    retry_counts[acc['evm_id']] += 1
                    if retry_counts[acc['evm_id']] < max_retry:
                        logger.info(f"任务 {acc['evm_id']} 失败，稍后重试...")
                        # 重新提交失败的任务
                        executor.submit(__do_task, acc, retry_counts[acc['evm_id']])
                    else:
                        logger.info(f"账号 {acc['evm_id']} 达到最大重试次数，跳过")
            except Exception as e:
                logger.info(f"未知异常 {acc['evm_id']} ：{e}")

    logger.info("所有任务完成")

def get_date_as_string():
    # 获取当前日期和时间
    now = datetime.now()
    # 将日期格式化为字符串 年-月-日
    date_string = now.strftime("%Y-%m-%d")
    return date_string

def get_local_ip():
    # 获取主机名
    hostname = socket.gethostname()
    # 获取主机的IP地址
    ip_address = socket.gethostbyname(hostname)
    return ip_address


if __name__ == '__main__':
    while True:
        ex_date_file = f"./ex_account_{get_date_as_string()}.txt"
        local_ip = get_local_ip()
        ex_list = read_data_list_file(ex_date_file, check_exists=True)
        account_list = read_data_list_file("./account.txt")
        questions = read_data_list_file("./questions.txt")
        # invite_url = read_data_first_file("./inviteUrl.txt")
        account_data = []
        for account in account_list:
            parts = account.split(",")
            if len(ex_list) > 0 and parts[0] in ex_list:
                logger.info(f'跳过账号：{parts[0]}')
                continue
            account_data.append({
                "evm_id": parts[0],
            })
        # 启动
        print(f'执行账号{len(account_data)}')
        run(accounts=account_data, max_workers=8)
