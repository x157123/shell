import time
import threading
import concurrent.futures
import random
import pyperclip
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
import requests
from decimal import Decimal
import os
from datetime import datetime, timedelta
import platform
from typing import Union

evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"
file_lock = threading.Lock()


# 打开浏览器
def __get_page(evm_id, window: int = 0):
    if platform.system().lower() == "windows":
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .add_extension(r"C:\Users\liulei\Desktop\fsdownload\signma")
            .set_user_data_path(f"D://tmp//rarible//{window}")
            .set_local_port(55443 + window)
            .headless(on_off=False))
    else:
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_paths(r"/opt/google/chrome/google-chrome")
            .add_extension(f"/home/lm/extensions/signma")
            .set_user_data_path(f"/home/lm/task/chrome_data/wall/{window}")
            .set_proxy(f"192.168.3.107:7890")
            .set_local_port(55543 + window)
            .headless(on_off=False))
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


# 获取元素内容
def __get_ele_value(page, xpath: str = '', loop: int = 5, must: bool = False,
                    find_all: bool = False,
                    index: int = -1):
    try:
        # logger.info(f'获取元素{xpath}
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
                # logger.info(f'{xpath}输入{value}')
                page.ele(locator=xpath).clear()
                time.sleep(0.5)
                page.ele(locator=xpath).input(value, clear=True)
            else:
                page.eles(locator=xpath)[index].clear()
                time.sleep(0.5)
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


def __close_signma_popup(page, count: int = 1, timeout: int = 15, must: bool = False):
    """处理 Signma 弹窗，遍历所有 tab 页签"""
    start_time = time.time()
    _count = 0
    while time.time() - start_time < timeout:
        time.sleep(2)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for tab in all_tabs:
            if f'{evm_ext_id}' in tab.url:
                _count += 1
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


# 获取文件名称
def get_all_files_in_directory(directory):
    file_list = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            # Add the full path of the file to the list
            file_list.append(os.path.join(root, file))

    return file_list


def get_rari_wallet(evm_address):

    # 请求接口
    url = f"https://rari.calderaexplorer.xyz/api/v2/addresses/{evm_address}"
    response = requests.get(url)
    logger.info(f'请求{evm_address}')
    #
    if response.status_code == 404:
        requests.get(f"https://rari.calderaexplorer.xyz/api/v2/search/check-redirect?q={evm_address}")
        time.sleep(5)
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
def get_rari_log(evm_address, num: int = 1):
    # 请求接口
    url = f"https://rari.calderaexplorer.xyz/api/v2/addresses/{evm_address}/transactions"
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
        info['end'] = get_rari_wallet(evm_address)
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


def __get_base_balance(evm_address):
    __headers = {
        'authority': 'mainnet.base.org',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://ct.app',
        'referer': 'https://ct.app/',
        'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    }
    json_data = {
        'jsonrpc': '2.0',
        'id': random.randint(1, 1000),
        'method': 'eth_getBalance',
        'params': [
            evm_address.lower(),
            'latest',
        ],
    }
    response = requests.post(url='https://mainnet.base.org/', headers=__headers, json=json_data)
    result = response.json()
    base_balance = int(result.get('result'), 16) / (10 ** 18)
    return base_balance


def __get_arb_balance(address):
    __headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Not?A_Brand\";v=\"99\", \"Chromium\";v=\"130\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "Referer": "https://ct.app/",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }
    json_data = {
        "id": random.randint(1, 1000),
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [
            address.lower(),
            "latest"
        ]
    }
    response = requests.post(url='https://arb-mainnet.g.alchemy.com/v2/TlHfhwlhVTEa1rMJwQwVf7xFCawVvr5U', headers=__headers, json=json_data)
    result = response.json()
    base_balance = int(result.get('result'), 16) / (10 ** 18)
    return base_balance

def get_local_time():
    utc_now = datetime.now()
    utc_plus_8 = utc_now + timedelta(hours=8)
    formatted_time = utc_plus_8.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


# 启动任务
def __do_task(evm_id, acc, num: int = 0):
    page = __get_page(evm_id=evm_id, window=num)
    logger.info(f'线程{num}:{len(acc)}')
    __login_wallet(page=page, evm_id=evm_id)

    page.get(url=url)
    __close_signma_popup(page=page, count=0)
    for ac in acc:
        try:
            base_balance = __get_arb_balance(address=ac["evm_addr"])
            if min_bal <= float(base_balance):
                logger.success(f'钱包金额充足:{base_balance}，跳过当前账号')
                with file_lock:
                    append_date_to_file(ex_log_file, ac["evm_addr"])
                    append_date_to_file(ex_data_file, f"{evm_id},{net},{ac['evm_id']},{ac['evm_addr']},{base_balance},0,{base_balance},{get_local_time()}")
            else:
                if __click_ele(page=page, xpath='x://button/div/div[text()="Select wallet"]', loop=1):
                    els = __get_ele(page=page, xpath='x://div[@data-testid="dynamic-modal-shadow"]')
                    if els and els.shadow_root:
                        __click_ele(page=els.shadow_root, xpath='x://button/div/span[text()="Signma"]', loop=1)
                        __handle_signma_popup(page=page, count=1)
                logger.info(f'线程{num}：钱包{ac["evm_addr"]}：余额为{base_balance}')
                time.sleep(2)
                __click_ele(page=page, xpath="x://div[contains(text(), 'Buy')]/following-sibling::button[@aria-label='Multi wallet dropdown']")
                __click_ele(page=page, xpath='x://div[text()="Paste wallet address"]')
                __input_ele_value(page=page, xpath='x://input[@placeholder="Address or ENS"]', value=ac["evm_addr"])
                if __click_ele(page=page, xpath='x://button[text()="Save" and not(@disabled)]'):
                    amount = "{:.6f}".format(random.uniform(start_bal, end_bal))
                    time.sleep(2)
                    __input_ele_value(page=page, xpath='x://input[@inputmode="decimal"]', value=amount)
                    send_amount = __get_ele_value(page=page, xpath='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]', find_all=True, index=0)
                    receive_amount = __get_ele_value(page=page, xpath='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]', find_all=True, index=1)
                    send_amount = send_amount.strip().replace('$', '')
                    receive_amount = receive_amount.strip().replace('$', '')
                    gas_fee = round(float(send_amount) - float(receive_amount), 3)
                    if float(gas_fee) > max_gas_fee:
                        logger.error(f'{gas_fee} gas too high {evm_id} to {ac["evm_addr"]}')
                        return False
                    if __click_ele(page=page, xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]'):
                        __handle_signma_popup(page=page, count=1)
                        if __get_ele(page=page, xpath='x://button[text()="Done"]', loop=5):
                            if __get_ele(page=page, xpath='x://button[text()="View Details"]', loop=1):
                                if __click_ele(page=page, xpath='x://button[text()="Done"]', loop=5):
                                    time.sleep(2)
                                    new_balance = __get_arb_balance(address=ac["evm_addr"])
                                    if min_bal <= float(new_balance):
                                        with file_lock:
                                            append_date_to_file(ex_log_file, ac["evm_addr"])
                                            append_date_to_file(ex_data_file, f"{evm_id},{net},{ac['evm_id']},{ac['evm_addr']},{base_balance},{amount},{new_balance},{get_local_time()}")
                                            logger.info(f"充值成功{ac['evm_id']}:{ac['evm_addr']}")
                        if not __close_signma_popup(page=page, count=0):
                            __click_ele(page=page, xpath="x//button[contains(@class, 'relay-cursor_pointer') and contains(@class, 'relay-text_gray9')]", loop=1)
                page.get(url=url)
                time.sleep(1)
        except Exception as e:
            logger.info(f'异常数据：{e}')
            try:
                page.quit()
            except Exception as e:
                logger.info(f'未知错误{e}')
            page = __get_page(evm_id=evm_id, window=num)
            __login_wallet(page=page, evm_id=evm_id)
            __close_signma_popup(page=page, count=0)
            page.get(url=url)


def split_array(arr, num_parts):
    # 计算每个子数组的大小
    avg_len = len(arr) // num_parts
    remainder = len(arr) % num_parts

    result = []
    start = 0

    for i in range(num_parts):
        end = start + avg_len + (1 if i < remainder else 0)
        result.append(arr[start:end])
        start = end

    return result


# 启动容器
def run(eve_id, data, max_workers: int = 5):
    # 将数据分配给 5 个线程
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 动态计算每个线程应该处理的数据量
        # 计算每个线程处理的数据段
        chunk_size = len(data) // max_workers
        remainder = len(data) % max_workers  # 计算余数，分配到前面的线程中

        # 创建任务，每个线程处理不同的数据部分
        start_idx = 0
        futures = []
        for i in range(max_workers):
            end_idx = start_idx + chunk_size + (1 if i < remainder else 0)  # 余数分配到前面线程
            sub_data = data[start_idx:end_idx]
            futures.append(executor.submit(__do_task, eve_id, sub_data, i + 1))  # 提交任务
            start_idx = end_idx

        # 等待任务完成
        for future in concurrent.futures.as_completed(futures):
            pass  # 如果有异常或需要返回结果，可以在这里处理

    print("所有任务完成")


def get_date_as_string():
    # 获取当前日期和时间
    now = datetime.now()
    # 将日期格式化为字符串 年-月-日
    date_string = now.strftime("%Y-%m-%d")
    return date_string


def get_arbiscan_wallet(page ,evm_address):
    arbiscan_page = page.new_tab(url=f'https://arbiscan.io/address/{evm_address}')
    time.sleep(2000)


def get_eth_balance(
        address: str,
        *,
        url: str = "https://eth-mainnet.public.blastapi.io/",
        block_tag: str = "latest",
        timeout: int = 10,
        return_eth: bool = False,
        return_str: bool = False,
) -> Union[int, Decimal, str]:
    payload = [{
        "id": 1,
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, block_tag],
    }]

    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()

    result_hex = resp.json()[0]["result"]         # e.g. '0x27bc86...'
    balance_wei = int(result_hex, 16)

    if not return_eth:
        return balance_wei

    # Wei → ETH，使用 Decimal 避免精度丢失与科学计数
    balance_eth = Decimal(balance_wei) / Decimal(10**18)

    if return_str:
        # format(..., 'f') 始终输出定点小数；再去掉多余 0 与 .
        return format(balance_eth, 'f').rstrip('0').rstrip('.')

    return balance_eth


if __name__ == '__main__':
    # 钱包最小余额，大于这个钱就不转
    min_bal = 0.0005
    # 随机转账金额 开始
    start_bal = 0.000611
    # 随机转账金额 结束
    end_bal = 0.000651
    # 钱包地址
    eve_id = 88102
    # 损耗现在
    max_gas_fee = 0.04
    # 转账窗口
    max_workers = 1
    # 需要转账的地址格式如下  1,0xd7746eaed250ba139ab09df7b15d3eea447246d4
    task_file = "./base_eth.txt"
    # 记录文件
    ex_log_file = "./base_eth_dt.txt"
    ex_data_file = "./base_eth_data.txt"
    net = 'op'

    url = "https://relay.link/bridge/arbitrum?fromChainId=8453"

    while True:
        # 执行任务情况
        ex_list = read_data_list_file(ex_log_file, check_exists=True)
        read_data_list_file(ex_data_file, check_exists=True)
        # 制定任务
        task_list = read_data_list_file(task_file)
        task_data = []
        for task in task_list:
            parts = task.split(",")
            if len(ex_list) > 0 and parts[1] in ex_list:
                logger.info(f'跳过任务：{parts[0]}:{parts[1]}')
                continue
            task_data.append({
                "evm_id": parts[0],
                "evm_addr": parts[1],
            })

        # 启动
        if len(task_data) <= 0:
            logger.info("已处理完毕,等待60秒")
            time.sleep(60)
        else:
            print(f'执行任务数{len(task_data)}')
            run(eve_id=eve_id, data=task_data, max_workers=max_workers)
