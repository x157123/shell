import requests
from DrissionPage import ChromiumPage, ChromiumOptions
import time
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
import pyperclip


# ========== 全局配置 ==========
evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"
ARGS_IP = ""  # 在 main 里赋值


def __get_page(_type, _id, _port):
    _pages = None
    logger.info(f"启动类型: {_type}")
    options = ChromiumOptions()
    if platform.system().lower() == "windows":
        options.set_browser_path(r"F:\chrome_tool\127.0.6483.0\chrome.exe")
    else:
        options.set_browser_path('/opt/google/chrome')

    if _type == 'prismax':
        if platform.system().lower() == "windows":
            options.add_extension(f"F:/chrome_tool/phantom")
        else:
            options.add_extension(f"/home/ubuntu/extensions/phantom")
    else:
        if platform.system().lower() == "windows":
            options.add_extension(f"F:/chrome_tool/signma")
        else:
            options.add_extension(f"/home/ubuntu/extensions/chrome-cloud")
    # 用户数据目录
    if platform.system().lower() == "windows":
        options.set_user_data_path(f"F:/tmp/chrome_data/{_type}/{_id}")
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
        _pages.set.window.max()

    logger.info('初始化结束')
    return _pages


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
                find_all: bool = False, index: int = 0) -> bool:
    for i in range(1, loop + 1):
        try:
            if not find_all:
                logger.info(f'点击按钮:{xpath}')
                ele = page.ele(locator=xpath, timeout=2)
                if ele:
                    ele.click()
                    return True
            else:
                eles = page.eles(locator=xpath, timeout=2)
                if eles and 0 <= index < len(eles):
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

                elif 'ohgmkpjifodfiomblclfpdhehohinlnn' in tab.url:
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


def __close_popup(page, _url: str = '', timeout: int = 15):
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
        for tab in page.get_tabs():
            if _url in tab.url:
                try:
                    tab.close()
                except Exception as e:
                    logger.debug(f"关闭弹窗失败：{e}")


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


def __do_task_linea(page, evm_id, index):
    __bool = False
    try:
        __handle_signma_popup(page=page, count=0)
        time.sleep(3)
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)

        __add_net_work(page=page, coin_name='linea')

        logger.info('已登录钱包')

        main_page = page.new_tab(url="https://linea.build/hub/rewards")

        shadow_host = main_page.eles('x://div[@id="dynamic-widget"]')
        if shadow_host:
            shadow_root = shadow_host[1].shadow_root
            if shadow_root:
                continue_button = __get_ele(page=shadow_root, xpath="x://button[@data-testid='ConnectButton']")
                if continue_button:
                    continue_button.click(by_js=False)


    except Exception as e:
        logger.info(f"窗口{index}: 处理任务异常: {e}")
    return __bool


def __do_task_portal(page, evm_id, index):
    __bool = False
    try:
        __handle_signma_popup(page=page, count=0)
        time.sleep(3)
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        logger.info('已登录钱包')

        main_page = page.new_tab(url="https://portal.abs.xyz/")
        time.sleep(5)
        if __get_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="Login with Wallet"]]', loop=4):
            time.sleep(5)
            click_x_y(363, 755, index)
            if __get_ele(page=main_page, xpath='x://div[normalize-space(.)="Other wallets"]/ancestor::button[1]',
                         loop=2):
                logger.info('点击成功')
            else:
                click_x_y(363, 755, index)
                time.sleep(1)
            if __get_ele(page=main_page, xpath='x://div[normalize-space(.)="Other wallets"]/ancestor::button[1]',
                         loop=20):
                time.sleep(2)
                click_x_y(437, 740, index)
                if __get_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="Signma"]]', loop=10):
                    time.sleep(2)
                    click_x_y(414, 524, index)
                    __handle_signma_popup(page=page, count=2, timeout=60)
                    time.sleep(20)

        __click_ele(page=main_page, xpath='x://button[normalize-space(.)="Skip"]', loop=5)

        main_page.get("https://portal.abs.xyz/profile")
        __click_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="Send"]]', loop=5)

        if 88111 <= int(evm_id) <= 89110:
            __input_ele_value(page=main_page, xpath='x://input[@placeholder="Address, domain or identity"]',
                              value='0xc0c828e71C462971F3105454592DbeFBd21D2BDb')
        else:
            __input_ele_value(page=main_page, xpath='x://input[@placeholder="Address, domain or identity"]',
                              value='0xf5eEE81fCD4b07CB6EcD3357d618312102230256')

        __click_ele(page=main_page, xpath='x://article[.//p[starts-with(normalize-space(.),"Balance:")]]/button',
                    loop=1)

        # __click_ele(page=main_page, xpath='x://button[contains(@class,"styles_switchButton__") and contains(@class,"styles_token__")]', loop=1)

        time.sleep(5)

        lis = main_page.eles(
            'x://ul[contains(@class,"styles_container__")]/li['
            'number(translate((.//h4[starts-with(normalize-space(.), "$")])[1], "$,", "")) > 0]'
        )

        data = []
        for li in lis:
            name = (li.ele('x:.//p[contains(@class,"styles_description__")]') or
                    li.ele('x:.//h4[not(starts-with(normalize-space(.), "$"))]')).text
            usd = li.ele('x:.//h4[starts-with(normalize-space(.), "$")]').text  # 如 "$2.1412"

            signma_log(message=f"{name},{usd}", task_name=f'portal_point_{get_date_as_string()}', index=evm_id)
            __bool = True
        time.sleep(5)
        # __click_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="25%"]]', loop=1)
        # time.sleep(5)
        # __click_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="75%"]]', loop=1)
        # time.sleep(5)
        # __click_ele(page=main_page, xpath='x://button[normalize-space(.)="Review Tokens" and not(@disabled)]', loop=1)
        # time.sleep(2)
        # __click_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="Send"]]', loop=1)
        #
        # time.sleep(5)
        # # PENGU         ABSTER
        # time.sleep(3000)

    except Exception as e:
        logger.info(f"窗口{index}: 处理任务异常: {e}")
    return __bool


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

    if send_evm_addr is not None:
        if __click_ele(page=w_page, xpath="x://div[contains(text(), 'Buy')]/following-sibling::button[@aria-label='Multi wallet dropdown']", loop=2):
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
                            signma_log(message=f"send,{amount},{gas_fee},{_url}", task_name=f'wallet_gift_{get_date_as_string()}', index=evm_id)
                            _bool = True
    if w_page is not None:
        w_page.close()
    return _bool

def __send_end_wallet(wallet_page, evm_id, send_evm_addr, amount, _url, max_gas_fee, end_amount, _type):
    _bool = False
    w_page = None
    try:
        w_page = wallet_page.new_tab(url=_url)
        if __click_ele(page=w_page, xpath='x://button[text()="Connect Wallet"]', loop=3):
            els = __get_ele(page=w_page, xpath='x://div[@data-testid="dynamic-modal-shadow"]')
            if els and els.shadow_root:
                if __click_ele(page=els.shadow_root, xpath='x://button/div/span[text()="Signma"]', loop=1):
                    __handle_signma_popup(page=wallet_page, count=1)
                else:
                    __click_ele(page=els.shadow_root, xpath='x://button[@data-testid="close-button"]', loop=1)
                time.sleep(2)

        if send_evm_addr is not None:
            if __click_ele(page=w_page, xpath="x://div[contains(text(), 'Buy')]/following-sibling::button[@aria-label='Multi wallet dropdown']", loop=2):
                if __click_ele(page=w_page, xpath='x://div[text()="Paste wallet address"]'):
                    __input_ele_value(page=w_page, xpath='x://input[@placeholder="Address or ENS"]', value=send_evm_addr)
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

        if 0 <= float(send_amount) <= 0.2:
            _bool = True
        else:
            gas_fee = round(float(send_amount) - float(receive_amount), 3)
            if float(gas_fee) > max_gas_fee:
                logger.error(f'{gas_fee} 地址 {send_evm_addr}')
                signma_log(message=f"gas_fee,{amount},{gas_fee},{_url}", task_name=f'wallet_{_type}', index=evm_id)

            elif __click_ele(page=w_page, xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]'):
                __handle_signma_popup(page=wallet_page, count=3)
                __handle_signma_popup(page=wallet_page, count=0)
                if __get_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                    if __get_ele(page=w_page, xpath='x://button[text()="View Details"]', loop=1):
                        if __click_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                            time.sleep(2)
                            signma_log(message=f"send,{amount},{gas_fee},{_url}", task_name=f'wallet_{_type}', index=evm_id)
                            _bool = True
                    else:
                        if __click_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                            if __click_ele(page=w_page, xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]'):
                                __handle_signma_popup(page=wallet_page, count=3)
                                __handle_signma_popup(page=wallet_page, count=0)
                                if __get_ele(page=w_page, xpath='x://button[text()="Done"]', loop=5):
                                    __get_ele(page=w_page, xpath='x://button[text()="View Details"]', loop=1)
                                    time.sleep(2)
                                    signma_log(message=f"send,{amount},{gas_fee},{_url}", task_name=f'wallet_{_type}', index=evm_id)
                                    _bool = True
    except Exception as e:
        logger.info(f"{evm_id}: 处理任务异常: {e}")
    if w_page is not None:
        w_page.close()
    return _bool

def __do_send_wallet(evm_id, send_evm_addr, amount):
    _bool = False
    wallet_page = None
    try:
        wallet_page = __get_page('wallet', evm_id, '34533')
        __login_wallet(page=wallet_page, evm_id=evm_id)
        __add_net_work(page=wallet_page, coin_name='base')
        urls = ["https://relay.link/bridge/rari?fromChainId=8453", "https://relay.link/bridge/appchain?fromChainId=8453", "https://relay.link/bridge/arbitrum?fromChainId=8453"]
        _url = random.choice(urls)
        _bool = __send_wallet(wallet_page, evm_id, send_evm_addr, amount, _url, 0.05, 0)
    except Exception as e:
        logger.info(f"钱包转账异常{send_evm_addr}：{e}")
    finally:
        if wallet_page is not None:
            wallet_page.quit()
    return _bool



def eth_get_balance_once(url: str, address: str) -> Decimal:
    SESSION = requests.Session()
    HEADERS = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1
    }
    r = SESSION.post(
        url,
        headers=HEADERS,
        data=json.dumps(payload),
        timeout=12,
        verify=True,
        proxies=None,
    )
    r.raise_for_status()
    data = r.json()
    if "result" in data and isinstance(data["result"], str):
        wei = int(data["result"], 16)
        return Decimal(wei) / Decimal(10**18)
    raise RuntimeError(str(data.get("error", "unknown error")))


def get_eth_balance(chain: str, address: str) -> str:
    RPC_URLS = {
        "base": ["https://mainnet.base.org"],
        "op": ["https://mainnet.optimism.io"],
        "arb": ["https://arb1.arbitrum.io/rpc"],
        "rari": [
            os.getenv("RARI_RPC") or "https://mainnet.rpc.rarichain.org/http",
            "https://1380012617.rpc.thirdweb.com",
            "https://rari.calderachain.xyz/http",
            ],
    }
    errors = []
    for url in RPC_URLS[chain]:
        for attempt in range(1, 6):
            try:
                eth = eth_get_balance_once(url, address)
                return f"{eth:.18f}"
            except Exception as e:
                errors.append(f"{url}#{attempt}: {e}")
                time.sleep(1.0)
    recent = " | ".join(errors[-3:]) if errors else "unknown"
    return "查询失败: " + recent


def __do_task_gift(page, evm_id, index, evm_addr, amount):
    __bool = False
    _bool = True
    try:
        if _bool:
            _bool = False
            time.sleep(1)
            __handle_signma_popup(page=page, count=0)
            time.sleep(2)
            __login_wallet(page=page, evm_id=evm_id)
            __handle_signma_popup(page=page, count=0)
            logger.info('已登录钱包')

            arb = get_eth_balance("arb", evm_addr)
            rari = get_eth_balance("rari", evm_addr)
            if float(arb) > 0.00005 and float(rari) > 0.00005:
                urls = ["https://relay.link/bridge/appchain?fromChainId=1380012617", "https://relay.link/bridge/appchain?fromChainId=42161"]
                _url = random.choice(urls)
                if _url == 'https://relay.link/bridge/appchain?fromChainId=1380012617':
                    _bool = __send_wallet(page, evm_id, None, 'Max', _url, 0.05, 0.00003)
                elif _url == 'https://relay.link/bridge/appchain?fromChainId=42161':
                    _bool = __send_wallet(page, evm_id, None, 'Max', _url, 0.05, 0.00001)
            elif float(arb) > 0.00005 > float(rari):
                _bool = __send_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/appchain?fromChainId=42161", 0.05, 0.00001)
            elif float(arb) < 0.00005 < float(rari):
                _bool = __send_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/appchain?fromChainId=1380012617", 0.05, 0.00003)

            __select_net(page=page, net_name='AppChain', net_name_t='Appchain', add_net='appChain')
            if _bool:
                num = random.randint(1, 5)
                if num <= 1:
                    main_page = page.new_tab(url="https://gift.xyz/1m-transactions-on-appchain")
                else:
                    main_page = page.new_tab(url="https://gift.xyz/")

                if __click_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="Sign in"]]', loop=2):
                    if __click_ele(page=main_page, xpath='x://span[normalize-space(.)="Sign in with Wallet"]/ancestor::button[1]', loop=5):
                        __click_ele(page=main_page, xpath='x://button[.//span[normalize-space(.)="Signma"]]', loop=5)
                        __handle_signma_popup(page=page, count=2)
                        time.sleep(5)
                        __handle_signma_popup(page=page, count=0)


                collect = main_page.eles("x://button[contains(normalize-space(.),'Collect')]")
                random.choice(collect).click()
                result = ''.join(random.choices(string.ascii_lowercase, k=(random.randint(5, 8))))
                __input_ele_value(page=main_page, xpath='x://input[@placeholder="Add message (optional)"]', value=result)
                if __click_ele(page=main_page, xpath='x://button[.//p[normalize-space(.)="Collect"]]', loop=2):
                    __handle_signma_popup(page=page, count=2)
                    if __get_ele(page=main_page, xpath="x://p[contains(normalize-space(.),'Collected Successfully!')]", loop=4):
                        signma_log(message=f"gift_nft", task_name=f'task_{get_date_as_string()}', index=evm_id)

                if main_page is not None:
                    main_page.close()

            if __send_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/rari?fromChainId=466", 0.1, 0.000005):
                __bool = True
    except Exception as e:
        logger.info(f"窗口{index}: 处理任务异常: {e}")
    return __bool


def __quyer_gas():
    params = {
        'module': 'gastracker',
        'action': 'gasoracle',
        'apikey': 'XGGFY4ZK56YAWC5U3698BQNH7W8RRHF954'
    }
    try:
        response = requests.get('https://api.etherscan.io/api', params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data['status'] == '1':
            return data['result']
        else:
            print(f"API返回错误: {data.get('message', '未知错误')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return None

def get_balance(rpc_url: str, address: str, unit: str) -> dict:
    """查询指定地址的余额"""
    try:
        # 连接到 AppChain
        web3 = Web3(Web3.HTTPProvider(rpc_url))

        # 检查连接
        if not web3.is_connected():
            return {"error": "无法连接到 AppChain"}

        # 检查地址格式并转换为校验和地址
        if not Web3.is_address(address):
            return {"error": "无效的地址格式"}

        # 转换为正确的校验和地址格式
        address = Web3.to_checksum_address(address)

        # 查询余额
        balance_wei = web3.eth.get_balance(address)
        balance_ether = Web3.from_wei(balance_wei, unit)

        return {
            "address": address,
            "balance": balance_ether,
            "success": True
        }
    except Exception as e:
        return {"error": f"查询失败: {str(e)}", "success": False}


def __do_end_eth(page, evm_id, evm_addr, _type, _amount):
    _end_bool = False
    _gas = __quyer_gas()
    if _gas is not None:
        _low_gas = _gas.get('SafeGasPrice', '99')
        if _low_gas is not None and float(_low_gas) < 1.8:
            logger.info(f'获取gas成功:{_low_gas}')
            __handle_signma_popup(page=page, count=0)
            __login_wallet(page=page, evm_id=evm_id)
            __handle_signma_popup(page=page, count=0)
            # 查询eth金额
            if _amount == '000':
                result = get_balance("https://bsc-dataseed.binance.org/", evm_addr, 'ether')
                _bool = False
                if result.get("success"):
                    if float(result['balance']) >= 0.00002:
                        _bool = True
                    else:
                        _amount = random.uniform(0.000611, 0.000720)
                        _bool = __send_end_wallet(page, evm_id, None, _amount, "https://relay.link/bridge/bsc?fromChainId=1", 0.2, 0, 'bnb')
                if _bool:
                    if _type == '1' or _type == '3' or _type == '5':
                        _end_bool = __send_end_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/base?fromChainId=56", 0.1, 0, 'base')
                    elif _type == '2' or _type == '4' or _type == '6':
                        _end_bool = __send_end_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/arbitrum?fromChainId=56", 0.1, 0, 'arb')
            else:
                if _type == '1':
                    # https://relay.link/bridge/base?fromChainId=1          eth 转 base  1
                    _bool = __send_end_wallet(page, evm_id, None, _amount, "https://relay.link/bridge/base?fromChainId=1", 0.1, 0, 'base')
                    if _bool:
                        _end_bool = __send_end_wallet(page, evm_id, '0xb3d4984fa477e5d4ce4158cf0f9365561657b1c1', 'Max', "https://relay.link/bridge/optimism?fromChainId=8453", 0.1, 0, 'op')
                elif _type == '2':
                    # https://relay.link/bridge/arbitrum?fromChainId=1      eth 转 arb   2
                    _bool = __send_end_wallet(page, evm_id, None, _amount, "https://relay.link/bridge/arbitrum?fromChainId=1", 0.1, 0, 'arb')
                    if _bool:
                        _end_bool = __send_end_wallet(page, evm_id, '0xb3d4984fa477e5d4ce4158cf0f9365561657b1c1', 'Max', "https://relay.link/bridge/optimism?fromChainId=42161", 0.1, 0, 'op')

                elif _type == '3' or _type == '4':
                    result = get_balance("https://mainnet.rpc.rarichain.org/http", evm_addr, 'ether')
                    if result.get("success"):
                        logger.info(f"余额: {result['balance']}")
                        _end_mon = 0
                        if float(result['balance']) > 0.0015:
                            _end_mon = random.uniform(0.00061, 0.00072)
                        else:
                            _end_mon = float(result['balance'])
                        # https://relay.link/bridge/rari?fromChainId=1          eth 转 rari      3\4
                        _bool = __send_end_wallet(page, evm_id, None, _amount, "https://relay.link/bridge/rari?fromChainId=1", 0.1, 0, 'rari')
                        if _bool:
                            if _type == '3':
                                # https://relay.link/bridge/base?fromChainId=1380012617  rari 转 base        3
                                _bool = __send_end_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/base?fromChainId=1380012617", 0.1,  _end_mon, 'base')
                                if _bool:
                                    _end_bool = __send_end_wallet(page, evm_id, '0xb3d4984fa477e5d4ce4158cf0f9365561657b1c1', 'Max', "https://relay.link/bridge/optimism?fromChainId=8453", 0.1, 0, 'op')
                            else:
                                # https://relay.link/bridge/arbitrum?fromChainId=1380012617  rari 转 arb     4
                                _bool = __send_end_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/arbitrum?fromChainId=1380012617", 0.1,  _end_mon, 'arb')
                                if _bool:
                                    _end_bool = __send_end_wallet(page, evm_id, '0xb3d4984fa477e5d4ce4158cf0f9365561657b1c1', 'Max', "https://relay.link/bridge/optimism?fromChainId=42161", 0.1, 0, 'op')

                elif _type == '5' or _type == '6':
                    result = get_balance("https://rpc.appchain.xyz/http", evm_addr, 'ether')
                    if result.get("success"):
                        logger.info(f"余额: {result['balance']}")
                        _end_mon = 0
                        if float(result['balance']) > 0.0015:
                            _end_mon = random.uniform(0.00061, 0.00072)
                        else:
                            _end_mon = float(result['balance'])
                        # https://relay.link/bridge/appchain?fromChainId=1      eth 转 appchain  5\6
                        _bool = __send_end_wallet(page, evm_id, None, _amount, "https://relay.link/bridge/appchain?fromChainId=1", 0.1, 0, 'appchain')
                        if _bool:
                            if _type == '5':
                                # https://relay.link/bridge/base?fromChainId=466  appchain 转 base           5
                                _bool = __send_end_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/base?fromChainId=466", 0.1, _end_mon, 'base')
                                if _bool:
                                    _end_bool = __send_end_wallet(page, evm_id, '0xb3d4984fa477e5d4ce4158cf0f9365561657b1c1', 'Max', "https://relay.link/bridge/optimism?fromChainId=8453", 0.1, 0, 'op')
                            else:
                                # https://relay.link/bridge/arbitrum?fromChainId=466  appchain 转 arb        6
                                _bool = __send_end_wallet(page, evm_id, None, 'Max', "https://relay.link/bridge/arbitrum?fromChainId=466", 0.1, _end_mon, 'arb')
                                if _bool:
                                    _end_bool = __send_end_wallet(page, evm_id, '0xb3d4984fa477e5d4ce4158cf0f9365561657b1c1', 'Max', "https://relay.link/bridge/optimism?fromChainId=42161", 0.1, 0, 'op')

    return _end_bool


def get_key(url):
    """
    发送GET请求到本地服务器获取key信息
    """
    try:
        # 发送GET请求
        response = requests.get(url)

        # 检查请求是否成功
        if response.status_code == 200:
            # 解析JSON响应
            data = response.json()
            print(f"请求成功！")
            print(f"Key: {data['key']}")
            return data['key']
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        print("连接错误：无法连接到服务器")
    except requests.exceptions.Timeout:
        print("请求超时")
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
    except json.JSONDecodeError:
        print("响应不是有效的JSON格式")

    return None


def extract_inviter_code_regex(url):
    """
    使用正则表达式提取inviterCode
    """
    pattern = r'inviterCode=([^&]+)'
    match = re.search(pattern, url)

    if match:
        return match.group(1)
    return None


def __do_quackai(page, evm_id):
    __bool = False
    try:
        __handle_signma_popup(page=page, count=0)
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        key = get_key("http://150.109.5.143:5000/get_key")
        inviter_code_regex = '0000'
        if key is not None and key != "0000":
            questions = read_data_list_file("/home/ubuntu/task/tasks/questions.txt")
            # questions = read_data_list_file("./questions.txt")
            main_page = page.new_tab(url=f"https://app.quackai.ai/quackipedia?inviterCode={key}")
            __click_ele(page=main_page, xpath='x://button[contains(text(), "Next")]', loop=1)
            __click_ele(page=main_page, xpath='x://button[contains(text(), "Next")]', loop=1)
            __click_ele(page=main_page, xpath='x://button[contains(text(), "Explore")]', loop=1)
            if __get_ele(page=main_page, xpath='x://button[div[div[contains(text(), "Connect Wallet")]]]', loop=2):
                __click_ele(page=main_page, xpath='x://button[div[div[contains(text(), "Connect Wallet")]]]', loop=1)
                if __click_ele(page=main_page, xpath='x://button[div[div[div[div[contains(text(), "Signma")]]]]]', loop=2):
                    __handle_signma_popup(page=page, count=2)
                    time.sleep(5)
                    __handle_signma_popup(page=page, count=0)

                if __get_ele(page=main_page, xpath='x://button[div[div[contains(text(), "Connect Wallet")]]]', loop=2):
                    __click_ele(page=main_page, xpath='x://button[div[div[contains(text(), "Connect Wallet")]]]', loop=1)
                    if __click_ele(page=main_page, xpath='x://button[div[div[div[div[contains(text(), "Signma")]]]]]', loop=2):
                        __handle_signma_popup(page=page, count=2)
                        time.sleep(5)
                        __handle_signma_popup(page=page, count=0)

            if __get_ele(page=main_page, xpath='x://div[text()="GO"]/parent::div/parent::button', loop=1):
                __click_ele(page=main_page, xpath='x://div[text()="GO"]/parent::div/parent::button', loop=1)
                __handle_signma_popup(page=page, count=1)
                time.sleep(5)
                __click_ele(page=main_page, xpath='x://div[text()="GO"]/parent::div/parent::button', loop=1)
                time.sleep(30)
                __handle_signma_popup(page=page, count=1)
                __click_ele(page=main_page, xpath='x://div[text()="GO"]/parent::div/parent::button', loop=1)
                time.sleep(30)
            __click_ele(page=main_page, xpath='x://button[contains(text(), "Get Passport")]', loop=1)
            if __get_ele(page=main_page, xpath='x://button[span[div[div[contains(text(), "BNB Chain")]]]]', loop=2):
                __click_ele(page=main_page, xpath='x://button[span[div[div[contains(text(), "BNB Chain")]]]]', loop=2)
                __handle_signma_popup(page=page, count=1)
                time.sleep(5)
                __handle_signma_popup(page=page, count=0)

            time.sleep(4)
            __click_ele(page=main_page, xpath='x://div[div[div[contains(text(), "Invite to Earn")]]]',find_all=True, index=1, loop=2)
            time.sleep(4)
            clipboard_text = pyperclip.paste().strip()
            time.sleep(4)
            clipboard_text = pyperclip.paste().strip()

            logger.info(f'数据：{clipboard_text}')
            inviter_code_regex = extract_inviter_code_regex(clipboard_text)
            if inviter_code_regex is not None and len(inviter_code_regex) == 6:
                url = "http://150.109.5.143:5000/add_key"
                payload = json.dumps({
                    "key": inviter_code_regex
                })
                headers = {
                    'Content-Type': 'application/json'
                }
                response = requests.request("POST", url, headers=headers, data=payload)

            for i in range(random.randint(6, 8)):
                __input_ele_value(page=main_page, xpath='x://textarea[@placeholder="What can I help you with?"]', value=random.choice(questions))
                __click_ele(page=main_page, xpath='x://div[div[div[div[contains(text(), "Send")]]]]', loop=2)
                if __get_ele(page=main_page, xpath='x://button[span[div[div[contains(text(), "BNB Chain")]]]]', loop=2):
                    __click_ele(page=main_page, xpath='x://button[span[div[div[contains(text(), "BNB Chain")]]]]', loop=2)
                    __handle_signma_popup(page=page, count=1)
                time.sleep(10)
                if i > 5:
                    __bool = True
                if __get_ele(page=main_page, xpath='x://p[contains(text(), "Your daily chat limit has been reached")]', loop=1):
                    __bool = True
                    break
            if __bool:
                _val = __get_ele_value(page=main_page, xpath='x://span[@class="font-[Poppins]"]')
                signma_log(message=f"end,{_val},{inviter_code_regex}", task_name=f'quackai_{get_date_as_string()}', index=evm_id)
        else:
            signma_log(message=f"error,{key},{key}", task_name=f'quackai_{get_date_as_string()}', index=evm_id)

    except Exception as e:
        logger.info(f"quackai: 处理任务异常: {e}")
    return __bool


def __do_task_logx(page, evm_id, index):
    __bool = False
    try:
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        logger.info('已登录钱包')

        main_page = page.new_tab(url="https://app.logx.network/portfolio")

        _amount = wait_for_positive_amount(
            page=main_page,
            xpath='x://div[contains(normalize-space(.),"Buying Power")]/following-sibling::div[1]//span[starts-with(normalize-space(.),"$")]'
        )

        if _amount <= 0:
            if __click_ele(page=main_page, xpath='x://span[text()="Connect wallet"]', loop=1):
                if __click_ele(page=main_page,
                               xpath='x://div[contains(@class,"sc-dcJtft iIBsYu btn marg") and .//*[contains(@d,"M21.4379 21.7337")]]',
                               loop=3):
                    __handle_signma_popup(page=page, count=2)
            if __click_ele(page=main_page, xpath='x://span[text()="Establish Connection"]', loop=1):
                if __click_ele(page=main_page,
                               xpath='x://div[div[div[text()="Establish Connection"]] and contains(@class,"sc-dcJtft iIBsYu sc-NxrBK idZGaa") ]',
                               loop=1):
                    __handle_signma_popup(page=page, count=1)

            __click_ele(page=main_page, xpath='x://div[contains(@class, "sc-djTQOc bLFUQW")]', loop=1)

            _amount = wait_for_positive_amount(
                page=main_page,
                xpath='x://div[contains(normalize-space(.),"Buying Power")]/following-sibling::div[1]//span[starts-with(normalize-space(.),"$")]'
            )

        _amount_total = wait_for_positive_amount(
            page=main_page,
            xpath='x://div[contains(normalize-space(.),"Total Volume")]/following-sibling::div//span'
        )

        signma_log(message=f"{_amount},{_amount_total}", task_name=f'logx_point_{get_date_as_string()}', index=evm_id)

        if _amount > 0:
            main_page.get('https://app.logx.network/trade/BTC')

            for attempt in range(2):
                time.sleep(5)
                __click_ele(page=main_page, xpath='x://div[text()="MAX"]', loop=2)
                click_x_y(1764, 416, index)  # 坐标点击：尽量保证分辨率一致
                time.sleep(1)
                click_x_y(1764, 416, index)  # 坐标点击：尽量保证分辨率一致
                time.sleep(1)
                x = random.randint(1690, 1725)
                click_x_y(x, 540, index)
                time.sleep(1)
                click_x_y(x, 580, index)
                logger.info(f'点击倍数:{x}:{index}')
                time.sleep(2)
                if random.choice([True, False]):
                    __click_ele(page=main_page,
                                xpath='x://div[contains(@class,"sc-edLa-Dd") and normalize-space(text())="Long"]',
                                loop=2)
                    click_x_y(1610, 720, index)
                else:
                    __click_ele(page=main_page,
                                xpath='x://div[contains(@class,"sc-edLa-Dd") and normalize-space(text())="Short"]',
                                loop=2)
                    click_x_y(1770, 720, index)
                logger.info('提交')
                time.sleep(15)
                if __get_ele(page=main_page, xpath='x://div[span[text()="Flash Close"]]', loop=2):
                    break
                else:
                    main_page.refresh()
            time.sleep(random.randint(3, 5))

            for attempt in range(8):
                if __click_ele(page=main_page, xpath='x://div[span[text()="Flash Close"]]', loop=2):
                    __bool = True
                    time.sleep(3)

                time.sleep(1)
                click_x_y(1430, 934, index)

    except Exception as e:
        logger.info(f"窗口{index}: 处理任务异常: {e}")
    return __bool


def __do_task_nexus(page, evm_id, index):
    __bool = False
    try:
        logger.info('登录钱包')
        time.sleep(3)
        __handle_signma_popup(page=page, count=0)
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)

        nexus = page.new_tab(url='https://app.nexus.xyz/rewards')
        __get_ele(page=nexus, xpath='x://a[contains(text(), "FAQ")]', loop=10)
        if __get_ele(page=nexus, xpath='x://button[div[contains(text(), "Sign in")]]', loop=1):
            __click_ele(page=nexus, xpath='x://button[div[contains(text(), "Sign in")]]', loop=1)
            shadow_host = nexus.ele('x://div[@id="dynamic-widget"]')
            if shadow_host:
                shadow_root = shadow_host.shadow_root
                if shadow_root:
                    continue_button = __get_ele(page=shadow_root, xpath="x://button[@data-testid='ConnectButton']")
                    if continue_button:
                        __click_ele(page=shadow_root, xpath="x://button[@data-testid='ConnectButton']")
                        shadow_host = nexus.ele('x://div[@data-testid="dynamic-modal-shadow"]')
                        if shadow_host:
                            shadow_root = shadow_host.shadow_root
                            if shadow_root:
                                continue_button = shadow_root.ele('x://p[contains(text(), "Continue with a wallet")]')
                                if continue_button:
                                    continue_button.click(by_js=True)
                                    time.sleep(1)
                                    signma_ele = shadow_root.ele('x://span[text()="Signma"]')
                                    if signma_ele:
                                        signma_ele.click(by_js=True)
                                        __handle_signma_popup(page=page, count=1, timeout=45)

            __handle_signma_popup(page=page, count=0)
            net_shadow_host = nexus.ele('x://div[@data-testid="dynamic-modal-shadow"]', timeout=3)
            if net_shadow_host:
                net_shadow_root = net_shadow_host.shadow_root
                if net_shadow_root:
                    newt_work = net_shadow_root.ele('x://button[@data-testid="SelectNetworkButton"]', timeout=3)
                    if newt_work:
                        newt_work.click(by_js=True)
                        __handle_signma_popup(page=page, count=1, timeout=45)

        if random.choice([True, False]):
            if __get_ele(page=nexus,
                         xpath='x://button[contains(normalize-space(.),"Claim") and contains(normalize-space(.),"Testnet NEX")]',
                         loop=2):
                __click_ele(page=nexus,
                            xpath='x://button[contains(normalize-space(.),"Claim") and contains(normalize-space(.),"Testnet NEX")]')
                time.sleep(65)
                nexus.get('https://app.nexus.xyz/rewards')

        ele = nexus.ele('x://span[contains(normalize-space(.), "NEX")]')
        if ele:
            t = ele.text.replace('\xa0', ' ').strip()
            import re
            m = re.search(r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*NEX\b', t, re.I)
            amount = (m.group(1).replace(',', '')) if m else '0'
            signma_log(message=amount, task_name=f'nexus_point_{get_date_as_string()}', index=evm_id)
            time.sleep(3)
            __bool = True
    except Exception as e:
        logger.info(f"窗口{index}: 处理任务异常: {e}")
    return __bool


# 登录 Phantom（新钱包）
def __login_new_wallet(page, evm_addr):
    time.sleep(5)
    phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa', timeout=1)
    if phantom_page is None:
        phantom_page = page.new_tab('chrome-extension://bfnaelmomeimhlpmgjnjophhpkkoljpa/popup.html')

    if __get_ele(page=phantom_page, xpath='x://button[@data-testid="unlock-form-submit-button"]', loop=2):
        __input_ele_value(page=phantom_page, xpath='x://input[@data-testid="unlock-form-password-input"]',
                          value='sdfasfd#dfff312')
        __click_ele(page=phantom_page, xpath='x://button[@data-testid="unlock-form-submit-button"]')
    else:
        phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa', timeout=1)

    if __get_ele(page=phantom_page,
                 xpath='x://button[contains(normalize-space(.), "我已经有一个钱包") or contains(normalize-space(.), "I already have a wallet")]',
                 loop=1):
        if __click_ele(page=phantom_page,
                       xpath='x://button[contains(normalize-space(.), "我已经有一个钱包") or contains(normalize-space(.), "I already have a wallet")]'):
            if __click_ele(page=phantom_page,
                           xpath='x://button[.//div[contains(normalize-space(.), "导入恢复短语") or contains(normalize-space(.), "Import Recovery Phrase")]]'):
                for i, word in enumerate(evm_addr.split(), 0):
                    __input_ele_value(page=phantom_page,
                                      xpath=f'x://input[@data-testid="secret-recovery-phrase-word-input-{i}"]',
                                      value=word)
            if __click_ele(page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]'):
                __click_ele(page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]')
                __input_ele_value(page=phantom_page, xpath='x://input[@data-testid="onboarding-form-password-input"]',
                                  value='sdfasfd#dfff312')
                __input_ele_value(page=phantom_page,
                                  xpath='x://input[@data-testid="onboarding-form-confirm-password-input"]',
                                  value='sdfasfd#dfff312')
                if __get_ele(page=phantom_page,
                             xpath='x://input[@data-testid="onboarding-form-terms-of-service-checkbox" and @aria-checked="false"]',
                             loop=1):
                    __click_ele(page=phantom_page,
                                xpath='x://input[@data-testid="onboarding-form-terms-of-service-checkbox" and @aria-checked="false"]',
                                loop=1)
                __click_ele(page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]', loop=1)
                time.sleep(1)
                __click_ele(page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]', loop=1)
                time.sleep(1)
                __click_ele(page=phantom_page,
                            xpath='x://button[contains(normalize-space(.), "继续") or contains(normalize-space(.), "Continue")]',
                            loop=1)
                time.sleep(1)
                __click_ele(page=phantom_page,
                            xpath='x://button[contains(normalize-space(.), "继续") or contains(normalize-space(.), "Continue")]',
                            loop=1)
                time.sleep(1)
                __click_ele(page=phantom_page,
                            xpath='x://button[contains(normalize-space(.), "开始") or contains(normalize-space(.), "Get Started")]',
                            loop=1)

    if phantom_page is not None:
        try:
            phantom_page.close()
        except Exception as e:
            logger.debug(f"关闭 Phantom 页面失败：{e}")


def __do_task_prismax(page, evm_id, evm_addr, index):
    __bool = False
    try:
        __login_new_wallet(page=page, evm_addr=evm_addr)

        main_page = page.new_tab(url='https://app.prismax.ai/')
        _login = True
        __get_ele(page=main_page, xpath='x://h3[contains(normalize-space(.), "Earnings")]')
        _wallet_but = __get_ele(page=main_page, xpath='x://div[text()="Connect Wallet"]', loop=1)
        if _wallet_but:
            main_page.actions.move_to(_wallet_but).click()
            time.sleep(4)
            if __click_ele(page=main_page,
                           xpath='x://div[contains(@class,"ConnectWalletHeader_connectOption") and .//p[normalize-space()="Phantom Wallet"]]'):
                phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa/notification.html',
                                           timeout=3)
                if phantom_page is not None:
                    if __get_ele(page=phantom_page, xpath='x://input[@data-testid="unlock-form-password-input"]',
                                 loop=1):
                        __input_ele_value(page=phantom_page,
                                          xpath='x://input[@data-testid="unlock-form-password-input"]',
                                          value='sdfasfd#dfff312')
                        if __click_ele(page=phantom_page, xpath='x://button[contains(normalize-space(.), "解锁")]'):
                            logger.info('解锁账号')
                    __click_ele(page=phantom_page, xpath='x://button[@data-testid="primary-button"]', loop=1)
                phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa/popup.html', timeout=3)
                if phantom_page is not None:
                    __click_ele(page=phantom_page, xpath='x://button[@data-testid="primary-button"]', loop=1)
            time.sleep(5)

        _wallet_but = __get_ele(page=main_page, xpath='x://div[text()="Connect Wallet"]', loop=1)
        if _wallet_but:
            main_page.get(url='https://app.prismax.ai/')
            __get_ele(page=main_page, xpath='x://h3[contains(normalize-space(.), "Earnings")]')
            time.sleep(10)
            _wallet_but = __get_ele(page=main_page, xpath='x://div[text()="Connect Wallet"]', loop=1)
            main_page.actions.move_to(_wallet_but).click()
            time.sleep(4)
            if __click_ele(page=main_page,
                           xpath='x://div[contains(@class,"ConnectWalletHeader_connectOption") and .//p[normalize-space()="Phantom Wallet"]]'):
                phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa/notification.html',
                                           timeout=3)
                if phantom_page is not None:
                    if __get_ele(page=phantom_page, xpath='x://input[@data-testid="unlock-form-password-input"]',
                                 loop=1):
                        __input_ele_value(page=phantom_page,
                                          xpath='x://input[@data-testid="unlock-form-password-input"]',
                                          value='sdfasfd#dfff312')
                        if __click_ele(page=phantom_page, xpath='x://button[contains(normalize-space(.), "解锁")]'):
                            logger.info('解锁账号')
                    __click_ele(page=phantom_page, xpath='x://button[@data-testid="primary-button"]', loop=1)
                phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa/popup.html', timeout=3)
                if phantom_page is not None:
                    __click_ele(page=phantom_page, xpath='x://button[@data-testid="primary-button"]', loop=1)
            time.sleep(5)

            if __get_ele(page=main_page, xpath='x://div[text()="Connect Wallet"]', loop=1):
                _login = False

        if _login:
            time.sleep(2)
            num_str = __get_ele_value(page=main_page,
                                      xpath='x://span[normalize-space()="Daily Prisma Points"]/following-sibling::div/span')
            if num_str is not None:
                try:
                    if float(num_str.replace(',', '')) > 0:
                        sum_num_str = __get_ele_value(page=main_page,
                                                      xpath='x://span[normalize-space()="All-Time Prisma Points"]/following-sibling::div/span')
                        signma_log(message=(sum_num_str or "0").replace(",", ""),
                                   task_name=f'prismax_point_{get_date_as_string()}', index=evm_id)
                        __bool = True
                except ValueError:
                    logger.debug(f"Daily Prisma Points 解析失败：{num_str}")

            # 尝试问答获取积分
            main_page.get('https://app.prismax.ai/whitepaper')
            if __click_ele(page=main_page, xpath='x://button[contains(normalize-space(.), "Review answers")]', loop=1):
                logger.info('答题积分完成')
            elif __get_ele(page=main_page, xpath='x://button[contains(normalize-space(.), "Start Quiz")]', loop=2):
                # for i in range(2):
                if __get_ele(page=main_page, xpath='x://button[contains(normalize-space(.), "Start Quiz")]', loop=2):
                    __click_ele(page=main_page, xpath='x://button[contains(normalize-space(.), "Start Quiz")]', loop=2)
                    if __click_ele(page=main_page, xpath='x://button[contains(normalize-space(.), "Take the quiz")]',
                                   loop=2):
                        for offset in range(5):
                            time.sleep(random.uniform(10, 15))
                            # _select_t = __get_ele(page=main_page, xpath='x://div[span[starts-with(normalize-space(.),"Higher token prices attract") or starts-with(normalize-space(.),"Teleoperator-generated data") or starts-with(normalize-space(.),"To automatically validate data quality") or starts-with(normalize-space(.),"Data collection infrastructure is fragmented") or starts-with(normalize-space(.),"Introduction of visual data collection")]]')
                            # if _select_t:
                            #     main_page.actions.move_to(_select_t).click()
                            # time.sleep(random.uniform(2, 4))
                            _select = __get_ele(page=main_page,
                                                xpath='x://div[span[starts-with(normalize-space(.),"To incentivize speed and discover") or starts-with(normalize-space(.),"Network-owned data is community-controlled") or starts-with(normalize-space(.),"Current AI models lack sufficient") or starts-with(normalize-space(.),"Achievement of high robot autonomy") or starts-with(normalize-space(.),"More robots generate valuable datasets")]]')
                            if _select:
                                main_page.actions.move_to(_select).click()
                            _next = __get_ele(page=main_page,
                                              xpath='x://button[(@class="QuizModal_navButton__Zy2TN" and contains(normalize-space(.), "Next →")) or (@class="QuizModal_goldButton__SjXdA" and contains(normalize-space(.), "Finish Quiz →"))]')
                            if _next:
                                time.sleep(random.uniform(5, 8))
                                main_page.actions.move_to(_next).click()
                        time.sleep(10)
                    main_page.get('https://app.prismax.ai/whitepaper')
                    time.sleep(2)
    except Exception as e:
        logger.info(f"窗口{index}处理任务异常: {e}")
    return __bool


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


def __down_file(url, out_file):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        with requests.get(url, headers=headers, timeout=20, stream=True) as r:
            r.raise_for_status()
            with open(out_file, "wb") as f:
                for chunk in r.iter_content(65536):
                    if chunk:
                        f.write(chunk)
        print(f"下载成功：{out_file}  ←  {url}")
    except requests.RequestException as e:
        print(f"下载失败：{e}")


# 获取邮箱 验证码code
def __get_email_code(page, _main_page, xpath, evm_addr, index):
    email_page = page.new_tab(url='https://mail.dmail.ai/inbox')
    # 通过小狐狸钱包打开狗头钱包
    code = None
    if __get_ele(email_page, xpath=f"x://div[@title='{evm_addr}']", loop=2):
        logger.info('已登录邮箱')
    else:
        click_x_y(1764, 416, index)  # 坐标点击：尽量保证分辨率一致
        if __click_ele(page=email_page, xpath='x://span[text()="MetaMask"]', loop=10):
            __handle_signma_popup(page=page, count=2, timeout=15)
    # 首次进入邮箱
    if __click_ele(page=email_page, xpath='x://a[text()="Next step"]', loop=1):
        __click_ele(page=email_page, xpath='x://a[text()="Next step"]', loop=1)
        __click_ele(page=email_page, xpath='x://a[text()="Launch"]')
        __click_ele(page=email_page, xpath='x://div[@data-title="Setting"]')
    if __click_ele(page=email_page, xpath='x://a[text()="Next"]', loop=1):
        __click_ele(page=email_page, xpath='x://a[text()="Finish"]')
    if __get_ele(email_page, xpath='x://span[text()="Inbox"]', loop=3):
        __click_ele(email_page, xpath='x://span[text()="Inbox"]')
        # 多尝试几次
        for i in range(5):
            try:
                __click_ele(email_page, xpath='x://div[contains(@class, "icon-refresh")]', loop=20)
                time.sleep(10)
                __click_ele(email_page, xpath='x://div[contains(@class,"sc-eDPEul")]//ul/li[1]', loop=40)
                # 读取验证码
                code = __get_ele_value(page=email_page, xpath=xpath, loop=5)
                # 删除读取到的验证邮箱
                if code is not None:
                    __click_ele(email_page, xpath='x://div[@data-title="trash"]')
                    time.sleep(3)
            except Exception as e:
                logger.error(f'error ==> {e}')
            if code is None:
                if i == 2:
                    __click_ele(page=_main_page, xpath='x://button[text()="Resend code"]')
                continue  # 跳到下一次循环
            else:
                break
    # 关闭邮箱页面
    email_page.close()
    return code

def __do_task_towns(page, index, evm_id, evm_addr):
    try:
        __handle_signma_popup(page=page, count=0)
        time.sleep(2)
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        logger.info('已登录钱包')
        towns_page = page.new_tab(url='https://app.towns.com/')
        if __click_ele(page=towns_page, xpath="x://button[contains(text(), 'Log In')]", loop=2):
            if __get_ele(page=towns_page, xpath="x://button[contains(text(), 'Continue with Email')]", loop=1) is None:
                __click_ele(page=towns_page, xpath="x://button[div[contains(text(), 'More options')]]", loop=2, must=True)

            __click_ele(page=towns_page,
                        xpath="x://button[contains(text(), 'Continue with Email')]", loop=2, must=True)
            __input_ele_value(page=towns_page, xpath='x://input[@id="email-input"]',
                              value=(evm_addr.lower() + "@dmail.ai"))
            time.sleep(2)
            __click_ele(page=towns_page,
                        xpath="x://button[span[contains(text(), 'Submit')] and not(@disabled)]", loop=2, must=True)
            code = __get_email_code(page=towns_page.browser,_main_page=towns_page,
                                    xpath='x://table[@data-id="react-email-section"]//p[@data-id="react-email-text"]',
                                    evm_addr=evm_addr.lower(), index=index)
            if code is not None:
                # 查找所有 input 元素，定位到 div 下的所有 text 类型的 input
                inputs = towns_page.eles('x://div//input[@type="text"]')
                for i, input_element in enumerate(inputs):
                    # 填入对应的数字
                    input_element.input(code[i])
                time.sleep(5)

        towns_page.get("https://app.towns.com/?panel=trading-wallet&stackId=main")
        time.sleep(10)

        if __get_ele(page=towns_page, xpath='x://span[contains(normalize-space(.), "orphaned funds")]'):
            __click_ele(page=towns_page, xpath='x://span[span[span[contains(normalize-space(.), "orphaned funds")]]]')
            time.sleep(5)
            __click_ele(page=towns_page, xpath='x://span[@data-testid="max-button"]')
            time.sleep(3)
            inp = towns_page.ele('x://input[@id="ethAmount"]', timeout=3)  # 也可用 'id:amount' 或 'css:input#amount'
            val = "0"
            if inp is not None:
                val = inp.run_js('return this.value') or "0"

            __input_ele_value(page=towns_page, xpath='x://input[@data-testid="pill-selector-input"]',
                              value='0xbcd224f78a1b75821a62ebda2835429c01f7b5ec')
            __click_ele(page=towns_page,
                        xpath='x://span[@data-testid="linked-wallet-option-0xbcd224f78a1b75821a62ebda2835429c01f7b5ec"]')
            time.sleep(5)
            if __click_ele(page=towns_page, xpath='x://button[.//p[normalize-space()="Transfer"]]'):
                __click_ele(page=towns_page, xpath='x://button[.//*[contains(normalize-space(.), "Confirm")]]', loop=8)
                if __get_ele(page=towns_page, xpath="x://span[contains(text(), 'Your assets have been transferred successfully')]", loop=8):
                    time.sleep(5)
                    signma_log(message=f"{val}", task_name=f'towns_{get_date_as_string()}', index=evm_id)
        else:
            if __get_ele(page=towns_page, xpath='x://button[.//span[text()="Send"]]'):
                __click_ele(page=towns_page, xpath='x://button[.//span[text()="Send"]]')
                __click_ele(page=towns_page, xpath='x://span[@id="container"]')
                time.sleep(3)
                __click_ele(page=towns_page, xpath='x://span[@data-testid="suggested-people-list-entries"]')
                time.sleep(5)
                __click_ele(page=towns_page, xpath='x://span[@data-testid="max-button"]')
                time.sleep(3)
                inp = towns_page.ele('x://input[@id="amount"]', timeout=3)  # 也可用 'id:amount' 或 'css:input#amount'
                val = "0"
                if inp is not None:
                    val = inp.run_js('return this.value') or "0"
                __input_ele_value(page=towns_page, xpath='x://input[@data-testid="pill-selector-input"]', value='0xbcd224f78a1b75821a62ebda2835429c01f7b5ec')
                __click_ele(page=towns_page, xpath='x://span[@data-testid="linked-wallet-option-0xbcd224f78a1b75821a62ebda2835429c01f7b5ec"]')
                time.sleep(5)
                if __click_ele(page=towns_page, xpath='x://button[.//p[normalize-space()="Send"]]'):
                    __click_ele(page=towns_page, xpath="x://button[contains(text(), 'Pay with ETH')]", loop=8)

                    time.sleep(5)
                    __click_ele(page=towns_page, xpath="x://button[contains(text(), 'Pay with ETH')]", loop=2)

                    if __get_ele(page=towns_page, xpath="x://span[contains(text(), 'ETH was sent to 0xbcd...5ec')]", loop=8):
                        signma_log(message=f"{val}", task_name=f'towns_{get_date_as_string()}', index=evm_id)
                        time.sleep(5)

    except Exception as e:
        logger.info(f"未知异常 {evm_id} ：{e}")
    return True


def __do_task_nft(page, index, evm_id):
    try:
        n = random.randint(1, 22264)
        image_files = f"/home/ubuntu/task/tasks/img/img{n:05d}.png"
        __down_file(f"https://vmxjp.15712345.xyz/img/img{n:05d}.png", image_files)
        image_descriptions = read_data_list_file("/home/ubuntu/task/tasks/image_descriptions.txt", check_exists=True)
        __handle_signma_popup(page=page, count=0)
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)

        __add_net_work(page=page, coin_name='rari')
        __select_net(page=page, net_name='Rari Chain', net_name_t='RARI Chain')

        hyperbolic_page = page.new_tab(url='https://rarible.com/create/start')
        # 等待页面加载完成

        if __get_ele(page=hyperbolic_page, xpath="x://a[contains(text(), 'Create')]", loop=5):
            time.sleep(0.1)
        else:
            hyperbolic_page.refresh()
            time.sleep(2)
            if __get_ele(page=hyperbolic_page, xpath="x://a[contains(text(), 'Create')]", loop=5):
                time.sleep(0.1)
            else:
                hyperbolic_page.refresh()
        if __get_ele(page=hyperbolic_page, xpath="x://a[contains(text(), 'Create')]", loop=5):
            __click_ele(page=hyperbolic_page, xpath="x://button[.//span[contains(text(), 'RARI Chain')]]", loop=1)
            if __click_ele(page=hyperbolic_page, xpath="x://span[contains(text(), 'MetaMask')]", loop=1):
                # 确定钱包  初次钱包确认4次， 通过之后只有两次
                __handle_signma_popup(page=page, count=4, timeout=20)
            # create-single
            # 判断是否需要注册
            # if __click_ele(page=hyperbolic_page, xpath='x://input[@placeholder="Display name"]', loop=1):
            #     # 随机一个英文名
            #     __input_ele_value(page=hyperbolic_page, xpath='x://input[@placeholder="Display name"]',
            #                       value=random.choice(english_names))
            #     __click_ele(page=hyperbolic_page,
            #                 xpath="x://button[.//span[contains(text(), 'I have read and accept the')]]", loop=2)
            #     __click_ele(page=hyperbolic_page,
            #                 xpath="x://button[.//span[contains(text(), 'I want to receive announcements and news')]]",
            #                 loop=2)
            #     __click_ele(page=hyperbolic_page, xpath="x://button[.//span[contains(text(), 'Finish sign-up')]]", loop=2)

            __click_ele(page=hyperbolic_page, xpath='x://button[@id="create-single"]', loop=2)

            # 随机设置要上传的文件路径
            hyperbolic_page.set.upload_files(image_files)
            # 点击触发文件选择框按钮
            div_element = hyperbolic_page.ele('x://button[span[span[span[text()="Choose File"]]]]')
            if div_element:
                div_element.click()
                # 等待路径填入
                hyperbolic_page.wait.upload_paths_inputted()

            # 随机定价
            __input_ele_value(page=hyperbolic_page, xpath='x://input[@placeholder="Enter price"]',
                              value=str("{:.5f}".format(random.uniform(0.00051, 0.00070))))
            if __click_ele(page=hyperbolic_page, xpath='x://div[@data-marker ="create-item-expiration"]', loop=2):
                # 随机
                if random.randint(1, 3) > 1:
                    __click_ele(page=hyperbolic_page, xpath='x://span[text() ="3 Months"]', loop=2)
                else:
                    __click_ele(page=hyperbolic_page, xpath='x://span[text() ="1 Month"]', loop=2)
            __input_ele_value(page=hyperbolic_page, xpath='x://input[@data-marker="create-token-name"]',
                              value=random.choice(image_descriptions))
            __click_ele(page=hyperbolic_page, xpath='x://button[@data-marker="create-token-submit-btn"]', loop=2)

            # 钱包两次确定
            __handle_signma_popup(page=page, count=2, timeout=90)
            time.sleep(10)
            __handle_signma_popup(page=page, count=0)
            time.sleep(2)
            __handle_signma_popup(page=page, count=0)
            # 获取成功按钮 <button type="button" data-marker="mint-receipt-view-btn" class="sc-aXZVg sc-eBMEME sc-dCFHLb sc-jxOSlx sc-tagGq dAopwH ctYaUb ciBRVx iANODE"><span class="sc-cfxfcM hpAeLf"><span class="sc-gFAWRd eNTBLN">View NFT</span></span></button>
            if __get_ele(page=hyperbolic_page, xpath='x://button[span[span[text()="View NFT"]]]', loop=10):
                time.sleep(3)
                # logger.info(f'{evm_id},nft 交易成功')
                signma_log(message=f"ntf", task_name=f'task_{get_date_as_string()}', index=evm_id)
                return True
            else:
                logger.info(f'{evm_id},nft 交易未提示成功')
    except Exception as e:
        logger.info(f"未知异常 {evm_id} ：{e}")
    return False


def __do_swap_rari_arb_eth(page, evm_id):
    try:
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        logger.info('已登录钱包')
        __add_net_work(page=page, coin_name='rari')
        __select_net(page=page, net_name='Rari Chain', net_name_t='RARI Chain')
        hyperbolic_page = page.new_tab(url='https://rari.bridge.caldera.xyz')
        time.sleep(2)
        if __click_ele(page=hyperbolic_page, xpath='x://button[text()="Connect Wallet"]', loop=2):
            __click_ele(page=hyperbolic_page, xpath='x://button/div/div/div/div[text()="Signma"]', loop=1)
            __handle_signma_popup(page=page, count=1)
        if __click_ele(page=hyperbolic_page, xpath='x://button[text()="Connect Wallet"]', loop=1):
            if __click_ele(page=hyperbolic_page, xpath='x://button/div/div/div/div[text()="Signma"]', loop=1):
                __handle_signma_popup(page=page, count=1)

        from_s = __get_ele_value(page=hyperbolic_page,
                                 xpath='x://span[text()="From"]/following-sibling::span[@class="whitespace-nowrap font-medium"]')
        if from_s == 'Arbitrum One':
            __click_ele(page=hyperbolic_page, xpath='x://button[contains(text(), "Swap")]')

        value = __get_ele_value(page=hyperbolic_page, xpath='x://span[contains(@class, "truncate whitespace-nowrap")]',
                                find_all=True, index=0)
        if float(value) > 0.000401:
            amount = "{:.6f}".format(random.uniform(0.0000201, 0.0000301))
            __input_ele_value(page=hyperbolic_page, xpath='x://input[@placeholder="Amount"]', value=amount)
            time.sleep(2)
            if __click_ele(page=hyperbolic_page,
                           xpath='x://button[contains(text(), "Transfer Tokens") and not(@disabled)]', loop=3):
                if __handle_signma_popup(page=page, count=1):
                    signma_log(message=f"rari_arb", task_name=f'task_{get_date_as_string()}', index=evm_id)
                    time.sleep(5)
    except Exception as e:
        logger.info(f"未知异常 {evm_id} ：{e}")
    return True


def __do_swap_rari_arb_eth_end(page, evm_id):
    try:
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        logger.info('已登录钱包')

        __add_net_work(page=page, coin_name='arbitrum')
        __select_net(page=page, net_name='Arbitrum One', net_name_t='Arbitrum One', add_net='arbitrum')
        hyperbolic_page = page.new_tab(url='https://rari.bridge.caldera.xyz')

        time.sleep(2)
        if __click_ele(page=hyperbolic_page, xpath='x://button[text()="Connect Wallet"]', loop=2):
            __click_ele(page=hyperbolic_page, xpath='x://button/div/div/div/div[text()="Signma"]', loop=1)
            __handle_signma_popup(page=page, count=1)
        if __click_ele(page=hyperbolic_page, xpath='x://button[text()="Connect Wallet"]', loop=1):
            if __click_ele(page=hyperbolic_page, xpath='x://button/div/div/div/div[text()="Signma"]', loop=1):
                __handle_signma_popup(page=page, count=1)

        if __click_ele(page=hyperbolic_page, xpath='x://button[contains(normalize-space(.), "Transactions")]', loop=1):
            time.sleep(10)
            for i in range(8):
                _buttons = hyperbolic_page.eles(
                    locator='x://button[.//div[contains(@class,"absolute") and contains(@class,"right-0") and contains(@class,"top-0") and contains(@class,"bg-red-500")]]')
                for btn in _buttons:
                    try:
                        btn.click()
                        # 如果点击后页面有变化，适当等待
                        time.sleep(0.5)
                        if __click_ele(page=hyperbolic_page,
                                       xpath="x://div[@role='menuitem' and contains(normalize-space(.), 'Finalize withdrawal')]"):
                            time.sleep(5)
                            __handle_signma_popup(page=page, count=1, timeout=30)
                            time.sleep(5)
                    except Exception as e:
                        print(f"点击按钮时出错：{e}")
                if __click_ele(page=hyperbolic_page,
                               xpath='x://button[contains(normalize-space(.), "Next")  and not(@disabled)]', loop=1):
                    logger.info('下一页数据')
                else:
                    break

    except Exception as e:
        logger.info(f"未知异常 {evm_id} ：{e}")
    return True


def __do_task_molten(page, evm_id, index):
    __end = False
    __bool = True
    try:
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        logger.info('已登录钱包')
        __add_net_work(page=page, coin_name='arb')
        main_page = None
        # if molten_list and evm_id in molten_list:
        #     __bool = True
        #     logger.info('已成功')
        # else:
        #     main_page = page.new_tab(url="https://app.unidex.exchange/?chain=arbitrum&from=0x0000000000000000000000000000000000000000&to=0x66e535e8d2ebf13f49f3d49e5c50395a97c137b1")
        #
        #     if __get_ele(page=main_page, xpath='x://button[contains(text(), "Connect Wallet") and not(@disabled)]', loop=3):
        #         if __click_ele(page=main_page, xpath='x://button[contains(text(), "Connect Wallet") and not(@disabled)]'):
        #             if __click_ele(main_page, xpath='x://button[@data-testid="rk-wallet-option-injected" or @data-testid="rk-wallet-option-metaMask"]'):
        #                 __handle_signma_popup(page=page, count=1)
        #
        #     if __get_ele(page=main_page, xpath='x://div[contains(text(), "Select a route")]'):
        #         # rari_eth = __get_arb_balance(evm_addr=evm_addr)
        #         rari_eth = '0'
        #         _no_end = True
        #         for x in range(5):
        #             _val_end = __get_ele_value(page=main_page, xpath='x://p[contains(@class,"chakra-text") and contains(normalize-space(.),"Balance:")]', loop=2)
        #             if _val_end is None:
        #                 _val_end = "0"
        #             _m = re.search(r'Balance:\s*([\d\.]+)', _val_end)
        #             if _m:
        #                 amount = _m.group(1) if _m else '0'
        #                 if float(amount) > 0.1:
        #                     _no_end = False
        #                     __bool = True
        #                     molten_list.append(evm_id)
        #                     break
        #             if _no_end :
        #                 _val = __get_ele_value(page=main_page, xpath='x://button[contains(@class,"chakra-button") and contains(normalize-space(.),"Balance:")]')
        #                 if _val is None:
        #                     _val = "0"
        #                 m = re.search(r'Balance:\s*([\d\.]+)', _val)
        #                 if m:
        #                     amount = m.group(1) if m else '0'
        #                     rari_eth = amount
        #                     if float(amount) > 0.00012:
        #                         inp = main_page.ele('x://input[contains(@class,"chakra-input") and contains(@class,"css-1o2m894")]')
        #                         inp.clear()
        #                         if float(amount) < 0.00012:
        #                             amount_val = random.uniform(0.00008, 0.00011)
        #                         elif float(amount) < 0.00015:
        #                             amount_val = random.uniform(0.000111, 0.000151)
        #                         else:
        #                             amount_val = random.uniform(0.000151, 0.000181)
        #                         if platform.system().lower() != "windows":
        #                             import pyautogui
        #                             pyautogui.moveTo(593, 370)
        #                             time.sleep(0.5)
        #                             pyautogui.click()
        #                             time.sleep(0.5)
        #                             logger.info('点击删除按钮')
        #                             pyautogui.press('backspace')
        #                             time.sleep(0.5)
        #                         inp.input(f"{amount_val:.6f}",clear=True)
        #                         time.sleep(3)
        #                         if __click_ele(page=main_page, xpath='x://div[@data-theme="dark" and contains(@class,"RouteWrapper")]',find_all=True, index=0):
        #                             if __click_ele(page=main_page, xpath='x://button[.//div[normalize-space(text())="SWAP USING"]]'):
        #                                 if __get_ele(page=main_page, xpath='x://div[contains(text(), "Swap Failed")]', loop=1):
        #                                     logger.info('购买异常')
        #                                     if __click_ele(page=main_page, xpath='x://div[@data-theme="dark" and contains(@class,"RouteWrapper")]', find_all=True, index=0):
        #                                         __click_ele(page=main_page, xpath='x://button[.//div[normalize-space(text())="SWAP USING"]]')
        #                                 else:
        #                                     __handle_signma_popup(page=page, count=1, timeout=60)
        #                                     time.sleep(5)
        #                                     # rari_eth_end = __get_arb_balance(evm_addr=evm_addr)
        #                                     rari_eth_end = '99'
        #                                     _val_end = __get_ele_value(page=main_page, xpath='x://button[contains(@class,"chakra-button") and contains(normalize-space(.),"Balance:")]')
        #                                     if _val_end is not None:
        #                                         m = re.search(r'Balance:\s*([\d\.]+)', _val_end)
        #                                         if m:
        #                                             rari_eth_end = m.group(1) if m else '99'
        #
        #                                     if float(rari_eth) > float(rari_eth_end) :
        #                                         _no_end = False
        #                                         __bool = True
        #                                         molten_list.append(evm_id)
        #                                         break
        #                                 main_page.get(url="https://app.unidex.exchange/?chain=arbitrum&from=0x0000000000000000000000000000000000000000&to=0x66e535e8d2ebf13f49f3d49e5c50395a97c137b1")
        #                                 time.sleep(3)
        if __bool:
            if main_page is None:
                main_page = page.new_tab("https://molten.bridge.caldera.xyz/")
            else:
                main_page.get("https://molten.bridge.caldera.xyz/")
            if __get_ele_value(page=main_page, xpath='x://span[normalize-space(text())="Arbitrum One"]', loop=5):
                if __get_ele(page=main_page, xpath='x://button[contains(text(), "Connect Wallet") and not(@disabled)]',
                             loop=1):
                    if __click_ele(page=main_page,
                                   xpath='x://button[contains(text(), "Connect Wallet") and not(@disabled)]'):
                        if __click_ele(main_page,
                                       xpath='x://button[@data-testid="rk-wallet-option-xyz.signma" or @data-testid="rk-wallet-option-metaMask"]'):
                            __handle_signma_popup(page=page, count=1)
                time.sleep(5)
                _mon_from = __get_ele_value(page=main_page,
                                            xpath='x://span[normalize-space(text())="From"]/parent::div/parent::div/parent::div/div[2]/span[2]')
                if float(_mon_from) <= 0:
                    time.sleep(3)
                    _mon_from = __get_ele_value(page=main_page,
                                                xpath='x://span[normalize-space(text())="From"]/parent::div/parent::div/parent::div/div[2]/span[2]')
                _mon_to = __get_ele_value(page=main_page,
                                          xpath='x://span[normalize-space(text())="To"]/parent::div/parent::div/parent::div/div[2]/span[2]')

                if float(_mon_from) < 0.3 and float(_mon_to) > 0.3:
                    __click_ele(page=main_page, xpath='x://button[contains(text(), "Swap")]')
                    time.sleep(3)
                    _mon_from = __get_ele_value(page=main_page,
                                                xpath='x://span[normalize-space(text())="From"]/parent::div/parent::div/parent::div/div[2]/span[2]')
                    _mon_to = __get_ele_value(page=main_page,
                                              xpath='x://span[normalize-space(text())="To"]/parent::div/parent::div/parent::div/div[2]/span[2]')
                if float(_mon_from) > 0.3:
                    _mon_from_tmp = _mon_from
                    # if float(_mon_from) > 1:
                    #     # percentages = [0.30, 0.35, 0.40]
                    #     # pct = random.choice(percentages)
                    #     # _dt = float(_mon_from_tmp) * pct
                    _dt = random.uniform(1.001, 1.502)
                    if _dt > float(_mon_from):
                        _mon_from_tmp = f"{(float(_mon_from) - 0.1):.3f}"
                        # _mon_from_tmp = f"{Decimal(str(_mon_from)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)}"
                    else:
                        _mon_from_tmp = f"{_dt:.3f}"
                    __input_ele_value(page=main_page, xpath='x://input[@placeholder="Amount"]', value=_mon_from_tmp)
                    if __click_ele(page=main_page,
                                   xpath='x://button[contains(text(), "Transfer Tokens") and not(@disabled)]'):
                        __handle_signma_popup(page=page, count=2, timeout=60)
                        time.sleep(2)
                        _mon_new_from = __get_ele_value(page=main_page,
                                                        xpath='x://span[normalize-space(text())="From"]/parent::div/parent::div/parent::div/div[2]/span[2]')
                        if float(_mon_from) > float(_mon_new_from):
                            __end = True
                            signma_log(message=f"molten", task_name=f'task_{get_date_as_string()}', index=evm_id)
                            time.sleep(5)
                elif float(_mon_to) > 0:
                    __end = True
    except Exception as e:
        logger.info(f"窗口{index}:处理任务: 异常: {e}")

    return __end


# ========== 主流程 ==========

if __name__ == '__main__':
    _this_day = ''
    _end_day_task = []
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--ip", type=str, help="ip参数", default="127.0.0.1")
    parser.add_argument("--display", type=str, help="X11 DISPLAY", default=":24")
    parser.add_argument("--base-port", type=int, help="本地调试端口", default=29541)
    args = parser.parse_args()
    ARGS_IP = args.ip or ""
    _window = args.display.lstrip(':')
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
            if (parts[1] == '0' and parts[0] not in _end_day_task) or (date_obj <= today and parts[0] not in end_tasks):
                # if parts[1] == '0' or (parts[0] not in end_tasks):
                logger.info(f'添加执行今日任务:{line}')
                filtered.append(line)
        random.shuffle(filtered)
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

                if len(arg) < 2:
                    logger.warning(f"任务 arg 参数不足，跳过：{parts[3]!r}")
                    continue

                _type = arg[0]
                _id = arg[1]

                if _type == 'gift':
                    evm_id = _id
                    evm_addr = arg[2]
                    amount = arg[3]
                    _bool = True
                    # 判断需要转账
                    if amount is not None and float(amount) > 0:
                        end_tasks = read_data_list_file("/home/ubuntu/task/tasks/end_gift_wallet.txt")
                        if evm_id not in end_tasks:
                            _bool = False
                            if __do_send_wallet('88102', evm_addr, amount):
                                append_date_to_file(file_path="/home/ubuntu/task/tasks/end_gift_wallet.txt", data_str=evm_id)
                                _bool = True

                    if _bool:
                        _page = __get_page(_type, _id, None)
                        if _page is None:
                            logger.error("浏览器启动失败，跳过该任务")
                            continue
                        _end = __do_task_gift(page=_page, index=_window, evm_id=_id, evm_addr=arg[2], amount=arg[3])
                else:
                    _page = __get_page(_type, _id, None)
                    if _page is None:
                        logger.error("浏览器启动失败，跳过该任务")
                        continue
                    elif _type == 'end_eth':
                        _end = __do_end_eth(page=_page, evm_id=_id, evm_addr=arg[2], _type=arg[3], _amount=arg[4])
                    elif _type == 'quackai':
                        _end = __do_quackai(page=_page, evm_id=_id)
                    # elif _type == 'linea':
                    #     _end = __do_task_linea(page=_page, index=_window, evm_id=_id)
                    #     _end = True
                    # elif _type == 'portal':
                    #     _end = __do_task_portal(page=_page, index=_window, evm_id=_id)
                    #     _end = True
                    # elif _type == 'towns':
                    #     _end = __do_task_towns(page=_page, index=_window, evm_id=_id, evm_addr=arg[2])
                    elif _type == 'logx':
                        # _end = __do_task_logx(page=_page, index=_window, evm_id=_id)
                        _end = True
                    elif _type == 'nft':
                        _end = __do_task_nft(page=_page, index=_window, evm_id=_id)
                        _end = True
                    elif _type == 'molten':
                        _end = __do_task_molten(page=_page, evm_id=_id, index=_window)
                        _end = True
                    elif _type == 'rari_arb':
                        _end = __do_swap_rari_arb_eth(page=_page, evm_id=_id)
                        _end = True
                    elif _type == 'rari_arb_end':
                        _end = __do_swap_rari_arb_eth_end(page=_page, evm_id=_id)
                        _end = True
                    elif _type == 'nexus':
                        _end = __do_task_nexus(page=_page, index=_window, evm_id=_id)
                    elif _type == 'prismax':
                        if len(arg) < 3:
                            logger.warning("prismax 需要助记词/私钥参数，已跳过")
                        else:
                            _end = __do_task_prismax(page=_page, index=_window, evm_id=_id, evm_addr=arg[2])
                    else:
                        logger.warning(f"未知任务类型：{_type}")
            except Exception as e:
                logger.info(f"任务异常: {e}")
            finally:
                if _page is not None:
                    try:
                        _page.quit()
                    except Exception:
                        logger.exception("退出错误")
                logger.info(f'数据{_end}:{_task_type}:{_task_id}')
                if _end and _task_id and platform.system().lower() != "windows":
                    if _task_type != '0':
                        append_date_to_file(file_path="/home/ubuntu/task/tasks/end_tasks.txt", data_str=_task_id)
                    else:
                        _end_day_task.append(_task_id)
            if len(filtered) > 24:
                time.sleep(800)
            elif len(filtered) > 12:
                time.sleep(1200)
            else:
                time.sleep(1800)

        time.sleep(1800)