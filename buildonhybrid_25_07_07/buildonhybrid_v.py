import requests
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import pyperclip
import random
from loguru import logger
import argparse
import os
import platform

evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"

def __click_ele(_page, xpath: str = '', loop: int = 5, must: bool = False,
                find_all: bool = False,
                index: int = -1) -> bool:
    loop_count = 1
    while True:
        logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                _page.ele(locator=xpath).click()
            else:
                _page.eles(locator=xpath)[index].click()
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


# 获取元素
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
              find_all: bool = False,
              index: int = -1):
    loop_count = 1
    while True:
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


def signma_log(message: str, task_name: str, index: str, node_name: str, total: str = "N", keywords: str = "") -> bool:
    try:
        url = "{}/service_route?service_name=signma_log&&task={}&&chain_id={}&&index={}&&msg={}&&total={}&&keywords={}"
        server_url = 'https://signma.bll06.xyz'
        full_url = url.format(server_url, task_name, node_name, index, message, total, keywords)
        try:
            response = requests.get(full_url, verify=False)
            if response.status_code == 200:
                logger.info("积分提交成功,")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return False
    except requests.exceptions.RequestException as e:
        raise logger.error(f"网络请求失败: {str(e)}")
    except Exception as e:
        raise logger.error(f"发送日志失败: {str(e)}")


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
                    __click_ele(_page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(_page=tab, xpath='x://button[@id="grantPermission"]')
                time.sleep(2)
                _count += 1

            elif '/notification.html#connect' in tab.url:
                __click_ele(_page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                __click_ele(_page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                time.sleep(2)
                _count += 1

            elif '/notification.html#confirmation' in tab.url:
                __click_ele(_page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                time.sleep(2)
                __click_ele(_page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                time.sleep(2)
                _count += 1

            elif '/notification.html#confirm-transaction' in tab.url:
                __click_ele(_page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                time.sleep(2)
                _count += 1

            elif '/popup.html?page=%2Fsign-transaction' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(_page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(_page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)
                _count += 1

            elif '/popup.html?page=%2Fsign-data' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(_page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(_page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)
                _count += 1

            elif 'popup.html?page=%2Fpersonal-sign' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(_page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(_page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)
                _count += 1

            elif ('&tab=%2Fadd-evm-chain' in tab.url) or ('/popup.html?requestId=' in tab.url):
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    __click_ele(_page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                __click_ele(_page=tab, xpath='x://button[@id="addNewChain"]')
                time.sleep(2)
                _count += 1

            elif 'popout.html?windowId=backpack' in tab.url:
                __click_ele(_page=tab, xpath='x://div/span[text()="确认"]')
                time.sleep(2)
                _count += 1

            elif f'{evm_ext_id}' in tab.url:
                tab.close()  # 关闭符合条件的 tab 页签
            # 如果处理了足够数量的 tab，则退出
            if _count >= count:
                return True
    # 如果处理的 tab 数量小于指定数量且 must 为 True，则抛出异常
    if _count < count and must:
        raise Exception(f'未处理指定数量的窗口')
    return False

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
                    __click_ele(_page=pop_tab, xpath="tag:button@@id=existingWallet")
    else:
        wallet_tab = page.new_tab(url=wallet_url)
        __input_ele_value(page=wallet_tab, xpath=xpath, value=evm_id)
        __click_ele(_page=wallet_tab, xpath="tag:button@@id=existingWallet")
        time.sleep(1)


# 窗口管理   __handle_signma_popup(page=page, count=2, timeout=30)
def __get_popup(page, count: str = '', timeout: int = 15):
    """处理 Signma 弹窗，遍历所有 tab 页签"""
    start_time = time.time()
    _count = 0
    while time.time() - start_time < timeout:
        time.sleep(2)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for tab in all_tabs:
            if count in tab.url:
                return tab
    return None


# 获取元素内容
def __get_ele_value(page, xpath: str = '', loop: int = 5, must: bool = False,
                    find_all: bool = False,
                    index: int = -1):
    try:
        # logger.info(f'获取元素{xpath}')
        _ele = __get_ele(page=page, xpath=xpath, loop=loop, must=must, find_all=find_all, index=index)
        if _ele is not None:
            if _ele:
                return _ele.text
    except Exception as e:
        error = e
        pass
    return None


def fa_code(page, code):
    _code = None
    fa_page = page.new_tab(url='https://2fa.run')
    __input_ele_value(page=fa_page, xpath='x://input[@id="secret-input-js"]',  value=code)
    _time = __get_ele_value(page=fa_page, xpath='x://span[@id="timer_js"]')
    if int(_time) < 10:
        time.sleep(int(_time) + 2)
    if __click_ele(_page=fa_page, xpath="x://button[@id='btn-js']"):
        _code = __get_ele_value(page=fa_page, xpath='x://span[@id="code_js"]')
    fa_page.close()
    return _code


def x_com(page, name, pwd, fa):
    _bool = False
    x_com_page = None
    try:
        x_com_page = __get_popup(page=page, count="twitter.com")
        __input_ele_value(page=x_com_page, xpath='x://input[@autocomplete="username"]', value=name)
        if __click_ele(_page=x_com_page, xpath='x://button[.//span[normalize-space(text())="下一步" or normalize-space(text())="Next"]]'):
            __input_ele_value(page=x_com_page, xpath='x://input[@autocomplete="current-password"]', value=pwd)
            if __click_ele(_page=x_com_page, xpath='x://button[.//span[normalize-space(text())="登录" or normalize-space(text())="Log in"]]'):
                _code = fa_code(page=page, code=fa)
                if _code is not None:
                    __input_ele_value(page=x_com_page, xpath='x://input[@inputmode="numeric"]', value=_code)
                    __click_ele(_page=x_com_page, xpath='x://button[.//span[normalize-space(text())="下一步" or normalize-space(text())="Next"]]')
        if __click_ele(_page=x_com_page, xpath='x://button[.//span[text()="Authorize app"]]'):
            time.sleep(5)
            _bool = True
    except Exception as e:
        logger.info("关联错误")
    finally:
        if x_com_page is not None:
            try:
                x_com_page.close()
            except Exception as e:
                logger.info("关闭异常")
    return _bool


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--param", type=str, help="参数")
    parser.add_argument("--ip", type=str, help="参数")
    args = parser.parse_args()
    pages = []
    idx = 0
    for part in args.param.split("||"):
        page = None
        try:
            os.environ['DISPLAY'] = ':23'
            port = 19615 + idx
            idx += 1
            arg = part.split(",")
            evm_id = arg[0]
            logger.info(f"启动:{evm_id}")
            options = ChromiumOptions()
            if platform.system().lower() != "windows":
                options.set_browser_path('/opt/google/chrome')
                options.set_user_data_path(f"/home/ubuntu/task/beboundless/chrome_data/{evm_id}")
                options.add_extension(r"/home/ubuntu/extensions/chrome-cloud")
            else:
                options.set_paths(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
                options.set_user_data_path(r"f:\tmp\rari\0" + evm_id)
                options.add_extension(r"F:\signma")
            options.set_local_port(port)
            page = ChromiumPage(options)
            page.set.window.max()

            __login_wallet(page=page, evm_id=evm_id)
            __handle_signma_popup(page=page, count=0)

            main_page = page.new_tab(url='https://claim.buildonhybrid.com/flow')
            time.sleep(5)

            if __get_ele(page=main_page, xpath='x://div[contains(@class,"flex") and contains(@class,"items-center") and contains(@class,"justify-end")]//button'):
                el = main_page.ele('x://div[contains(@class,"flex") and contains(@class,"items-center") and contains(@class,"justify-end")]//button')
                el.click(by_js=True)
                if __click_ele(_page=main_page, xpath='x://button[@data-testid="rk-wallet-option-xyz.signma"]'):
                    __handle_signma_popup(page=page, count=2)

                __handle_signma_popup(page=page, count=0)

            if __click_ele(_page=main_page, xpath='x://button[text()="Next"]'):
                if __get_ele(page=main_page, xpath='x://p[normalize-space()="Congratulations!"]', loop=1):
                    signma_log(message="1", task_name="buildonhybrid_v", index=evm_id, node_name=args.ip)
                elif __get_ele(page=main_page, xpath='x://p[normalize-space()="Not Eligible"]', loop=1):
                    signma_log(message="0", task_name="buildonhybrid_v", index=evm_id, node_name=args.ip)
                elif __get_ele(page=main_page, xpath='x://p[normalize-space()="You’ve successfully registered for the airdrop!"]', loop=1):
                    signma_log(message="9", task_name="buildonhybrid_v", index=evm_id, node_name=args.ip)
            time.sleep(10)
        except Exception as e:
            logger.info("重新错误")
        finally:
            if page is not None:
                try:
                    page.quit()
                except Exception as e:
                    logger.info("窗口关闭错误")
