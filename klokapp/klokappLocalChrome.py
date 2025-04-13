import time
import random
import asyncio
import argparse
import pyperclip
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
from datetime import datetime


# 打开浏览器
def __get_page(index, user, chromePort):
    page = ChromiumPage(
        addr_or_opts=ChromiumOptions()
        .set_browser_path(path="/opt/google/chrome/google-chrome")
        .add_extension(f"/home/{user}/extensions/chrome-cloud")
        .set_user_data_path(f"/home/{user}/task/chrome/{index}")
        .set_local_port(chromePort)
        .headless(on_off=False))
    page.wait.doc_loaded(timeout=30)
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
    wallet_url = "chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
    wallet_tab = page.new_tab(url=wallet_url)
    xpath = "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
    __input_ele_value(wallet_tab, xpath, evm_id)
    __click_ele(page=wallet_tab, xpath="tag:button@@id=existingWallet")
    if len(page.get_tabs(title="Signma")) > 0 and page.tabs_count >= 2:
        time.sleep(3)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for pop_tab in all_tabs:
            if pop_tab.url == wallet_url:
                __input_ele_value(pop_tab, xpath, evm_id)
                __click_ele(page=wallet_tab, xpath="tag:button@@id=existingWallet")
                pop_tab.close()
    time.sleep(1)


# 获取元素
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False):
    loop_count = 1
    while True:
        logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            logger.info(f'点击按钮{xpath}:{loop_count}')
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
        logger.info(f'获取元素{xpath}')
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
                      index: int = -1) -> int:
    loop_count = 0
    while True:
        try:
            if not find_all:
                page.ele(locator=xpath).input(value, clear=True)
            else:
                page.eles(locator=xpath)[index].input(value, clear=True)
            return 1
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return 0
        loop_count += 1


# 窗口管理   __handle_signma_popup(page=page, count=2, timeout=30)
def __handle_signma_popup(page, count: int = 1, timeout: int = 15, must: bool = False):
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

            elif 'popout.html?windowId=backpack' in tab.url:
                __click_ele(page=tab, xpath='x://div/span[text()="确认"]')
                time.sleep(2)
            elif 'ohgmkpjifodfiomblclfpdhehohinlnn' in tab.url:
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
    email_url = 'https://mail.dmail.ai/inbox'
    email_page = page.new_tab(url=email_url)
    # 通过小狐狸钱包打开狗头钱包
    if __click_ele(page=email_page, xpath='x://span[text()="MetaMask"]', loop=20):
        __handle_signma_popup(page=page, count=1, timeout=15)
    code = None
    loop_count = 0
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
def read_questions_list_file(file_path):
    with open(file_path, "r") as file:
        questions = file.readlines()
    # 过滤掉空白行并去除每行末尾的换行符
    return [question.strip() for question in questions if question.strip()]


# 启动任务
def __do_task(page, evm_id, questions):
    try:
        with open('./inviteUrl.txt', 'r', encoding='utf-8') as file:
            content = file.read().strip()  # 读取并去除空白字符
    except FileNotFoundError:
        content = ""  # 如果文件不存在，则认为没有内容

    logger.info("登录钱包")
    __login_wallet(page=page, evm_id=evm_id)

    url = 'https://klokapp.ai/'
    if content:
        url = content

    hyperbolic_page = page.new_tab(url=url)
    # 关联钱包
    if __click_ele(page=hyperbolic_page, xpath='x://button[text()="Connect Wallet"]', loop=5):
        __click_ele(page=hyperbolic_page, xpath='x://button//span[contains(text(), "Signma")]', loop=5)
        __handle_signma_popup(page=page, count=1, timeout=15)
        __click_ele(page=hyperbolic_page, xpath='x://button[text()="Sign in"]', loop=5)
        __handle_signma_popup(page=page, count=1, timeout=15)
    __click_ele(page=hyperbolic_page, xpath='x://button[@aria-label="Close modal"]', loop=5)

    if content:
        logger.info('已有邀请码，不再拷贝')
    else:
        # 获取邀请码
        clipboard_text = __get_click_clipboard(page=page, xpath='x://button[text()="Copy Referral Link"]')
        if clipboard_text is not None and clipboard_text != '':
            # 文件为空，写入字符串
            with open('./inviteUrl.txt', 'a', encoding='utf-8') as file:
                file.write(clipboard_text)

    # 提问
    for i in range(15):
        __dialogue(page=hyperbolic_page, value=random.choice(questions))

    # 获取积分
    integral = __get_ele_value(page=hyperbolic_page,
                               xpath='x://div[contains(text(), "Total Mira Points")]/following-sibling::div')
    if integral is None:
        logger.info(f"获取积分:{integral}")


def __dialogue(page, value):
    loop_count = 0
    while True:
        try:
            ele = page.ele(locator='x://div[@class="style_loadingDots__NNnij"]')
            if ele:
                time.sleep(2)
            else:
                # 已满
                _input = page.ele('x://textarea[@name="message" and @disabled]')
                if _input:
                    return
                __input_ele_value(page=page, xpath='x://textarea[@name="message"]', value=value)
                __click_ele(page=page, xpath='x://button//img[@alt="Send message"]', loop=1)
                return
        except Exception as e:
            error = e
            pass
        if loop_count >= 15:
            return 0
        loop_count += 1


# 启动容器
def run(evm_id, question):
    page = __get_page(index=evm_id, user='lm', chromePort=39001)
    try:
        __do_task(page=page, evm_id=evm_id, questions=question)
    except Exception as e:
        logger.info(f"发生错误: {e}")
    finally:
        page.quit()


if __name__ == '__main__':
    # 钱包id
    evm_id = 4333
    # 问题
    questions = read_questions_list_file("/opt/data/questions.txt")
    run(evm_id=evm_id, question=questions)
