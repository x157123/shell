from loguru import logger
import time


# 点击元素
def __click_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
                find_all: bool = False,
                index: int = -1) -> int:
    loop_count = 1
    while True:
        logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                logger.info(f'点击按钮{xpath}:{loop_count}')
                page.ele(locator=xpath).click(by_js=None)
            else:
                page.eles(locator=xpath)[index].click(by_js=None)
            break
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


# 窗口管理   handle_signma_popup(page=page, count=2, timeout=30)
def handle_signma_popup(page, count: int = 1, timeout: int = 15, must: bool = False):
    """处理 Signma 弹窗，遍历所有 tab 页签"""
    start_time = time.time()
    _count = 0
    logger.info('关闭窗口')
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

            elif ('popout.html?windowId=backpack' in tab.url):
                __click_ele(page=tab, xpath='x://div/span[text()="确认"]')
                time.sleep(2)
            elif ('ohgmkpjifodfiomblclfpdhehohinlnn' in tab.url):
                tab.close()  # 关闭符合条件的 tab 页签
            # 如果处理了足够数量的 tab，则退出
            if _count >= count:
                return True

    # 如果处理的 tab 数量小于指定数量且 must 为 True，则抛出异常
    if _count < count and must:
        raise Exception(f'未处理指定数量的窗口')
    return False

# 获取邮箱 验证码code
def get_email_code(tab):
    email_url = 'https://mail.dmail.ai/inbox'
    email_page = tab.browser.new_tab(url=email_url)
    time.sleep(15)
    if email_page.ele('x://span[text()="MetaMask"]'):
        __click_ele(email_page, xpath='x://span[text()="MetaMask"]')
        for _ in range(3):
            handle_signma_popup(page=tab, count=1, timeout=15)
            time.sleep(8)
    code = ''
    loop_count = 0
    while True:
        try:
            time.sleep(20)
            # click_element(email_page, xpath='x://span[text()="Starred"]')
            # time.sleep(3)
            # click_element(email_page, xpath='x://span[text()="Inbox"]')
            # time.sleep(3)
            __click_ele(email_page, xpath='x://div[contains(@class, "icon-refresh")]')
            time.sleep(40)
            __click_ele(email_page, xpath='x://div[contains(@class,"sc-eDPEul")]//ul/li[1]')
            time.sleep(3)
            # 读取验证码
            ele = email_page.ele(locator='x://p[@class="main__code"]/span')
            if ele:
                code = ele.text
                logger.info(f"读取到验证码:{code}")
            if code is not None:
                __click_ele(email_page, xpath='x://div[@data-title="trash"]')
                time.sleep(3)
            print(code)
        except Exception as e:
            logger.error(f'error ==> {e}')
        if loop_count >= 5:
            return
        if code is None:
            loop_count += 1
            continue  # 跳到下一次循环
        else:
            break
    email_page.close()
    return code
