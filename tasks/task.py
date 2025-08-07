import requests
from DrissionPage import ChromiumPage, ChromiumOptions
import time
from datetime import datetime
import random
from loguru import logger
import argparse
import os

evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"

def get_points(tab):
    # 获取积分：点击按钮后从剪贴板读取
    if __click_ele(tab, "x://button[.//span[text()='Points']]"):
        time.sleep(15)  # 确保剪贴板内容更新
        # 定位到指定的 div 元素并获取其文本内容
        target_div = tab.ele("x://div[text()='Accumlated points']/following-sibling::div")
        # 获取该 div 中的文本
        text = target_div.text
        # logger.info(f"Text from the div: {text}")
        return text


def __click_ele(_page, xpath: str = '', loop: int = 5, must: bool = False,
                find_all: bool = False,
                index: int = -1) -> bool:
    loop_count = 1
    while True:
        # logger.info(f'查找元素{xpath}:{loop_count}')
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


def signma_log(message: str, task_name: str, index: str) -> bool:
    try:
        url = "{}/service_route?type={}&&id={}&&data={}"
        server_url = 'http://150.109.5.143:9900'
        full_url = url.format(server_url, task_name, index, message)
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

def get_date_as_string():
    # 获取当前日期和时间
    now = datetime.now()
    # 将日期格式化为字符串 年-月-日
    date_string = now.strftime("%Y-%m-%d")
    return date_string



def click_x_y(x, y, window):
    display = f':{window}'
    os.environ['DISPLAY'] = display
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.moveTo(x, y)  # 需要你先手动量好按钮在屏幕上的位置
    pyautogui.click()



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


def wait_for_positive_amount(page, xpath, max_attempts=1, interval=1):
    """
    循环最多 max_attempts 次，从指定 xpath 获取金额字符串，
    去掉 '$' 后转成 float，并在金额 > 0 时立即返回该值。
    如果都没拿到 >0 的值，返回 0.0。
    """
    for attempt in range(max_attempts):
        raw = __get_ele_value(page=page, xpath=xpath)
        if raw:
            clean = raw.lstrip('$')
            try:
                value = float(clean)
                if value > 0:
                    return value
            except ValueError:
                # 转换失败则忽略，继续重试
                pass
        time.sleep(interval)
    # 重试完都没拿到大于 0 的值
    return 0.0


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
            elif 'ohgmkpjifodfiomblclfpdhehohinlnn' in tab.url:
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


def __do_task_logx(page, evm_id, index):
    __bool = False
    try:
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        logger.info('已登录钱包')

        main_page = page.new_tab(url="https://app.logx.network/portfolio")

        _amount = wait_for_positive_amount(page=main_page, xpath='x://div[contains(normalize-space(.),"Buying Power")]/following-sibling::div[1]//span[starts-with(normalize-space(.),"$")]')

        if _amount <= 0:
            if __click_ele(_page=main_page, xpath='x://span[text()="Connect wallet"]', loop=1):
                if __click_ele(_page=main_page, xpath='x://div[contains(@class,"sc-dcJtft iIBsYu btn marg") and .//*[contains(@d,"M21.4379 21.7337")]]', loop=3):
                    __handle_signma_popup(page=page, count=2)
            if __click_ele(_page=main_page, xpath='x://span[text()="Establish Connection"]', loop=1):
                if __click_ele(_page=main_page, xpath='x://div[div[div[text()="Establish Connection"]] and contains(@class,"sc-dcJtft iIBsYu sc-NxrBK idZGaa") ]', loop=1):
                    __handle_signma_popup(page=page, count=1)

            __click_ele(_page=main_page, xpath='x://div[contains(@class, "sc-djTQOc bLFUQW")]', loop=1)

            _amount = wait_for_positive_amount(page=main_page, xpath='x://div[contains(normalize-space(.),"Buying Power")]/following-sibling::div[1]//span[starts-with(normalize-space(.),"$")]')

        _amount_total = wait_for_positive_amount(page=main_page, xpath='x://div[contains(normalize-space(.),"Total Volume")]/following-sibling::div//span')

        signma_log(message=f"{_amount},{_amount_total}", task_name=f'logx_point_{get_date_as_string()}', index=evm_id)

        if _amount > 0:
            main_page.get('https://app.logx.network/trade/BTC')
            # 关闭可能忘记的窗口
            __click_ele(_page=main_page, xpath='x://div[span[text()="Flash Close"]]', loop=1)

            for attempt in range(5):
                if __click_ele(_page=main_page, xpath='x://div[text()="MAX"]'):
                    click_x_y(1764, 416, index)   # 1
                    # 找到元素
                    ele = __get_ele(page=main_page, xpath='x://div[contains(@class,"sc-edLa-Dd") and normalize-space(text())="Long"]')
                    if ele is not None:
                        time.sleep(1)
                        x = random.randint(1645, 1695)
                        click_x_y(x, 540, index)
                        click_x_y(x, 580, index)
                        logger.info(f'点击倍数:{x}:{index}')
                        time.sleep(2)
                        if random.choice([True, False]):
                            __click_ele(_page=main_page, xpath='x://div[contains(@class,"sc-edLa-Dd") and normalize-space(text())="Long"]')
                        else:
                            __click_ele(_page=main_page, xpath='x://div[contains(@class,"sc-edLa-Dd") and normalize-space(text())="Short"]')
                        logger.info('提交')
                    if __get_ele(page=main_page, xpath='x://div[span[text()="Flash Close"]]', loop=2):
                        break
                    else:
                        main_page.refresh()
            time.sleep(random.randint(3, 5))

            # 关闭
            for attempt in range(8):
                if __click_ele(_page=main_page, xpath='x://div[span[text()="Flash Close"]]', loop=2):
                    __bool = True
                    time.sleep(3)
                else:
                    break
    except Exception as e:
        logger.info(f"窗口{index}: 处理任务异常: {e}")
    return __bool


def __do_task_nexus(page, evm_id, index):
    __bool = False
    try:
        logger.info('登录钱包')
        __login_wallet(page=page, evm_id=evm_id)
        __handle_signma_popup(page=page, count=0)
        nexus = page.new_tab(url='https://app.nexus.xyz/rewards')
        __get_ele(page=nexus, xpath='x://a[contains(text(), "FAQ")]', loop=10)
        if __get_ele(page=nexus, xpath='x://button[div[contains(text(), "Sign in")]]', loop=1):
            __click_ele(_page=nexus, xpath='x://button[div[contains(text(), "Sign in")]]', loop=1)
            shadow_host = nexus.ele('x://div[@id="dynamic-widget"]')
            if shadow_host:
                shadow_root = shadow_host.shadow_root
                if shadow_root:
                    continue_button = __get_ele(page=shadow_root, xpath="x://button[@data-testid='ConnectButton']")
                    if continue_button:
                        __click_ele(_page=shadow_root, xpath="x://button[@data-testid='ConnectButton']")
                        # 定位到包含 shadow DOM 的元素
                        shadow_host = nexus.ele('x://div[@data-testid="dynamic-modal-shadow"]')
                        if shadow_host:
                            # 进入 shadow DOM
                            shadow_root = shadow_host.shadow_root
                            if shadow_root:
                                # 在 shadow DOM 中查找目标元素
                                continue_button = shadow_root.ele('x://p[contains(text(), "Continue with a wallet")]')
                                if continue_button:
                                    # 点击目标元素
                                    continue_button.click(by_js=True)
                                    time.sleep(1)
                                    # 点击页面中显示 "Signma" 的元素
                                    signma_ele = shadow_root.ele('x://span[text()="Signma"]')
                                    if signma_ele:
                                        signma_ele.click(by_js=True)
                                        __handle_signma_popup(page=page, count=1, timeout=15)
                                else:
                                    logger.info("没有找到 'Signma' 元素。")
                            else:
                                logger.info("没有找到 'Continue with a wallet' 元素。")

            __handle_signma_popup(page=page, count=0)
            # 定位到包含 shadow DOM 的元素
            net_shadow_host = nexus.ele('x://div[@data-testid="dynamic-modal-shadow"]', timeout=3)
            if net_shadow_host:
                # 进入 shadow DOM
                net_shadow_root = net_shadow_host.shadow_root
                if net_shadow_root:
                    newt_work = net_shadow_root.ele('x://button[@data-testid="SelectNetworkButton"]', timeout=3)
                    if newt_work:
                        newt_work.click(by_js=True)
                        __handle_signma_popup(page=page, count=1, timeout=15)

        if __get_ele(page=nexus, xpath='x://button[contains(normalize-space(.),"Claim") and contains(normalize-space(.),"Testnet NEX")]', loop=2):
            __click_ele(_page=nexus, xpath='x://button[contains(normalize-space(.),"Claim") and contains(normalize-space(.),"Testnet NEX")]')
            time.sleep(65)
            nexus.get('https://app.nexus.xyz/rewards')

        ele = nexus.ele('x://span[contains(normalize-space(.), "NEX")]')
        if ele:
            t = ele.text.replace('\xa0', ' ').strip()  # 处理不换行空格
            import re
            m = re.search(r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*NEX\b', t, re.I)
            amount = (m.group(1).replace(',', '')) if m else '0'
            signma_log(message=amount, task_name=f'nexus_point_{get_date_as_string()}', index=evm_id)
            time.sleep(3)
            __bool = True
    except Exception as e:
        logger.info(f"窗口{index}: 处理任务异常: {e}")
    return __bool



def __get_popup(page, _url: str = '', timeout: int = 15):
    """处理 Signma 弹窗，遍历所有 tab 页签"""
    start_time = time.time()
    _count = 0
    while time.time() - start_time < timeout:
        time.sleep(1)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for tab in all_tabs:
            if _url in tab.url:
                return tab
    return None

# 登录钱包
def __login_new_wallet(page, evm_addr):
    time.sleep(5)
    phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa', timeout=1)
    if phantom_page is None:
        phantom_page = page.new_tab('chrome-extension://bfnaelmomeimhlpmgjnjophhpkkoljpa/popup.html')

    if __get_ele(page=phantom_page, xpath='x://button[@data-testid="unlock-form-submit-button"]', loop=2):
        __input_ele_value(page=phantom_page, xpath='x://input[@data-testid="unlock-form-password-input"]', value='sdfasfd#dfff312')
        __click_ele(_page=phantom_page, xpath='x://button[@data-testid="unlock-form-submit-button"]')
    else:
        phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa', timeout=1)

    if __get_ele(page=phantom_page, xpath='x://button[contains(normalize-space(.), "我已经有一个钱包") or contains(normalize-space(.), "I already have a wallet")]', loop=1):
        if __click_ele(_page=phantom_page, xpath='x://button[contains(normalize-space(.), "我已经有一个钱包") or contains(normalize-space(.), "I already have a wallet")]'):
            if __click_ele(_page=phantom_page, xpath='x://button[.//div[contains(normalize-space(.), "导入恢复短语") or contains(normalize-space(.), "Import Recovery Phrase")]]'):
                for i, word in enumerate(evm_addr.split(), 0):
                    __input_ele_value(page=phantom_page, xpath=f'x://input[@data-testid="secret-recovery-phrase-word-input-{i}"]', value=word)
                # __input_ele_value(page=phantom_page, xpath='x://textarea[@name="privateKey"]', value=evm_addr)
            if __click_ele(_page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]'):
                __click_ele(_page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]')
                __input_ele_value(page=phantom_page, xpath='x://input[@data-testid="onboarding-form-password-input"]', value='sdfasfd#dfff312')
                __input_ele_value(page=phantom_page, xpath='x://input[@data-testid="onboarding-form-confirm-password-input"]', value='sdfasfd#dfff312')
                if __get_ele(page=phantom_page, xpath='x://input[@data-testid="onboarding-form-terms-of-service-checkbox" and @aria-checked="false"]', loop=1):
                    __click_ele(_page=phantom_page, xpath='x://input[@data-testid="onboarding-form-terms-of-service-checkbox" and @aria-checked="false"]', loop=1)
                __click_ele(_page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]', loop=1)
                time.sleep(1)
                __click_ele(_page=phantom_page, xpath='x://button[@data-testid="onboarding-form-submit-button"]', loop=1)
                time.sleep(1)
                __click_ele(_page=phantom_page, xpath='x://button[contains(normalize-space(.), "继续") or contains(normalize-space(.), "Continue")]', loop=1)
                time.sleep(1)
                __click_ele(_page=phantom_page, xpath='x://button[contains(normalize-space(.), "开始") or contains(normalize-space(.), "Get Started")]', loop=1)

    if phantom_page is not None:
        try:
            phantom_page.close()
        except Exception as e:
            error = e
            pass


def __close_popup(page, _url: str = '', timeout: int = 15):
    """处理 Signma 弹窗，遍历所有 tab 页签"""
    start_time = time.time()
    _count = 0
    while time.time() - start_time < timeout:
        time.sleep(1)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for tab in all_tabs:
            if _url in tab.url:
                tab.close()

def __do_task_prismax(page, evm_id, evm_addr, index):
    __bool = False
    try:

        __login_new_wallet(page=page, evm_addr=evm_addr)
        # 页面
        main_page = page.new_tab(url='https://app.prismax.ai/')
        _login = True
        __get_ele(page=main_page, xpath='x://h3[contains(normalize-space(.), "Total hours of data contributed")]')
        _wallet_but = __get_ele(page=main_page, xpath='x://div[text()="Connect Wallet"]', loop=1)
        if _wallet_but:
            main_page.actions.move_to(_wallet_but).click()
            if __click_ele(_page=main_page, xpath='x://div[contains(@class,"ConnectWalletHeader_connectOption") and .//p[normalize-space()="Phantom Wallet"]]'):
                phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa/notification.html', timeout=3)
                if phantom_page is not None:
                    if __get_ele(page=phantom_page, xpath='x://input[@data-testid="unlock-form-password-input"]', loop=1):
                        __input_ele_value(page=phantom_page, xpath='x://input[@data-testid="unlock-form-password-input"]', value='sdfasfd#dfff312')
                        if __click_ele(_page=phantom_page, xpath='x://button[contains(normalize-space(.), "解锁")]'):
                            logger.info('解锁账号')
                    __click_ele(_page=phantom_page, xpath='x://button[@data-testid="primary-button"]', loop=1)
                phantom_page = __get_popup(page=page, _url='bfnaelmomeimhlpmgjnjophhpkkoljpa/popup.html', timeout=3)
                if phantom_page is not None:
                    __click_ele(_page=phantom_page, xpath='x://button[@data-testid="primary-button"]', loop=1)
            time.sleep(5)
            if __get_ele(page=main_page, xpath='x://div[text()="Connect Wallet"]', loop=1):
                _login = False

        if _login:
            time.sleep(2)
            num_str = __get_ele_value(page=main_page, xpath='x://span[normalize-space()="Today\'s Prisma Points Earnings"]/following-sibling::div/span[contains(@class,"Dashboard_pointsValue__")]')
            if num_str is not None and float(num_str) > 0:
                # 当日结束
                sum_num_str = __get_ele_value(page=main_page, xpath='x://span[normalize-space()="Overall Prisma Points Earnings"]/following-sibling::div/span[contains(@class,"Dashboard_pointsValue__")]')
                # append_date_to_file(lock=lock, file_path=end_filepath, data_str=evm_id)
                # append_date_to_file(lock=lock, file_path='integral_all.txt', data_str=str(evm_id)+ "," + sum_num_str.replace(",", "") + "," + datetime.now().strftime('%Y%m%d'))
                signma_log(message=sum_num_str.replace(",", ""), task_name=f'prismax_point_{get_date_as_string()}', index=evm_id)
                __bool = True

            # 尝试问答获取积分
            main_page.get('https://app.prismax.ai/whitepaper')
            if __click_ele(_page=main_page, xpath='x://button[contains(normalize-space(.), "Review answers")]', loop=1):
                logger.info('答题积分完成')
            elif __get_ele(page=main_page, xpath='x://button[contains(normalize-space(.), "Start Quiz")]', loop=2):
                for i in range(2):
                    if __get_ele(page=main_page, xpath='x://button[contains(normalize-space(.), "Start Quiz")]', loop=2):
                        __click_ele(_page=main_page, xpath='x://button[contains(normalize-space(.), "Start Quiz")]', loop=2)
                        __click_ele(_page=main_page, xpath='x://button[contains(normalize-space(.), "Take the quiz")]')
                        for offset in  range(5):
                            time.sleep(random.uniform(1, 5))       # 页面提交错误，延迟看是否能解决
                            _select_t = __get_ele(page=main_page, xpath='x://div[span[starts-with(normalize-space(.),"Higher token prices attract") or starts-with(normalize-space(.),"Teleoperator-generated data") or starts-with(normalize-space(.),"To automatically validate data quality") or starts-with(normalize-space(.),"Data collection infrastructure is fragmented") or starts-with(normalize-space(.),"Introduction of visual data collection")]]')
                            main_page.actions.move_to(_select_t).click()
                            time.sleep(3)
                            _select = __get_ele(page=main_page, xpath='x://div[span[starts-with(normalize-space(.),"To incentivize speed and discover") or starts-with(normalize-space(.),"Network-owned data is community-controlled") or starts-with(normalize-space(.),"Current AI models lack sufficient") or starts-with(normalize-space(.),"Achievement of high robot autonomy") or starts-with(normalize-space(.),"More robots generate valuable datasets")]]')
                            logger.info(_select.html)
                            main_page.actions.move_to(_select).click()
                            time.sleep(4)
                            _next = __get_ele(page=main_page, xpath='x://button[(@class="QuizModal_navButton__Zy2TN" and contains(normalize-space(.), "Next →")) or (@class="QuizModal_goldButton__SjXdA" and contains(normalize-space(.), "Finish Quiz →"))]')
                            if _next:
                                time.sleep(1)
                                logger.info(_next.html)
                                main_page.actions.move_to(_next).click()
                        time.sleep(5)
                        main_page.get('https://app.prismax.ai/whitepaper')
                        time.sleep(2)
                    else:
                        break
    except Exception as e:
        logger.info(f"窗口{index}处理任务异常: {e}")
    finally:
        if page is not None:
            try:
                page.quit()
            except Exception as e:
                logger.exception("退出错误")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--param", type=str, help="参数")
    parser.add_argument("--ip", type=str, help="参数")
    args = parser.parse_args()
    _window = '24'
    for part in args.param.split("||"):
        page = None
        try:
            os.environ['DISPLAY'] = f':{_window}'
            port = 29541
            arg = part.split(",")
            _type = arg[0]
            _id = arg[1]
            logger.info(f"启动:{type}")
            options = ChromiumOptions()
            options.set_browser_path('/opt/google/chrome')
            if _type == 'prismax':
                options.add_extension(f"/home/ubuntu/extensions/phantom")
            else:
                options.add_extension(f"/home/ubuntu/extensions/chrome-cloud")

            options.set_user_data_path(f"/home/ubuntu/task/tasks/{_type}/chrome_data/{_id}")
            options.set_user_agent(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
            options.set_local_port(port)
            page = ChromiumPage(options)
            page.set.window.max()

            if _type == 'logx':
                __do_task_logx(page=page,index=_window, evm_id=_id)
            elif _type == 'nexus':
                __do_task_nexus(page=page,index=_window, evm_id=_id)
            elif _type == 'prismax':
                __do_task_prismax(page=page, index=_window, evm_id=_id, evm_addr=arg[2])

        except Exception as e:
            logger.info(f"任务异常: {e}")
        finally:
            if page is not None:
                try:
                    page.quit()
                except Exception as e:
                    logger.exception("退出错误")
