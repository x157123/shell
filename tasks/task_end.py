import requests
from DrissionPage import ChromiumPage, ChromiumOptions
from datetime import datetime
import random
from loguru import logger
import argparse
import os
from decimal import Decimal
import platform
import json
import string
from web3 import Web3
import re
import hmac
import hashlib
import struct
import time
import base64
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import shutil


# ========== 全局配置 ==========
evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"   #老版本

# evm_ext_id = "heagpibejnndofpglilpndpgdfdhhfpo"

ARGS_IP = ""  # 在 main 里赋值


def __get_page(_type, _id, _port, _home_ip):
    # if _type == 'nexus_joina_sse':
    #     if platform.system().lower() == "windows":
    #         logger.info('跳过删除')
    #     else:
    #         try:
    #             # 删除临时文件
    #             dir_path = f"/home/ubuntu/task/tasks/{_type}/chrome_data/{_id}"
    #             if os.path.isdir(dir_path):
    #                 shutil .rmtree(dir_path)
    #                 time.sleep(1)
    #         except Exception as e:
    #             logger.info("删除临时文件错误")
    _pages = None
    logger.info(f"启动类型: {_type}")
    options = ChromiumOptions()
    if platform.system().lower() == "windows":
        options.set_browser_path(r"E:\chrome_tool\127.0.6483.0\chrome.exe")
    else:
        options.set_browser_path('/opt/google/chrome')
    if _home_ip:
        options.set_proxy(f"{_home_ip}:47163")

    if platform.system().lower() == "windows":
        options.add_extension(f"E:/chrome_tool/signma")
        if _type == 'nexus_joina_sse':
            options.add_extension(f"E:/chrome_tool/cookin")
    else:
        options.add_extension(f"/home/ubuntu/extensions/chrome-cloud")

    if _type == 'prismax':
        options.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

    # 用户数据目录
    if platform.system().lower() == "windows":
        options.set_user_data_path(f"E:/tmp/chrome_data/{_type}/{_id}")
    else:
        options.set_user_data_path(f"/home/ubuntu/task/tasks/{_type}/chrome_data/{_id}")
    # 端口可能被占用，尝试几次
    for offset in range(3):
        try:
            if _port is not None:
                options.set_local_port(_port)
            else:
                options.set_local_port(port + offset)
            _pages = ChromiumPage(options)
            break
        except Exception as e:
            logger.warning(f"端口 {port + offset} 启动失败，重试：{e}")
            time.sleep(1)
            _pages = None
    if _pages is not None:
        if platform.system().lower() != "windows":
            _pages.set.window.max()
        _pages.set.blocked_urls(r'.*\.(jpg|png|gif|webp|svg)')

    logger.info('初始化结束')
    return _pages


def check_available() -> Optional[Tuple[str, str]]:
    url = "http://43.163.232.251:22300/api/ip/get"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        # 检查 success 字段和必需的 id、ip 字段
        if data.get("success") and data.get("id") and data.get("ip"):
            return (data["id"], data["ip"])
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def end_available(_key: str = '0000') -> bool:
    url = f"http://43.163.232.251:22300/api/ip/return?id={_key}"
    try:
        response = requests.get(url, timeout=15)  # 设置超时 5 秒
        response.raise_for_status()  # 如果响应状态码不是 200 会抛异常
    except Exception as e:
        print("请求失败:", e)
    return True


# ========== 文件读写 ==========

# 读取txt文件（显式 UTF-8，确保创建文件）
def read_data_list_file(file_path, check_exists=True):
    if check_exists and not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8'):
            pass
    with open(file_path, "r", encoding='utf-8') as file:
        questions = file.readlines()
    return [question.strip() for question in questions if question.strip()]


# 文件追加（显式 UTF-8）
def append_date_to_file(file_path, data_str):
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(data_str + '\n')


# ========== 工具函数 ==========

def signma_log(message: str, task_name: str, index: str) -> bool:
    """修复：使用 params 自动 URL 编码；不再使用 raise logger.error；加超时"""
    try:
        server_url = 'http://150.109.5.143:9900'
        params = {"ip": ARGS_IP, "type": task_name, "id": index, "data": message}
        r = requests.get(server_url, params=params, timeout=5)
        if r.status_code == 200:
            logger.info("积分提交成功")
        else:
            logger.warning(f"日志上报返回码：{r.status_code}")
        return True
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return False


def get_date_as_string():
    return datetime.now().strftime("%Y-%m-%d")


def click_x_y(x, y, window):
    """尽量避免使用坐标点击；如必须，请确保 DISPLAY 在主流程里统一设置"""
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.moveTo(x, y)
    pyautogui.click()


# 稳定点击
def __click_ele(page, xpath: str, loop: int = 5, must: bool = False,
                find_all: bool = False, move_click: bool = False, index: int = 0) -> bool:
    for i in range(1, loop + 1):
        try:
            if not find_all:
                logger.info(f'点击按钮:{xpath}')
                ele = page.ele(locator=xpath, timeout=2)
                if ele:
                    if move_click:
                        page.actions.move_to(ele).click()
                    else:
                        ele.click()
                    return True
            else:
                eles = page.eles(locator=xpath, timeout=2)
                if eles and 0 <= index < len(eles):
                    if move_click:
                        page.actions.move_to(eles[index]).click()
                    else:
                        eles[index].click()
                    return True
        except Exception as e:
            logger.debug(f'点击失败({i}/{loop}) {xpath}: {e}')
        time.sleep(1)
    if must:
        raise Exception(f'未找到元素:{xpath}')
    return False


# 获取元素
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
              find_all: bool = False,
              index: int = -1):
    loop_count = 1
    for i in range(1, loop + 1):
        logger.info(f'查找元素{xpath}:{loop_count}')
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


# 获取元素文本
def __get_ele_value(page, xpath: str = '', loop: int = 5, must: bool = False,
                    find_all: bool = False, index: int = 0):
    try:
        _ele = __get_ele(page=page, xpath=xpath, loop=loop, must=must, find_all=find_all, index=index)
        if _ele:
            return _ele.text
    except Exception as e:
        logger.debug(f'获取文本失败 {xpath}: {e}')
    return None


def get_points(tab):
    """修复：拼写可能为 'Accumulated points'，并加判空"""
    if __click_ele(page=tab, xpath="x://button[.//span[text()='Points']]"):
        # 建议换成等待具体元素出现而不是固定 sleep
        for _ in range(15):
            target_div = tab.ele("x://div[text()='Accumulated points']/following-sibling::div")
            if target_div:
                return target_div.text
            time.sleep(1)
    return None


def wait_for_positive_amount(page, xpath, max_attempts=8, interval=1):
    """循环尝试获取 >0 的金额，默认尝试 8 次"""
    for attempt in range(max_attempts):
        raw = __get_ele_value(page=page, xpath=xpath)
        if raw:
            clean = raw.strip().lstrip('$').replace(',', '')
            try:
                value = float(clean)
                if value > 0:
                    return value
            except ValueError:
                pass
        time.sleep(interval)
    return 0.0

def __handle_phantom_popup(page, count: int = 1, timeout: int = 15, must: bool = False):
    """
    处理 Signma 弹窗，遍历所有 tab。
    修复：当 count=0 时，表示“尽力清弹窗”，整轮扫描后返回是否处理过。
    """
    start_time = time.time()
    _count = 0
    processed_any = False
    while time.time() - start_time < timeout:
        time.sleep(2)
        all_tabs = page.get_tabs()
        for tab in all_tabs:
            try:
                if 'bfnaelmomeimhlpmgjnjophhpkkoljpa/notification.html' in tab.url:
                    __click_ele(page=tab, xpath='x://button[@data-testid="primary-button"]', loop=1)

                time.sleep(1)
            except Exception as e:
                logger.debug(f"处理弹窗异常：{e}")
            # 原逻辑：处理足够数量即返回
            if count > 0 and _count >= count:
                return True
        # count==0：整轮扫描后再返回
        if count == 0:
            return processed_any


def __handle_signma_popup(page, count: int = 1, timeout: int = 15, must: bool = False):
    """
    处理 Signma 弹窗，遍历所有 tab。
    修复：当 count=0 时，表示“尽力清弹窗”，整轮扫描后返回是否处理过。
    """
    start_time = time.time()
    _count = 0
    processed_any = False
    while time.time() - start_time < timeout:
        time.sleep(2)
        all_tabs = page.get_tabs()
        for tab in all_tabs:
            try:
                if '/popup.html?page=%2Fdapp-permission' in tab.url:
                    if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                        __click_ele(page=tab, xpath='x://*[@id="close"]')
                        time.sleep(1)
                    if __click_ele(page=tab, xpath='x://button[@id="grantPermission"]'):
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif '/notification.html#connect' in tab.url:
                    if __click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]'):
                        __click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif '/notification.html#confirmation' in tab.url:
                    if __click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]'):
                        time.sleep(2)
                        __click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif '/notification.html#confirm-transaction' in tab.url:
                    if __click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]'):
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif '/popup.html?page=%2Fsign-transaction' in tab.url:
                    if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                        __click_ele(page=tab, xpath='x://*[@id="close"]')
                        time.sleep(1)
                    if __click_ele(page=tab, xpath='x://button[@id="sign"]'):
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif '/popup.html?page=%2Fsign-data' in tab.url:
                    if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                        __click_ele(page=tab, xpath='x://*[@id="close"]')
                        time.sleep(1)
                    if __click_ele(page=tab, xpath='x://button[@id="sign"]'):
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif 'popup.html?page=%2Fpersonal-sign' in tab.url:
                    if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                        __click_ele(page=tab, xpath='x://*[@id="close"]')
                        time.sleep(1)
                    if __click_ele(page=tab, xpath='x://button[@id="sign"]'):
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif ('&tab=%2Fadd-evm-chain' in tab.url) or ('/popup.html?requestId=' in tab.url):
                    if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                        __click_ele(page=tab, xpath='x://*[@id="close"]')
                        time.sleep(1)
                    if __click_ele(page=tab, xpath='x://button[@id="addNewChain"]'):
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif 'popout.html?windowId=backpack' in tab.url:
                    if __click_ele(page=tab, xpath='x://div/span[text()="确认"]'):
                        time.sleep(2)
                        _count += 1
                        processed_any = True

                elif evm_ext_id in tab.url:
                    try:
                        tab.close()
                    except Exception as e:
                        logger.debug(f"关闭扩展 tab 失败：{e}")

            except Exception as e:
                logger.debug(f"处理弹窗异常：{e}")

            # 原逻辑：处理足够数量即返回
            if count > 0 and _count >= count:
                return True

        # count==0：整轮扫描后再返回
        if count == 0:
            return processed_any

    if _count < count and must:
        raise Exception('未处理指定数量的窗口')
    return _count >= count if count > 0 else processed_any


def __get_popup(page, _url: str = '', timeout: int = 15):
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
        all_tabs = page.get_tabs()
        for tab in all_tabs:
            if _url in tab.url:
                return tab
    return None

def __get_popup_url(page, _url: str = '', timeout: int = 15):
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
        all_tabs = page.get_tabs()
        for tab in all_tabs:
            if _url in tab.url:
                return tab.url
    return None


def __close_popup(page, _url: str = '', timeout: int = 15):
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
        for tab in page.get_tabs():
            if _url in tab.url:
                try:
                    tab.close()
                    return True
                except Exception as e:
                    logger.debug(f"关闭弹窗失败：{e}")
    return False

# ========== 业务函数 ==========

# 输入值
def __input_ele_value(page, xpath: str = '', value: str = '', loop: int = 5, must: bool = False,
                      find_all: bool = False, index: int = 0) -> bool:
    for i in range(1, loop + 1):
        try:
            if not find_all:
                ele = page.ele(locator=xpath, timeout=1)
                if ele:
                    ele.clear()
                    time.sleep(0.2)
                    ele.input(value, clear=True)
                    return True
            else:
                eles = page.eles(locator=xpath, timeout=1)
                if eles and 0 <= index < len(eles):
                    eles[index].clear()
                    time.sleep(0.2)
                    eles[index].input(value, clear=True)
                    return True
        except Exception as e:
            logger.debug(f'输入失败({i}/{loop}) {xpath}: {e}')
        time.sleep(0.5)
    if must:
        raise Exception(f'未找到元素:{xpath}')
    return False


# 登录钱包（Signma）
def __login_wallet(page, evm_id):
    time.sleep(3)
    wallet_url = f"chrome-extension://{evm_ext_id}/tab.html#/onboarding"
    xpath = "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
    if len(page.get_tabs(title="Signma")) > 0 and page.tabs_count >= 2:
        time.sleep(3)
        for pop_tab in page.get_tabs():
            if pop_tab.url == wallet_url:
                if __input_ele_value(page=pop_tab, xpath=xpath, value=evm_id):
                    time.sleep(1)
                    __click_ele(page=pop_tab, xpath="tag:button@@id=existingWallet")
    else:
        wallet_tab = page.new_tab(url=wallet_url)
        __input_ele_value(page=wallet_tab, xpath=xpath, value=evm_id)
        __click_ele(page=wallet_tab, xpath="tag:button@@id=existingWallet")
        time.sleep(1)


# 钱包转账
def __send_wallet(wallet_page, evm_id, send_evm_addr, amount, _url, max_gas_fee, end_amount):
    _bool = False
    w_page = wallet_page.new_tab(url=_url)
    if __click_ele(page=w_page, xpath='x://button[text()="Connect Wallet"]', loop=3):
        els = __get_ele(page=w_page, xpath='x://div[@data-testid="dynamic-modal-shadow"]')
        if els and els.shadow_root:
            if __click_ele(page=els.shadow_root, xpath='x://button/div/span[text()="Signma"]', loop=1):
                __handle_signma_popup(page=wallet_page, count=1)
            else:
                __click_ele(page=els.shadow_root, xpath='x://button[@data-testid="close-button"]', loop=1)
    time.sleep(2)

    __handle_signma_popup(page=wallet_page, count=0)
    if send_evm_addr is not None:
        if __click_ele(page=w_page,
                       xpath="x://div[contains(text(), 'Buy')]/following-sibling::button[@aria-label='Multi wallet dropdown']",
                       loop=2):
            if __click_ele(page=w_page, xpath='x://div[text()="Paste wallet address"]'):
                __input_ele_value(page=w_page, xpath='x://input[@placeholder="Address or ENS"]', value=send_evm_addr)
                if __click_ele(page=w_page, xpath='x://button[text()="Save" and not(@disabled)]'):
                    time.sleep(2)
    if amount == 'Max':
        balance_value = (
            w_page.ele('x://button[text()="MAX"]')
            .parent(3)
            .ele('x://div[contains(text(), "Balance:")]')
            .text.replace("Balance:", "")
            .strip()
        )
        amount = "{:.5f}".format(float(balance_value) - end_amount)
    if amount is not None:
        __input_ele_value(page=w_page, xpath='x://input[@inputmode="decimal"]', value=amount)

    time.sleep(4)
    send_amount = __get_ele_value(page=w_page,
                                  xpath='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
                                  find_all=True, index=0)
    receive_amount = __get_ele_value(page=w_page,
                                     xpath='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
                                     find_all=True, index=1)
    send_amount = send_amount.strip().replace('$', '')
    receive_amount = receive_amount.strip().replace('$', '')
    gas_fee = round(float(send_amount) - float(receive_amount), 3)
    if float(gas_fee) > max_gas_fee:
        # logger.error(f'{gas_fee} gas too high to {send_evm_addr}')
        signma_log(message=f"gas_fee,{amount},{gas_fee},{_url}", task_name=f'wallet_gift_{get_date_as_string()}', index=evm_id)

    elif __click_ele(page=w_page, xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]'):
        __handle_signma_popup(page=wallet_page, count=3)
        __handle_signma_popup(page=wallet_page, count=0)
        if __get_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
            if __get_ele(page=w_page, xpath='x://button[text()="View Details"]', loop=1):
                if __click_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                    time.sleep(2)
                    signma_log(message=f"send,{amount},{gas_fee},{_url}", task_name=f'wallet_gift_{get_date_as_string()}', index=evm_id)
                    _bool = True
            else:
                if __click_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                    if __click_ele(page=w_page, xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]'):
                        __handle_signma_popup(page=wallet_page, count=3)
                        __handle_signma_popup(page=wallet_page, count=0)
                        if __get_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                            __get_ele(page=w_page, xpath='x://button[text()="View Details"]', loop=1)
                            time.sleep(2)
                            signma_log(message=f"send,{amount},{gas_fee},{_url}",
                                       task_name=f'wallet_gift_{get_date_as_string()}', index=evm_id)
                            _bool = True
    if w_page is not None:
        w_page.close()
    return _bool


def __send_end_wallet(wallet_page, evm_id, send_evm_addr, amount, _url, max_gas_fee, end_amount, _type):
    _bool = False
    w_page = None
    try:
        w_page = wallet_page.new_tab(url=_url)

        __click_ele(page=w_page, xpath='x://button[text()="I Understand"]', loop=3)

        if __click_ele(page=w_page, xpath='x://button[text()="Connect Wallet"]', loop=3):
            els = __get_ele(page=w_page, xpath='x://div[@data-testid="dynamic-modal-shadow"]')
            if els and els.shadow_root:
                if __click_ele(page=els.shadow_root, xpath='x://button/div/span[text()="Signma"]', loop=1):
                    __handle_signma_popup(page=wallet_page, count=1)
                else:
                    __click_ele(page=els.shadow_root, xpath='x://button[@data-testid="close-button"]', loop=1)
                time.sleep(2)

        if send_evm_addr is not None:
            if __click_ele(page=w_page,
                           xpath="x://div[contains(text(), 'Buy')]/following-sibling::button[@aria-label='Multi wallet dropdown']",
                           loop=2):
                if __click_ele(page=w_page, xpath='x://div[text()="Paste wallet address"]'):
                    __input_ele_value(page=w_page, xpath='x://input[@placeholder="Address or ENS"]',
                                      value=send_evm_addr)
                    if __click_ele(page=w_page, xpath='x://button[text()="Save" and not(@disabled)]'):
                        time.sleep(2)

        balance_value = (
            w_page.ele('x://button[text()="MAX"]')
            .parent(3)
            .ele('x://div[contains(text(), "Balance:")]')
            .text.replace("Balance:", "")
            .strip()
        )

        if amount == 'Max':
            if float(end_amount) > 0:
                amount = "{:.5f}".format(float(balance_value) - end_amount)
            else:
                __click_ele(page=w_page, xpath='x://button[text()="MAX"]', loop=1)
        elif amount == '20%':
            __click_ele(page=w_page, xpath='x://button[text()="20%"]', loop=1)
        elif amount == '50%':
            __click_ele(page=w_page, xpath='x://button[text()="50%"]', loop=1)
        if amount is not None and amount != 'Max' and amount != '20%' and amount != '50%':
            if float(amount) > 0:
                __input_ele_value(page=w_page, xpath='x://input[@inputmode="decimal"]', value=amount)
            else:
                __input_ele_value(page=w_page, xpath='x://input[@inputmode="decimal"]', value="0")

        time.sleep(10)
        send_amount = __get_ele_value(page=w_page,
                                      xpath='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
                                      find_all=True, index=0)
        receive_amount = __get_ele_value(page=w_page,
                                         xpath='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
                                         find_all=True, index=1)
        send_amount = send_amount.strip().replace('$', '')
        receive_amount = receive_amount.strip().replace('$', '')

        # if 0 <= float(send_amount) <= 0.2:
        #     _bool = True
        if float(balance_value) < end_amount:
            _bool = True
        else:
            if float(send_amount) > 10:
                max_gas_fee = max_gas_fee * 2
            gas_fee = round(float(send_amount) - float(receive_amount), 3)
            if float(gas_fee) > max_gas_fee:
                logger.error(f'{gas_fee} 地址 {send_evm_addr}')
                signma_log(message=f"gas_fee,{send_evm_addr},{amount},{gas_fee},{_url}", task_name=f'wallet_{_type}', index=evm_id)

            elif __click_ele(page=w_page, xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]'):
                __handle_signma_popup(page=wallet_page, count=3)
                __handle_signma_popup(page=wallet_page, count=0)
                if __get_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                    if __get_ele(page=w_page, xpath='x://button[text()="View Details"]', loop=1):
                        if __click_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                            time.sleep(2)
                            signma_log(message=f"send,{send_evm_addr},{amount},{gas_fee},{_url}", task_name=f'wallet_{_type}',
                                       index=evm_id)
                            _bool = True
                    else:
                        if __click_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                            if __click_ele(page=w_page,
                                           xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]'):
                                __handle_signma_popup(page=wallet_page, count=3)
                                __handle_signma_popup(page=wallet_page, count=0)
                                if __get_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                                    __get_ele(page=w_page, xpath='x://button[text()="View Details"]', loop=1)
                                    time.sleep(2)
                                    signma_log(message=f"send,{send_evm_addr},{amount},{amount},{gas_fee},{_url}", task_name=f'wallet_{_type}',
                                               index=evm_id)
                                    _bool = True
    except Exception as e:
        logger.info(f"{evm_id}: 处理任务异常: {e}")
    if w_page is not None:
        w_page.close()
    return _bool


def __eth_to_op_arb_base(page, evm_id, evm_addr):
    _bool = False
    __login_wallet(page=page, evm_id=evm_id)
    __handle_signma_popup(page=page, count=0)
    _gas = __quyer_gas()
    if _gas is not None:
        _low_gas = _gas.get('SafeGasPrice', '99')
        if _low_gas is not None and float(_low_gas) < 0.3:
            ethereum = get_eth_balance("ethereum", evm_addr)
            if ethereum is not None and float(ethereum) > 0.00004:
                _type = int(evm_id) % 3
                if _type == 0:
                    _type_str = 'op'
                    _url = "https://relay.link/bridge/optimism?fromChainId=1"
                elif _type == 1:
                    _type_str = 'base'
                    _url = "https://relay.link/bridge/base?fromChainId=1"
                else:
                    _type_str = 'arb'
                    _url = "https://relay.link/bridge/arbitrum?fromChainId=1"
                _bool = __send_end_wallet(page, evm_id, None, 'Max', _url, 0.05, 0.00003, f'eth_{_type_str}')
            elif ethereum is not None and float(ethereum) < 0.00004:
                _bool = True
            if _bool:
                signma_log(message=f"{evm_addr},{_low_gas},{ethereum}", task_name=f'wallet_eth_to_op_arb_base', index=evm_id)
    return _bool

def __swap_op_arb_base(page, evm_id, evm_addr):
    _bool = False
    __login_wallet(page=page, evm_id=evm_id)
    __handle_signma_popup(page=page, count=0)
    _gas = __quyer_gas()
    if _gas is not None:
        _low_gas = _gas.get('SafeGasPrice', '99')
        if _low_gas is not None and float(_low_gas) < 0.3:
            _base = get_eth_balance("base", evm_addr)
            _op = get_eth_balance("opt", evm_addr)
            _arb = get_eth_balance("arb", evm_addr)
            _rari = get_eth_balance("rari", evm_addr)
            if _rari is not None and float(_rari) > 0.000025:
                __add_net_work(page=page, coin_name='rari')
                key, value = get_max_from_map({'base': _base, 'opt': _op, 'arb': _arb})
                if key == 'base':
                    _url = 'https://relay.link/bridge/base?fromChainId=1380012617'
                elif key == 'opt':
                    _url = 'https://relay.link/bridge/optimism?fromChainId=1380012617'
                else :
                    _url = 'https://relay.link/bridge/arbitrum?fromChainId=1380012617'
                __send_end_wallet(page, evm_id, None, 'Max', _url, 0.05, 0.00002, f'rari_{key}')

                _base = get_eth_balance("base", evm_addr)
                _op = get_eth_balance("opt", evm_addr)
                _arb = get_eth_balance("arb", evm_addr)


            key, value = get_max_from_map({'base': _base, 'opt': _op, 'arb': _arb})

            if value is not None and float(value) > 0.00005:
                _end_net = ''
                __add_net_work(page=page, coin_name=key)

                _page_main = page.new_tab('https://bridge.t3rn.io/')
                if __click_ele(page=_page_main, xpath='x://button[text()="Connect wallet"]', loop=2):
                    __click_ele(page=_page_main, xpath='x://button/div/div/div/div[text()="Signma"]', loop=1)
                    __handle_signma_popup(page=page, count=1)
                if __click_ele(page=_page_main, xpath='x://button[text()="Connect wallet"]', loop=1):
                    if __click_ele(page=_page_main, xpath='x://button/div/div/div/div[text()="Signma"]', loop=1):
                        __handle_signma_popup(page=page, count=1)

                _amount = "{:.5f}".format(float(value) - 0.00003)
                if key == 'base':
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network-and-asset" and .//span[text()="from"]]', loop=4)
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Base"]]', loop=1)
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network-and-asset" and .//span[text()="to"]]', loop=4)
                    if random.choice([True, False]):
                        _end_net = 'Arbitrum One'
                        __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Arbitrum One"]]', loop=5)
                    else:
                        _end_net = 'Optimism'
                        __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Optimism"]]', loop=5)
                    evm_id_int = int(evm_id)
                    if 30005 <= evm_id_int <=30304 or 30405 <= evm_id_int <=30504 or 37826 <= evm_id_int <=39425 or 77338 <= evm_id_int <=77837:
                        _amount = "{:.5f}".format(float(value) - 0.00004)

                elif key == 'opt':
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network-and-asset" and .//span[text()="from"]]', loop=4)
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Optimism"]]', loop=1)
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network-and-asset" and .//span[text()="to"]]', loop=4)
                    if random.choice([True, False]):
                        __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Arbitrum One"]]', loop=5)
                        _end_net = 'Arbitrum One'
                    else:
                        _end_net = 'Base'
                        __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Base"]]', loop=5)

                elif key == 'arb':
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network-and-asset" and .//span[text()="from"]]', loop=4)
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Arbitrum One"]]', loop=1)
                    __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network-and-asset" and .//span[text()="to"]]', loop=4)
                    if random.choice([True, False]):
                        _end_net = 'Base'
                        __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Base"]]', loop=5)
                    else:
                        _end_net = 'Optimism'
                        __click_ele(page=_page_main, xpath='x://button[@data-testid="ui-select-network" and .//span[text()="Optimism"]]', loop=5)

                __input_ele_value(page=_page_main, xpath='x://input[@data-testid="ui-max-reward-input"]', loop=5, value=_amount)
                __click_ele(page=_page_main, xpath='x://button[text()="text()="Connect to Arbitrum One" or "text()="Connect to Base" or text()="Connect to Optimism"]', loop=3)
                if __click_ele(page=_page_main, xpath='x://button[text()="Confirm transaction"]', loop=5):
                    __handle_signma_popup(page=page, count=1)
                    time.sleep(5)
                    __handle_signma_popup(page=page, count=0)
                    if __get_ele(page=_page_main, xpath='x://a[text()="Submit a new order"]', loop=25):
                        _bool = True
                    else:
                        _mon_end = get_eth_balance(key, evm_addr)
                        if float(_mon_end) < float(value):
                            _bool = True
                if _bool:
                    signma_log(message=f"{evm_addr},{key}.{_end_net},{_amount}", task_name=f'wallet_swap_op_arb_base', index=evm_id)
    return _bool


def __task_camelot_apechain(page, evm_id, evm_addr):
    camelot_page = None
    __bool_2 = False
    result = get_ape_balance(evm_addr)
    try:
        _bool = False
        __handle_signma_popup(page=page, count=0)
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)

        __add_net_work(page=page, coin_name='apechain')

        camelot_page = page.new_tab(url='https://app.camelot.exchange/')
        if __click_ele(page=camelot_page, xpath="x://button[contains(text(), 'Connect')]", loop=1):
            shadow_host = camelot_page.ele('x://onboard-v2')  # 定位到 shadow-host
            shadow_root = shadow_host.shadow_root
            __click_ele(page=shadow_root, xpath='x://div[text()="MetaMask"]', loop=2)
            # 确定钱包  初次钱包确认4次， 通过之后只有两次
            __handle_signma_popup(page=page, count=4, timeout=20)

        __click_ele(page=camelot_page, xpath='x://div[contains(@class, "nav-link d-flex align-items-center")]')
        __click_ele(page=camelot_page, xpath='x://div[div[p[contains(text(), "ApeChain")]]]')
        __click_ele(page=camelot_page, xpath="x://button[contains(@class, 'btn btn-unstyled')]", loop=1)

        _gas = __quyer_gas()
        if _gas is not None:
            _low_gas = _gas.get('SafeGasPrice', '99')
            if _low_gas is not None and float(_low_gas) < 0.3:
                if __click_ele(page=camelot_page, xpath='x://div[contains(@class, "nav-link d-flex align-items-center")]'):
                    if __click_ele(page=camelot_page, xpath='x://div[div[p[contains(text(), "ApeChain")]]]'):
                        __click_ele(page=camelot_page, xpath="x://button[contains(@class, 'btn btn-unstyled')]", loop=1)
                        for i in range(5):
                            camelot_page.refresh()
                            # 示例 : 自定义代币列表
                            custom_tokens = [
                                {"key": "APE", "decimals": 18, "is_native": True},
                                {"key": "APEETH", "contract": "0xcF800F4948D16F23333508191B1B1591daF70438", "decimals": 18},
                                {"key": "APEUSD", "contract": "0xa2235d059f80e176d931ef76b6c51953eb3fbef4", "decimals": 18},
                            ]
                            url = 'https://apechain.calderachain.xyz/http'
                            result_type = get_wallet_balance_type(url, evm_addr, custom_tokens)
                            print("自定义配置查询结果:")
                            ape = result_type.get("APE", Decimal(0))
                            apeeth = result_type.get("APEETH", Decimal(0))
                            apeusd = result_type.get("APEUSD", Decimal(0))

                            print(f"ape: {ape}")
                            print(f"apeeth: {apeeth}")
                            print(f"apeusd: {apeusd}")

                            if apeusd >= Decimal("0.02"):
                                __click_ele(page=camelot_page, xpath='x://div[div[div[text()="From"]]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://button[span[text()="apeUSD"]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://div[div[div[text()="To"]]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://button[span[text()="APE"]]', loop=2)
                                time.sleep(2)
                                __click_ele(page=camelot_page, xpath='x://a[contains(text(), "Max")]', loop=2)
                                __get_ele(page=camelot_page, xpath='x://button[.//span[contains(text(), "Approve apeUSD")] and not(@disabled)]', loop=3)
                                __do_swap(page=camelot_page, loop=3, cont="Add apeUSD to Wallet", conts="Add APE to Wallet", swap_txt="Approve apeUSD")
                            elif ape >= Decimal("0.2"):
                                # 交换金额
                                __click_ele(page=camelot_page, xpath='x://div[div[div[text()="From"]]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://button[span[text()="APE"]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://div[div[div[text()="To"]]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://button[span[text()="apeETH"]]', loop=2)
                                # _text = __get_ele_value(page=camelot_page, xpath='x://div[contains(@class, "text-secondary") and contains(., "balance") and contains(., "Max")]')
                                # if _text:
                                #     # 提取金额部分
                                #     match = re.search(r'balance:\s*([\d.]+)', _text)
                                #     if match:
                                #         value = match.group(1)
                                _run_mon = round(float(ape - Decimal("0.1")), 6)
                                # 输入金额
                                __input_ele_value(page=camelot_page,
                                                  xpath="x://a[contains(text(), 'Max')]/ancestor::div[@class='text-secondary text-small text-right']/preceding-sibling::input",
                                                  value=str(_run_mon))
                                __get_ele(page=camelot_page, xpath='x://button[.//span[contains(text(), "Swap")] and not(@disabled)]', loop=3)
                                __do_swap(page=camelot_page, loop=3, cont="Add apeETH to Wallet", conts="Add APE to Wallet")
                            elif apeeth > Decimal("0"):
                                # 交换金额
                                __click_ele(page=camelot_page, xpath='x://div[div[div[text()="From"]]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://button[span[text()="apeETH"]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://div[div[div[text()="To"]]]', loop=2)
                                __click_ele(page=camelot_page, xpath='x://button[span[text()="APE"]]', loop=2)
                                time.sleep(2)
                                __click_ele(page=camelot_page, xpath='x://a[contains(text(), "Max")]', loop=2)
                                __get_ele(page=camelot_page, xpath='x://button[.//span[contains(text(), "Swap")] and not(@disabled)]', loop=3)
                                __bool_2 = __do_swap(page=camelot_page, loop=3, cont="Add apeETH to Wallet", conts= "Add APE to Wallet")
                            else:
                                __bool_2 = True
                            if __bool_2:
                                break
    except Exception as e:
        logger.info(f'异常数据：{e}')
        pass
    finally:
        if camelot_page is not None:
            try:
                camelot_page.close()
            except Exception:
                logger.info('关闭异常')
    _result = get_ape_balance(evm_addr)
    signma_log(message=f"{evm_addr},{__bool_2},{result['balance_eth']},{_result['balance_eth']}", task_name=f'camelot_apechain_{get_date_as_string()}', index=evm_id)
    return __bool_2


def __do_swap(page, loop: int = 3, cont: str = 'cont', conts: str = 'cont', swap_txt: str = 'swap'):
    attempts = 0
    time.sleep(3)
    for i in range(loop):
        # 点击 swap 按钮
        __click_ele(page=page, xpath=f'x://button[span[span[contains(text(), "Swap") or contains(text(), "{swap_txt}")]] and not(@disabled)]', loop=1)
        __click_ele(page=page, xpath=f'x://button[span[contains(text(), "Swap") or contains(text(), "{swap_txt}")] and not(@disabled)]', loop=1)
        __click_ele(page=page, xpath='x://button[span[contains(text(), "Approve apeETH") or contains(text(), "Approve APE") or contains(text(), "Approve apeUSD")]]', loop=1)
        # 处理钱包确认框 一次
        __handle_signma_popup(page=page.browser, count=2, timeout=25)
        # 检查是否发生错误
        if __get_ele(page=page,
                     xpath='x://h4[contains(text(), "Error while swapping. If the issue persists, please contact our support.") '
                           'or contains(text(), "Insufficient token allowance, please close this modal and try to increase your tokens approval amount.")]',
                     loop=1):
            logger.info(f'转账错误提示，尝试次数 {attempts + 1}')
            __click_ele(page=page, xpath='x://button[i[contains(@class, "mdi-close")]]', loop=5)
        elif __get_ele(page=page, xpath=f'x://button[span[contains(text(), "{cont}") or contains(text(), "{conts}")]]', loop=1):
            return True
        __close_popup(page=page.browser, _url=f'{evm_ext_id}', timeout=5)
        __click_ele(page=page, xpath='x://button[i[contains(@class, "mdi-close")]]', loop=1)
    return False


def __relay_link(page, evm_id, evm_addr):
    _bool = False
    __handle_signma_popup(page=page, count=0)
    __login_wallet(page=page, evm_id=evm_id)
    __handle_signma_popup(page=page, count=0)
    emv_id_int = int(evm_id)
    emd_w = 0.0006
    result = get_ape_balance(evm_addr)
    _base = get_eth_balance("base", evm_addr)
    _op = get_eth_balance("opt", evm_addr)
    _arb = get_eth_balance("arb", evm_addr)
    _rari = get_eth_balance("rari", evm_addr)
    _sum = float(_base) + float(_op) + float(_arb) + float(_rari)
    key, value = get_max_from_map({'base': _base, 'opt': _op, 'arb': _arb, 'rari': _rari})
    _sw = False
    if not (4291 <= emv_id_int <= 9290):
        if result and result['success'] and float(result['balance_eth']) >= 0.7:
            emd_w = 0.0005
        if _sum < emd_w:
            _gas = __quyer_gas()
            if _gas is not None:
                _low_gas = _gas.get('SafeGasPrice', '99')
                if _low_gas is not None and float(_low_gas) < 0.3:
                    _sw = True
                    wallet_page = __get_page('wallet', '88102', '34533', False)
                    __handle_signma_popup(page=wallet_page, count=0)
                    __login_wallet(page=wallet_page, evm_id='88102')
                    __handle_signma_popup(page=wallet_page, count=0)
                    __add_net_work(page=wallet_page, coin_name='base')
                    __handle_signma_popup(page=wallet_page, count=0)
                    _url = 'https://relay.link/bridge/apechain?fromChainId=8453'
                    _run_mon = round(random.uniform(0.000611, 0.000652), 6)
                    if result and result['success'] and float(result['balance_eth']) >= 0.7:
                        _run_mon = round(random.uniform(0.000511, 0.000552), 6)
                    _send_mon  = _run_mon - _sum
                    if _send_mon <= 0.00005:
                        _send_mon += 0.00005

                    elif key == 'opt':
                        _url = 'https://relay.link/bridge/optimism?fromChainId=8453'
                    else:
                        _url = 'https://relay.link/bridge/arbitrum?fromChainId=8453'

                    _bool = __send_end_wallet(wallet_page, '88102', evm_addr, round(_send_mon, 6), _url, 0.06, 0, f'eth_88102_apechain')
                    if wallet_page is not None:
                        try:
                            wallet_page.quit()
                        except Exception:
                            logger.exception("退出错误")
                    _base = get_eth_balance("base", evm_addr)
                    _op = get_eth_balance("opt", evm_addr)
                    _arb = get_eth_balance("arb", evm_addr)
                    _rari = get_eth_balance("rari", evm_addr)
                    _sum = float(_base) + float(_op) + float(_arb) + float(_rari)
                    key, value = get_max_from_map({'base': _base, 'opt': _op, 'arb': _arb, 'rari': _rari})

    if result and result['success'] and float(result['balance_eth']) <= 0.7:
        _gas = __quyer_gas()
        if _gas is not None:
            _low_gas = _gas.get('SafeGasPrice', '99')
            if _low_gas is not None and float(_low_gas) < 0.3:
                _sw = True
                if not (4291 <= emv_id_int <= 9290):
                    __add_net_work(page=page, coin_name=key)
                    _url = ''
                    if key == 'base':
                        _url = 'https://relay.link/bridge/apechain?fromChainId=8453'
                    elif key == 'opt':
                        _url = 'https://relay.link/bridge/apechain?fromChainId=10'
                    elif key == 'arb':
                        _url = 'https://relay.link/bridge/apechain?fromChainId=42161'
                    elif key == 'rari':
                        _url = 'https://relay.link/bridge/apechain?fromChainId=1380012617'

                    _end_mon = round(random.uniform(0.0001207, 0.0001425), 6)
                    __send_end_wallet(page, evm_id, None, _end_mon, _url, 0.06, 0, f'eth_apechain')
                    # 0.0001207 0.0001425   0.05
                else:
                    wallet_page = __get_page('wallet', '88102', '34533', False)
                    __handle_signma_popup(page=wallet_page, count=0)
                    __login_wallet(page=wallet_page, evm_id='88102')
                    __handle_signma_popup(page=wallet_page, count=0)
                    __add_net_work(page=wallet_page, coin_name='base')
                    __handle_signma_popup(page=wallet_page, count=0)
                    _url = 'https://relay.link/bridge/apechain?fromChainId=8453'
                    _send_mon = round(random.uniform(0.0001207, 0.0001425), 6)
                    __send_end_wallet(wallet_page, '88102', evm_addr, _send_mon, _url, 0.06, 0, f'eth_88102_apechain')
                    if wallet_page is not None:
                        try:
                            wallet_page.quit()
                        except Exception:
                            logger.exception("退出错误")
    if _sw:
        result = get_ape_balance(evm_addr)
        _base = get_eth_balance("base", evm_addr)
        _op = get_eth_balance("opt", evm_addr)
        _arb = get_eth_balance("arb", evm_addr)
        _rari = get_eth_balance("rari", evm_addr)
        _sum = float(_base) + float(_op) + float(_arb) + float(_rari)
    if 4291 <= emv_id_int <= 9290:
        if result and result['success'] and float(result['balance_eth']) >= 0.7:
            _bool = True
    else:
        if _sum >= emd_w and result and result['success'] and float(result['balance_eth']) >= 0.7:
            _bool = True

    signma_log(message=f"{evm_addr},{_bool},{_base},{_op},{_arb},{_rari},{result['balance_eth']},{_sum:.18f}", task_name=f'ape_task_{get_date_as_string()}', index=evm_id)
    return _bool



def get_max_from_map(data_map):
    if not data_map:
        return None, None
    max_key = max(data_map, key=data_map.get)
    max_value = data_map[max_key]
    return max_key, max_value



def vf_cf(_nexus, _index, _name:str = "quest.nexus.xyz"):
    _bool = False
    for i in range(5):
        time.sleep(4)
        if __get_ele(page=_nexus, xpath=f'x://h1[contains(text(), "{_name}")]', loop=1):
            time.sleep(5)
            click_x_y(524 + random.randint(1, 28), 393 + random.randint(1, 8), _index)
            time.sleep(10)
            _bool = False
        else:
            _bool = True
            break
    return _bool


# 添加网络
def __add_net_work(page, coin_name='base'):
    obj = {
        'arb': 42161,
        'base': 8453,
        'opt': 10,
        'hemi': 43111,
        'arbitrum': 42161,
        'linea': 59144,
        'appChain': 466,
        'rari': 1380012617,
        'apechain': 33139,
    }
    number = obj[coin_name]
    chain_page = page.new_tab(f'https://chainlist.org/?search={number}&testnets=false')
    try:
        if __click_ele(page=chain_page, xpath='x://button[text()="Connect Wallet"]', loop=1):
            __handle_signma_popup(page=page, count=1)
        __click_ele(page=chain_page,
                    xpath=f'x://td[contains(text(), "{number} ")]/../../../following-sibling::button[1]')
        __handle_signma_popup(page=page, count=1, timeout=5)
    except Exception as e:
        error = e
        pass
    finally:
        chain_page.close()
    return True


def __select_net(page, net_name, net_name_t: str = None, add_net: str = None):
    if net_name_t is None:
        net_name_t = net_name
    wallet_page = page.new_tab(f'chrome-extension://{evm_ext_id}/popup.html')
    if __click_ele(page=wallet_page, xpath='x://button[@data-testid="top_menu_network_switcher"]', loop=2):
        if __click_ele(page=wallet_page,
                       xpath=f'x://li[div[div[contains(text(), "{net_name}") or contains(text(), "{net_name_t}")]]]',
                       loop=5):
            time.sleep(5)
        else:
            if add_net is not None:
                __add_net_work(page=page, coin_name=add_net)
    wallet_page.close()


# ========== 主流程 ==========

if __name__ == '__main__':
    _this_day = ''
    _end_day_task = []
    TASK_TYPES = {'prismax_home'}
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--ip", type=str, help="ip参数", default="127.0.0.1")
    parser.add_argument("--display", type=str, help="X11 DISPLAY", default=":24")
    parser.add_argument("--base-port", type=int, help="本地调试端口", default=29541)
    TASK_TYPES_PRISMAX = {'prismax_home'}
    args = parser.parse_args()
    ARGS_IP = args.ip or ""
    _window = args.display.lstrip(':')
    evm_id = ""
    _task = ""
    _type = ""
    while True:
        _this_day_tmp = datetime.now().strftime("%Y-%m-%d")
        if _this_day != _this_day_tmp:
            _end_day_task = []
            _this_day = _this_day_tmp

        today = datetime.today().date()
        if platform.system().lower() == "windows":
            tasks = read_data_list_file("./tasks.txt")
            end_tasks = read_data_list_file("./end_tasks.txt")
        else:
            tasks = read_data_list_file("/home/ubuntu/task/tasks/tasks.txt")
            end_tasks = read_data_list_file("/home/ubuntu/task/tasks/end_tasks.txt")
        logger.info(f'开始执行{ARGS_IP}:{_window}:{args.display}:{len(tasks)}')
        # 统一设置 DISPLAY
        os.environ['DISPLAY'] = f':{_window}'

        # 过滤：保留“今天及以前”的数据；并排除已完成（end_tasks）之外的行
        filtered = []
        filtered_paismax = []
        for line in tasks:
            parts = line.split("||")
            if len(parts) < 3:
                logger.warning(f"任务行格式不正确，跳过：{line!r}")
                continue
            date_str = parts[2]
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"日期解析失败，跳过：{date_str!r} in {line!r}")
                continue
            # 需求：获取今天之前（含今天）的数据，且未完成；另外 parts[0]=='0' 也保留
            if (parts[1] == '0' and parts[0] not in _end_day_task) or (
                    parts[1] != '0' and date_obj <= today and parts[0] not in end_tasks):
                # if parts[1] == '0' or (parts[0] not in end_tasks):
                _argsa = parts[3].split(",")
                # logger.info(f'添加执行今日任务leix :{_argsa[0]}')
                if _argsa[0] in TASK_TYPES:
                    if _argsa[0] in TASK_TYPES_PRISMAX:
                        logger.info(f'添加执行今日机器人任务:{line}')
                        filtered_paismax.append(line)
                    else:
                        if _argsa[0] == 'camelot_apechain':
                            filtered.append(line)
                            if random.choice([True, False]):
                                filtered.append(line)
                        # if _argsa[0] == 'swap_op_arb_base':
                        #     if random.choice([True, False]):
                        #         filtered.append(line)
                        logger.info(f'添加执行今日任务:{line}')
                        filtered.append(line)

        if len(filtered) > 0:
            for part in filtered:
                _page = None
                _end = False
                _task_id = ''
                _task_type = ''
                try:
                    parts = part.split("||")
                    if len(parts) < 4:
                        logger.warning(f"任务参数不足，跳过：{part!r}")
                        continue

                    port = args.base_port
                    _task_id = parts[0]
                    _task_type = parts[1]
                    arg = parts[3].split(",")
                    _task = parts[3]

                    if len(arg) < 2:
                        logger.warning(f"任务 arg 参数不足，跳过：{parts[3]!r}")
                        continue

                    _type = arg[0]
                    _id = arg[1]
                    logger.info(f'开始数据:{_task_type}:{_task_id}')
                    if _type in TASK_TYPES:
                        logger.warning(f"启动任务1:{_type}:{part}")


                        if _type == 'prismax_home':
                            _end = True
                        else:
                            _home_ip = False
                            # if _type == 'nexus_joina':
                            #     _home_ip = check_available(_id)
                            #     if _home_ip:
                            #         logger.info('加载住宅ip')
                            #     else:
                            #         break
                            _page = __get_page(_type, _id, None, _home_ip)
                            if _page is None:
                                logger.error("浏览器启动失败，跳过该任务")
                                continue
                            if _type == 'eth_end':
                                _end = __eth_to_op_arb_base(page=_page , evm_id=_id, evm_addr=arg[2])
                            else:
                                logger.warning(f"未知任务类型：{_type}")
                except Exception as e:
                    logger.info(f"任务异常: {e}")
                finally:
                    logger.info(f'结束数据:{_task_type}:{_task_id}')
                    if _page is not None:
                        try:
                            _page.quit()
                        except Exception:
                            logger.exception("退出错误")
                    # if _type:
                    if _type in TASK_TYPES:
                        logger.info(f'数据{_end}:{_task_type}:{_task_id}')
                        if _end and _task_id:
                            if _task_type != '0':
                                if platform.system().lower() != "windows":
                                    append_date_to_file(file_path="/home/ubuntu/task/tasks/end_tasks.txt",
                                                        data_str=_task_id)
                                else:
                                    append_date_to_file(file_path="E:/tmp/chrome_data/end_tasks.txt", data_str=_task_id)
                            else:
                                _end_day_task.append(_task_id)
                        else:
                            signma_log(message=f"{_type},{_task_id},{_task}",
                                       task_name=f'error_task_{get_date_as_string()}', index=evm_id)
        else:
            time.sleep(60)