import time
from loguru import logger

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

    # 有时候网络慢多尝试几次
    while True:
        try:
            __click_ele(email_page, xpath='x://div[contains(@class, "icon-refresh")]', loop=20)
            # 获取最新一条
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
            elif f'ohgmkpjifodfiomblclfpdhehohinlnn' in tab.url:
                tab.close()  # 关闭符合条件的 tab 页签
            # 如果处理了足够数量的 tab，则退出
            if _count >= count:
                return True
    # 如果处理的 tab 数量小于指定数量且 must 为 True，则抛出异常
    if _count < count and must:
        raise Exception(f'未处理指定数量的窗口')
    return False

