import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pyperclip
import requests
from decimal import Decimal
import platform
import os
from DrissionPage._pages.chromium_page import ChromiumPage
import time
from DrissionPage._configs.chromium_options import ChromiumOptions
import paho.mqtt.client as mqtt
import json
import argparse
from loguru import logger
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import random
from datetime import datetime


evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"
file_lock = threading.Lock()


# 打开浏览器
def __get_page(evm_id, user, retry: int = 0):
    if retry > 0:
        port = 7890
        pass_list = ''
    else:
        mod_value = int(evm_id) % 2300
        port = 51000 + (2300 if mod_value == 0 else mod_value)
        pass_list = "--proxy-bypass-list=localhost;127.0.0.1;192.168.0.0/16;10.0.0.0/8;172.16.0.0/12"
    if platform.system().lower() == "windows":
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_paths(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
            .set_user_data_path(r"D:\tmp\rarible\0")
            .set_local_port(55443)
            .headless(on_off=False))
    else:
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_paths(r"/opt/google/chrome/google-chrome")
            .add_extension(f"/home/ubuntu/extensions/chrome-cloud")
            .set_user_data_path(f"/home/ubuntu/task/chrome_data/{evm_id}")
            # .set_proxy(f"192.168.3.107:7890")
            .set_local_port(int(evm_id[-4:]) + 3000)
            .headless(on_off=False))
    page.set.window.max()
    return page


# 获取剪切板数据
def __get_click_clipboard(page, xpath, loop: int = 5, must: bool = False,
                          find_all: bool = False,
                          index: int = -1):
    pyperclip.copy('')
    time.sleep(1)
    __click_ele(page=page, xpath=xpath, loop=loop, must=must, find_all=find_all, index=index)
    time.sleep(1)
    clipboard_text = pyperclip.paste().strip()
    # logger.info(f"输出剪切板结果：{clipboard_text}")
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
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
              find_all: bool = False,
              index: int = -1):
    loop_count = 1
    while True:
        # logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                # logger.info(f'查找元素{xpath}:{loop_count}')
                txt = page.ele(locator=xpath)
                if txt:
                    return txt
            else:
                # logger.info(f'查找元素{xpath}:{loop_count}:{find_all}:{index}')
                txt = page.eles(locator=xpath)[index]
                if txt:
                    return txt
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return None
        loop_count += 1

# 获取元素
def __get_ele_s(page, xpath: str = '', loop: int = 5, must: bool = False):
    loop_count = 1
    while True:
        # logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            ele = page.eles(locator=xpath)
            if ele:
                return ele
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return None
        loop_count += 1


# 获取元素内容
def __get_ele_value(page, xpath: str = '', loop: int = 5, must: bool = False,
                    find_all: bool = False,
                    index: int = -1):
    try:
        logger.info(f'获取元素数据{xpath}')
        _ele = __get_ele(page=page, xpath=xpath, loop=loop, must=must, find_all=find_all, index=index)
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
        logger.info(f'查找元素{xpath}:{loop_count}')
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
def __get_email_code(page, xpath, evm_addr):
    email_page = page.new_tab(url='https://mail.dmail.ai/inbox')
    code = None
    try:
        # 通过小狐狸钱包打开狗头钱包
        loop_count = 0
        if __get_ele(email_page, xpath=f"x://div[@title='{evm_addr}']", loop=2):
            logger.info('已登录邮箱')
        else:
            if __click_ele(page=email_page, xpath='x://span[text()="MetaMask"]', loop=10):
                __handle_signma_popup(page=page, count=1, timeout=60)
        # 首次进入邮箱
        if __click_ele(page=email_page, xpath='x://a[text()="Next step"]', loop=5):
            __click_ele(page=email_page, xpath='x://a[text()="Launch"]')
            __click_ele(page=email_page, xpath='x://div[@data-title="Setting"]')
        if __click_ele(page=email_page, xpath='x://a[text()="Next"]', loop=5):
            __click_ele(page=email_page, xpath='x://a[text()="Finish"]')

        # 多尝试几次
        while True:
            try:
                __click_ele(email_page, xpath='x://div[contains(@class, "icon-refresh")]', loop=20, must=True)
                __click_ele(email_page, xpath='x://div[contains(@class,"sc-eDPEul")]//ul/li[1]', loop=40, must=True)
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
    except Exception as e:
        logger.error(f'error ==> {e}')
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


# 获取文件名称
def get_all_files_in_directory(directory):
    file_list = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            # Add the full path of the file to the list
            file_list.append(os.path.join(root, file))

    return file_list


def get_wallet(evm_addr):
    # 请求接口
    url = f"https://rari.calderaexplorer.xyz/api/v2/addresses/{evm_addr}"
    response = requests.get(url)

    # 检查请求是否成功
    if response.status_code == 200:
        data = response.json()  # 将响应的 JSON 数据解析为字典
        # 获取前两行数据
        # 假设虚拟货币有 18 位小数
        decimal_places = 18
        conversion_factor = 10 ** decimal_places
        actual_fee_value = Decimal(int(data["coin_balance"])) / Decimal(conversion_factor)
        return str(actual_fee_value)


# 获取转账记录
def get_log(evm_addr, num: int = 1):
    # 请求接口
    url = f"https://rari.calderaexplorer.xyz/api/v2/addresses/{evm_addr}/transactions"
    response = requests.get(url)
    # 检查请求是否成功
    if response.status_code == 200:
        data = response.json()  # 将响应的 JSON 数据解析为字典
        logger.info(data)
        # 获取前两行数据
        items = data.get("items", [])[:num]  # 取前两项数据
        # 假设虚拟货币有 18 位小数
        decimal_places = 18
        conversion_factor = 10 ** decimal_places
        info = {
            "fee_1": None,
            "fee_2": None,
            "gas_all": None,
            "gas_time": None
        }
        actual_fee_value_1 = None
        if num >= 1:
            # 将 fee_value 转换为实际的货币数值
            actual_fee_value_1 = Decimal(int(items[0]["fee"]["value"])) / Decimal(conversion_factor)
            # 去除末尾的零
            info['fee_1'] = str(actual_fee_value_1.normalize())
            info['gas_all'] = info['fee_1']
        if num >= 2:
            # 将 fee_value 转换为实际的货币数值
            actual_fee_value_2 = Decimal(int(items[1]["fee"]["value"])) / Decimal(conversion_factor)
            # 去除末尾的零
            info['fee_2'] = str(actual_fee_value_2.normalize())
            info['gas_all'] = str(actual_fee_value_1 + actual_fee_value_2)

        # 获取最终钱包
        info['end'] = get_wallet(evm_addr)
        return info
    else:
        print(f"请求失败，状态码: {response.status_code}")
        return None


# 随机金额
def adjust_value(input_value: str) -> str:
    try:
        # 尝试将输入值转换为 Decimal 类型
        original_value = Decimal(input_value)

        # 生成一个介于 0.8 和 0.85 之间的随机数
        random_factor = Decimal(random.uniform(0.8, 0.85))

        # 调整原始值
        adjusted_value = original_value * random_factor

        # 保留 5 位小数
        adjusted_value = adjusted_value.quantize(Decimal('0.00001'))  # 保留5位小数

        # 强制返回字符串格式，以避免科学计数法
        return format(adjusted_value, '.5f')  # 输出为标准小数格式
    except ValueError:
        # 如果转换失败，说明 input_value 不是有效的数字
        return "0"


def wait_for_element_or_refresh(page, xpath, max_retries=3, timeout=5):
    """
    等待指定的元素出现，如果没有出现，则刷新页面并重试，直到达到最大重试次数。
    :param page: 浏览器页面对象
    :param xpath: 要等待的元素的 xpath
    :param max_retries: 最大重试次数
    :param timeout: 每次查找元素的最大等待时间
    :return: 成功返回 True，失败返回 False
    """
    retries = 0
    while retries < max_retries:
        # 等待元素加载
        if __get_ele(page=page, xpath=xpath, loop=timeout):
            logger.info(f"元素 {xpath} 成功加载，继续执行操作。")
            return True  # 元素加载成功，继续执行
        else:
            page.refresh()  # 刷新页面
            logger.info(f"第 {retries + 1} 次尝试刷新页面")

        retries += 1  # 失败时增加重试次数
        time.sleep(2)  # 等待页面重新加载

    # 如果达到最大重试次数，仍未成功加载元素，记录并返回 False
    logger.info(f"达到最大重试次数 {max_retries}，未能成功加载元素 {xpath}，关闭窗口。")
    return False



# 检测手续费是否过高
def check_difference_exceeds_threshold(value1: str, value2: str) -> bool:
    # 去除 '$' 符号并转换为浮动数
    value1_float = float(value1.replace("$", ""))
    value2_float = float(value2.replace("$", ""))

    # 计算两个值的差距
    difference = abs(value1_float - value2_float)

    # 计算 2% 的阈值
    threshold = 0.02 * value1_float

    # 判断差距是否超过 2%
    if difference > threshold:
        # return "差距超过 2%"
        return False
    return False

# 启动任务
def __do_task(acc, retry: int = 0):
    evm_id = acc['evm_id']
    evm_addr = acc['evm_addr']
    page = __get_page(evm_id=evm_id, user='lm', retry=retry)
    status = False
    try:
        logger.info(f"登录钱包{evm_id},第{retry}次尝试访问")
        __login_wallet(page=page, evm_id=evm_id)

        hyperbolic_page = page.new_tab(url='https://app.towns.com/')

        # 关闭多余的窗口
        __handle_signma_popup(page=page, count=0, timeout=15)

        if __click_ele(page=hyperbolic_page,
                       xpath="x://button[span[p[contains(text(), 'Login')]] and not(@disabled)]", loop=2):
            if __get_ele(page=hyperbolic_page,
                           xpath="x://button[contains(text(), 'Continue with Email')]", loop=1) is None:
                __click_ele(page=hyperbolic_page,
                            xpath="x://button[div[contains(text(), 'More options')]]", loop=2, must=True)

            __click_ele(page=hyperbolic_page,
                        xpath="x://button[contains(text(), 'Continue with Email')]", loop=2, must=True)
            __input_ele_value(page=hyperbolic_page, xpath='x://input[@id="email-input"]',
                              value=(evm_addr.lower() + "@dmail.ai"))

            __click_ele(page=hyperbolic_page,
                        xpath="x://button[span[contains(text(), 'Submit')] and not(@disabled)]", loop=2, must=True)
            code = __get_email_code(page=hyperbolic_page.browser, xpath='x://table[@data-id="react-email-section"]//p[@data-id="react-email-text"]', evm_addr=evm_addr.lower())
            # 查找所有 input 元素，定位到 div 下的所有 text 类型的 input
            inputs = hyperbolic_page.eles('x://div//input[@type="text"]')
            for i, input_element in enumerate(inputs):
                # 填入对应的数字
                input_element.input(code[i])


        __click_ele(page=hyperbolic_page, xpath="x://span[@data-testid='towns-wallet-button']", loop=10, must=True)
        __click_ele(page=hyperbolic_page, xpath="x://span[span[contains(text(), 'Deposit')]]", loop=10, must=True)
        with file_lock:
            solana_val = __get_click_clipboard(page=hyperbolic_page, xpath="x://button[contains(text(), 'Copy')]", loop=2, must=True, find_all=True, index=0)
            base_eth = __get_click_clipboard(page=hyperbolic_page, xpath="x://button[contains(text(), 'Copy')]", loop=2, must=True, find_all=True, index=1)
            if solana_val and base_eth:
                append_date_to_file(register_date_file, evm_id)
                append_date_to_file(register_log_date_file, evm_id + "," + solana_val + "," + base_eth)
                logger.info(f'{evm_id}:solana_val:{solana_val},base_eth:{base_eth}')
                client.publish("appInfo", json.dumps(get_app_info_integral(base_eth, evm_id, 0)))
                client.publish("appInfo", json.dumps(get_app_info_integral(solana_val, evm_id, 1)))
                status = True
                # add_log(message=solana_val, task_name='towns_solana_key', index=evm_id, node_name='127.0.0.1',server_url="http://192.168.0.16:8082")
                # add_log(message=base_eth, task_name='towns_base_eth_key', index=evm_id, node_name='127.0.0.1',server_url="http://192.168.0.16:8082")



        #
        # __click_ele(page=hyperbolic_page, xpath="x://span[img[@alt='Towns Points']]", loop=10, must=True)
        # points = __get_points(page=hyperbolic_page)
        #
        # __click_ele(page=hyperbolic_page, xpath='x://span[@class="_153ynsn0 _3zlyma5ms _3zlymaa _3zlyma6k1 _3zlyma6hj" and contains(@style, "data:image/png;base64")]', loop=10, must=True)
        # if __get_ele(page=hyperbolic_page, xpath= f'x://span[contains(text(), "The beaver is not ready for his belly rub")]', loop=2):
        #     logger.info('签到时间未到，稍后重试')
        #     return False
        # else:
        #     __click_ele(page=hyperbolic_page, xpath="x://button[contains(text(), 'Pay with ETH')]", loop=2, must=True)
        #     __handle_signma_popup(hyperbolic_page.browser, count=1, timeout=15)
        #
    except Exception as e:
        logger.info(f"未知异常 {acc['evm_id']} ：{e}")
    finally:
        if page is not None:
            try:
                page.quit()
            except Exception as pge:
                logger.info(f"错误")
    return status


def get_app_info_integral(data, evm_id, type):
    return {
        "serverId": f"{all_args.serverId}",
        "applicationId": f"{all_args.appId}",
        "publicKey": f"{evm_id}",
        "operationType": f"{type}",
        "description": f"{data}",
    }



def __get_points(page):
    # 延迟两秒 等待数据加载
    time.sleep(2)
    # 查找 class 为指定的 span 元素
    span_element = __get_ele(page=page ,xpath=f'x://span[contains(@class,  "_153ynsn0 _3zlyma5mj _3zlyma3ij _3zlyma3o1 _3zlyma3tj _3zlyma3z1 _3zlymaa _1b907cju _3zlyma2ds _3zlyma5oj _3zlyma6l1 _153ynsn1")]')
    if span_element:
        # 获取所有 p 元素
        p_elements = span_element.eles('x://p')
        # 排除指定索引的 p 元素并获取其他 p 元素的文本
        texts = []
        for i, p_element in enumerate(p_elements):
            if i not in [1, 3]:
                texts.append(p_element.text.strip())
                logger.info(p_element.text.strip())
        return texts
    return None



# 启动容器
def run(accounts, max_workers: int = 5, max_retry: int = 2):
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





# =================================================   MQTT   ======================================
def create_mqtt_client(broker, port, username, password, topic):
    """
    创建并配置MQTT客户端，使用 MQTTv5 回调方式
    protocol=mqtt.MQTTv5 来避免旧版回调弃用警告
    """
    client = mqtt.Client(
        protocol=mqtt.MQTTv5,  # 指定使用 MQTTv5
        userdata={"topic": topic}  # 传递自定义数据
    )
    client.username_pw_set(username, password)

    # 注册回调函数（使用 v5 风格签名）
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        raise ConnectionError(f"Error connecting to broker: {e}")

    return client


# ========== MQTT 事件回调函数（MQTTv5） ==========
def on_connect(client, userdata, flags, reason_code, properties=None):
    """
    当客户端与 Broker 建立连接后触发
    reason_code = 0 表示连接成功，否则为失败码
    """
    if reason_code == 0:
        print("Connected to broker successfully.")
        # 仅发布消息，去除订阅
        pass
    else:
        print(f"Connection failed with reason code: {reason_code}")


def on_disconnect(client, userdata, reason_code, properties=None):
    """
    当客户端与 Broker 断开连接后触发
    可以在此处进行自动重连逻辑
    """
    print(f"Disconnected from broker, reason_code: {reason_code}")
    # 如果 reason_code != 0，则表示非正常断开
    while True:
        try:
            print("Attempting to reconnect...")
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # 等待 5 秒后重试


def on_message(client, userdata, msg):
    """
    当收到订阅主题的新消息时触发
    v5 中的 on_message 参数与 v3.x 相同： (client, userdata, message)
    """
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")


# =================================================   MQTT   ======================================


def read_file(file_path):
    """从文件中读取内容并去除多余空白"""
    try:
        # logger.info(f"读取文件: {file_path}")
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError(f"文件未找到: {file_path}")


def decrypt_aes_ecb(secret_key, data_encrypted_base64, accountType):
    """
    解密 AES ECB 模式的 Base64 编码数据，
    去除 PKCS7 填充后返回所有 accountType 为 "hyper" 的记录。
    """
    try:
        # Base64 解码
        encrypted_bytes = base64.b64decode(data_encrypted_base64)
        # 创建 AES 解密器
        cipher = AES.new(secret_key.encode('utf-8'), AES.MODE_ECB)
        # 解密数据
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        # 去除 PKCS7 填充（AES.block_size 默认为 16）
        decrypted_bytes = unpad(decrypted_bytes, AES.block_size)
        # 将字节转换为字符串
        decrypted_text = decrypted_bytes.decode('utf-8')

        # 解析 JSON 字符串为 Python 对象（通常为列表）
        data_list = json.loads(decrypted_text)

        # 创建结果列表，收集所有 accountType 为 "hyper" 的记录
        result = [item for item in data_list if item.get('accountType') == accountType]

        # 返回结果列表，如果没有匹配项则返回空列表
        return result
    except Exception as e:
        # 记录错误日志
        logger.error(f"解密失败: {e}")
        return []



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    parser.add_argument("--chromePort", type=str, help="浏览器端口", required=True)
    all_args = parser.parse_args()

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()
    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + all_args.appId + '_user.json')
    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(all_args.decryptKey, encrypted_data_base64, 'towns')

    while True:
        # 执行任务情况
        # ex_task_date_file = f"./ex_account_{get_date_as_string()}.txt"
        register_date_file = f"./register.txt"
        register_log_date_file = f"./registerLog.txt"
        ex_list = read_data_list_file(register_date_file, check_exists=True)
        task_data = []
        for key in public_key_tmp:
            if len(ex_list) > 0 and key["secretKey"] in ex_list:
                logger.info(f'跳过任务：{key["secretKey"]}')
                continue
            task_data.append({
                "evm_id": key["secretKey"],
                "evm_addr": key["publicKey"],
                # "task_type": parts[2],
            })

        if len(task_data) <= 0:
            logger.info('结束任务')
            time.sleep(1000)
        # 启动
        print(f'执行任务数{len(task_data)}')
        run(accounts=task_data, max_workers=1)
