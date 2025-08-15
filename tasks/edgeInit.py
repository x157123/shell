import requests
from DrissionPage import ChromiumPage, ChromiumOptions
import time
from datetime import datetime
import random
from loguru import logger
import argparse
import os
from decimal import Decimal, ROUND_DOWN
import platform
import re

# ========== 全局配置 ==========
evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"
ARGS_IP = ""  # 在 main 里赋值


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


def __do_task_linea(page, evm_id, index):
    __bool = False
    try:
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

# 添加网络
def __add_net_work(page, coin_name='base'):
    obj = {
        'arb': 42161,
        'base': 8453,
        'opt': 10,
        'hemi': 43111,
        'arbitrum': 42161,
        'linea': 59144,
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



def __get_page():
    page = ChromiumPage(
        addr_or_opts=ChromiumOptions()
            .set_browser_path(path=r"/usr/bin/microsoft-edge")
            .auto_port()
            .headless(on_off=False))
    page.wait.doc_loaded(timeout=30)
    page.set.window.max()
    return page

# ========== 主流程 ==========

if __name__ == '__main__':
    _this_day = ''
    _end_day_task = []
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--index", type=str, help="index参数", default="0")
    parser.add_argument("--display", type=str, help="X11 DISPLAY", default=":24")
    parser.add_argument("--base-port", type=int, help="本地调试端口", default=29541)
    args = parser.parse_args()
    ARGS_IP = args.ip or ""
    _window = args.display.lstrip(':')

    __get_page()

    time.sleep(20)