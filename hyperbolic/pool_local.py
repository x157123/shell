import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from DrissionPage import ChromiumPage, ChromiumOptions
import random
import csv
import pyperclip
from loguru import logger
import requests
import pyautogui
import os

# 最大重试次数
MAX_RETRY = 5
max_workers = 1


def __get_page(index, wallet):
    # page = ChromiumPage(
    #     addr_or_opts=ChromiumOptions()
    #     .set_user_data_path(path=f'D://tmp/hyperbolic/{index}')
    #     .set_local_port(7896 + index)
    #     .headless(on_off=False))
    page = ChromiumPage(
        addr_or_opts=ChromiumOptions()
        .set_paths(r"/opt/google/chrome/google-chrome")
        .set_proxy("192.168.3.107:7890")
        # .add_extension("/home/lm/extensions/signma")
        .set_user(user=f"Profile {wallet}")
        .set_user_data_path(path=f'/home/lm/task/chrome_data/{wallet}')
        .set_local_port(7896 + index)
        .headless(on_off=False))
    page.wait.doc_loaded(timeout=30)
    page.set.window.max()
    return page


def __click_ele(page, xpath: str = '', loop: int = 5, must: bool = False, by_jd: bool = True, find_all: bool = False,
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


def __input_ele(page, xpath: str = '', value: str = '', loop: int = 5, must: bool = False, find_all: bool = False,
                index: int = -1) -> int:
    loop_count = 0
    while True:
        try:
            if not find_all:
                ele = page.ele(locator=xpath).input(value, clear=True)
            else:
                page.eles(locator=xpath)[index].input(value, clear=True)
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
        time.sleep(2)
    return 1


def handle_signma_popup(page, count: int = 1, timeout: int = 15, must: bool = False):
    """处理 Signma 弹窗，遍历所有 tab 页签"""
    start_time = time.time()
    _count = 0
    while time.time() - start_time < timeout:
        time.sleep(2)
        # 获取所有打开的 tab 页签
        all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
        # 遍历所有的 tab 页签
        for tab in all_tabs:
            logger.info(tab.url)
            if 'auth/action?mode=verifyEmail&oobCode' in tab.url:
                tab.close()  # 关闭符合条件的 tab 页签
                _count += 1
            # 如果处理了足够数量的 tab，则退出
            if _count >= count:
                return True

    # 如果处理的 tab 数量小于指定数量且 must 为 True，则抛出异常
    if _count < count and must:
        raise Exception(f'未处理指定数量的窗口')
    return False


def open_email(page, email, passwd, register: int = 0, reset: int = 0, passwd_new: str = ''):
    email_page = page.new_tab(url='https://firstmail.ltd/ru-RU/webmail/login')
    time.sleep(2)
    # 获取邮箱输入框并输入邮箱
    email_input = email_page.ele('x://input[@id="email"]')
    if email_input:
        # 获取地址输入框并输入邮件
        __input_ele(email_page, 'x://input[@id="email"]', email)
        # 获取密码输入框并输入密码
        __input_ele(email_page, 'x://input[@id="password"]', passwd)

        # 记录开始时间
        start_time = time.time()
        # 循环判断按钮状态，最多等待10秒
        bol = True
        while True:
            captcha_button = email_page.ele('x://button[@id="captcha"]')
            if captcha_button:
                # 检查按钮是否禁用
                if 'disabled' not in captcha_button.attr('outerHTML'):
                    # 如果按钮没有禁用，点击按钮
                    if bol:
                        captcha_button.click()
                        logger.success("点击按钮校验按钮...")
                        bol = False
                    else:
                        logger.success("等待...")
                    time.sleep(2)  # 等待2秒，模拟延迟

                # 获取最新的按钮状态
                captcha_button = email_page.ele('x://button[@id="captcha"]')

                # 检查按钮是否变成 "input-captcha-error" 或 "input-captcha-success"
                if 'input-captcha-error' in captcha_button.attr(
                        'class') or 'input-captcha-success' in captcha_button.attr('class'):
                    # 如果按钮变为结束状态，继续操作
                    logger.success("按钮变为结束状态，继续...")
                    time.sleep(2)  # 等待2秒，模拟延迟
                    break

                # 检查是否超时（最多等待50秒）
                if time.time() - start_time > 50:
                    logger.success("超过最大等待时间，跳出循环")
                    raise Exception(f'超过最大等待时间，跳出循环')
                    # email_page.close()
                    # break

        logger.success(f'登录账号：{email}')
        # 找到登录按钮并点击
        __click_ele(email_page, 'x://button[@class="btn btn-primary w-100"]')
    if register == 1:
        time.sleep(5)  # 等待5s
        logger.success(f'校验邮箱：{email}')
        # 点击第一封邮件
        __click_ele(email_page,
                    'x://ul[@class="list-unstyled m-0"]/li[1]//div[@class="email-list-item-content ms-2 ms-sm-0 me-2"]')

        time.sleep(5)  # 等待5s
        # 切换到 iframe 上下文
        iframe = email_page.ele('x://iframe')  # 定位到 iframe 元素
        iframe_page = email_page.get_frame(iframe)  # 切换到 iframe 中
        # 找到 iframe 中的 a 标签并点击
        __click_ele(iframe_page, 'x://a[contains(@href, "action?mode=verifyEmail")]')  # 少数情况会失败
        time.sleep(40)
        bool = handle_signma_popup(page, 1, 15, False)
        if bool == False and iframe_page.ele('x://a[contains(@href, "action?mode=verifyEmail")]'):
            pyautogui.moveTo(462, 495)  # 需要你先手动量好按钮在屏幕上的位置
            pyautogui.click()
            logger.info('点击坐标')
            time.sleep(40)
            handle_signma_popup(page, 1, 15, False)

    if reset == 1:
        logger.success(f'重置密码：{email}')

    email_page.close()
    # return email_page


# 登录并操作函数，支持重试次数
def __do_task(account, retry: int = 0):
    if not os.path.isfile('./transfer.txt'):
        with open(file='./transfer.txt', mode='a+', encoding='utf-8') as file:
            file.close()
        time.sleep(0.1)
        del file
    __transfer = open(file='./transfer.txt', mode='r+', encoding='utf-8')
    __transfer_str = __transfer.read()

    if account['wallet_addr'] in __transfer_str:
        logger.info(f"跳过：{account['wallet_addr']}")
        return True

    if not os.path.isfile('./token.txt'):
        with open(file='./token.txt', mode='a+', encoding='utf-8') as file:
            file.close()
        time.sleep(0.1)
        del file
    __token = open(file='./token.txt', mode='r+', encoding='utf-8')
    __token_str = __token.read()

    if not os.path.isfile('./register.txt'):
        with open(file='./register.txt', mode='a+', encoding='utf-8') as file:
            file.close()
        time.sleep(0.1)
        del file
    __register = open(file='./register.txt', mode='r+', encoding='utf-8')
    __register_str = __register.read()
    bool = True
    email = account['email']
    index = account['index']
    wallet = account['wallet']
    wallet_addr = account['wallet_addr']  # 钱包地址
    passwd = account['passwd']
    passwd_new = account['passwd_new']
    register = account['register']  # 账号注册
    reset = account['reset']  # 重置密码
    transfer = account['transfer']  # 转账
    logger.info(f"任务 {index} 开始 - {email} 第 {retry + 1} 次尝试")

    page = __get_page(index, wallet)
    try:
        hyperbolic_page = page.new_tab("https://app.hyperbolic.xyz")
        time.sleep(random.randint(2, 5))
        # if register is not None and register == 1 and wallet_addr not in __register_str:
        #     if (not hyperbolic_page.ele('x://button[contains(text(), "Deposit")]')):
        #         # 创建账号
        #         __click_ele(page=hyperbolic_page, xpath='x://button[contains(text(), "Create an account ")]')
        #
        #         # 获取邮箱输入框并输入邮箱
        #         email_input = hyperbolic_page.ele('x://input[@name="email"]')
        #         email_input.input(email, clear=True)
        #
        #         # 获取密码输入框并输入密码
        #         password_input = hyperbolic_page.ele('x://input[@name="password"]')
        #         password_input.input(passwd_new, clear=True)
        #         time.sleep(5)
        #         # 点击checkbox按钮
        #         cf_verify(hyperbolic_page, 834, 563)
        #         time.sleep(5)
        #         __click_ele(page=hyperbolic_page, xpath='x://button[contains(text(), "Sign Up")]', loop=15)
        #         time.sleep(5)
        # else:
        if hyperbolic_page.ele('x://input[@name="email"]'):
            # 获取邮箱输入框并输入邮箱
            __input_ele(hyperbolic_page, 'x://input[@name="email"]', email)
            # 获取密码输入框并输入密码
            __input_ele(hyperbolic_page, 'x://input[@name="password"]', passwd_new)
            time.sleep(5)
            # 点击checkbox按钮
            cf_verify(hyperbolic_page, 836 + random.randint(1, 6), 512 + random.randint(1, 6))
            time.sleep(5)
            if (hyperbolic_page.ele('x://button[contains(text(), "Log In") and not(@aria-haspopup="dialog") and not(@disabled)]')):
                time.sleep(15)
                cf_verify(hyperbolic_page, 836 + random.randint(1, 6), 512 + random.randint(1, 6))

            __click_ele(page=hyperbolic_page,
                        xpath='x://button[contains(text(), "Log In") and not(@aria-haspopup="dialog") and not(@disabled)]',
                        loop=10)

        if (hyperbolic_page.ele('x://button[contains(text(), "Resend verification link")]')):
            __click_ele(page=hyperbolic_page,
                        xpath='x://button[contains(text(), "Resend verification link")]', must=True)
            time.sleep(5)
            if wallet_addr not in __register_str:
                __register.write(wallet_addr + '\r')
                __register.flush()

            # 进入邮箱 进行验证
            open_email(page, email=email, passwd=passwd, register=register, reset=reset, passwd_new=passwd_new)

        time.sleep(5)
        # 关闭弹窗
        __click_ele(page=hyperbolic_page, xpath='x://button[contains(text(), "Get Started")]', loop=1)
        # # 绑定钱包
        # hyperbolic_page.get("https://app.hyperbolic.xyz/billing")
        # __click_ele(page=hyperbolic_page, xpath='x://button[contains(text(), "Get Started")]', loop=1)
        # __click_ele(page=hyperbolic_page, xpath='x://button[contains(text(), "Wallet Address")]', loop=1, must=True)
        # __input_ele(page=hyperbolic_page, xpath='x://input[@placeholder="Paste your wallet address here"]',
        #             value=wallet_addr, must=True)
        # __click_ele(page=hyperbolic_page, xpath='x://button[text()="Add"]', loop=2, must=True)

        # 获取token
        hyperbolic_page.get("https://app.hyperbolic.xyz/settings")
        pyperclip.copy('')
        time.sleep(5)
        __click_ele(page=hyperbolic_page, xpath='x://button[@data-tooltip-id="api-key-tooltip"]')
        pyautogui.moveTo(683, 1066)  # 需要你先手动量好按钮在屏幕上的位置
        pyautogui.click()
        clipboard_text = pyperclip.paste().strip()
        logger.info(f'获取剪辑版数据{clipboard_text}')
        token_str = wallet + ":" + clipboard_text
        if clipboard_text is not None and clipboard_text != "" and token_str not in __token_str:
            __token.write(token_str + '\r')
            __token.flush()

        # 开始转账
        if transfer == 1:
            if wallet_addr in __transfer_str:
                logger.success(f'已转账跳过 ==> {wallet_addr}')
            else:
                hyperbolic_page.get("https://app.hyperbolic.xyz/billing")
                time.sleep(5)
                logger.info('开始转账')
                random_number = random.randint(11, 20)
                logger.info(f"转账金额0.000000000000{str(random_number)}")
                # send_get_request(index, "0.000000000000" + str(random_number))
                # 验证是否绑定成功
                ok = hyperbolic_page.ele('x://span[contains(text(), "0xd3cB24E0Ba20865C530831C85Bd6EbC25f6f3B60")]')
                to = "0xd3cB24E0Ba20865C530831C85Bd6EbC25f6f3B60"
                # 获取转账合约地址
                if ok:
                    span_element = hyperbolic_page.ele('x://span[contains(@class, "text-base font-semibold")]')
                    if span_element:
                        span_text = span_element.text
                        # 将文本转换为数字（整数或浮点数）
                        span_value = float(span_text)  # 使用 float 以支持整数和浮动数字
                        # 判断 span_value 是否大于 0
                        if span_value <= 0:
                            url_tmp = "http://192.168.0.16:8082/service_route?service_name=token_trans&&index={}&&to={}&&value=0.000000000000{}&&contractAddr=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913&&chainId=8453"
                            transfer_url = url_tmp.format(wallet, to, random_number)
                            logger.info(transfer_url)
                            transfer_page = page.new_tab(transfer_url)
                            time.sleep(20)
                            transfer_page.close()

                        __transfer.write(wallet_addr + '\r')
                        __transfer.flush()
                        time.sleep(5)
                        hyperbolic_page.refresh()
                        time.sleep(5)
                else:
                    raise Exception(f'充值判断失败')

    except Exception as e:
        logger.info(f"任务 {index} 失败 - {email} 错误: {e}")
        bool = False  # 失败
    finally:
        page.quit()
        return bool


def cf_verify(window_page, x, y):
    # 第二步：进入第一个 shadow-root 上下文
    shadow_host = window_page.ele('x://div[@id="cf-turnstile"]/div')  # 定位到 shadow-host
    shadow_root = shadow_host.shadow_root  # 获取 shadow-root
    # 第三步：在 shadow-root 中获取 iframe
    iframe_in_shadow = shadow_root.ele('x://iframe')  # 定位到 shadow-root 内的 iframe
    iframe_page_in_shadow = window_page.get_frame(iframe_in_shadow)  # 切换到嵌套的 iframe 上下文
    # 第四步：进入第二个 shadow-root（嵌套的 shadow-root）
    shadow_host_2 = iframe_page_in_shadow.ele('x://body')  # 定位到第二个 shadow-host
    shadow_root_2 = shadow_host_2.shadow_root  # 获取第二个 shadow-root
    logger.info('检测cf验证')
    # 第五步：定位到 checkbox 并点击
    __checkbox = shadow_root_2.ele('x://input[@type="checkbox"]')
    # __click_ele(shadow_root_2, 'x://input[@type="checkbox"]')
    if __checkbox:
        pyautogui.moveTo(x, y)  # 需要你先手动量好按钮在屏幕上的位置
        pyautogui.click()
        # iframe_page_in_shadow.actions.move_to(__checkbox).click()
    logger.info('检测cf验证结束')
    time.sleep(5)


def send_get_request(index, value, to="0xd3cB24E0Ba20865C530831C85Bd6EbC25f6f3B60"
                     , contractAddr="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", chainId=8453):
    logger.info(f"转账{value}")
    # Define the base URL
    url = "http://192.168.0.16:8082/service_route"

    # Prepare the parameters with default values for contractAddr and chainId
    params = {
        "service_name": "token_trans",
        "index": index,
        "to": to,
        "value": value,
        "contractAddr": contractAddr,
        "chainId": chainId
    }

    # Send the GET request
    response = requests.get(url, params=params)

    # Check the response status and content
    if response.status_code == 200:
        logger.info("Request was successful!")
        return response.text  # or response.json() if the response is in JSON format
    else:
        logger.info(f"Request failed with status code: {response.status_code}")
        return None


# 主任务调度
def run_tasks(accounts):
    retry_counts = {acc['email']: 0 for acc in accounts}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        # 提交所有任务，不需要等待每个任务完成
        for acc in accounts:
            future = executor.submit(__do_task, acc)
            futures.append(future)

        # 处理任务结果
        for future in as_completed(futures):
            acc = accounts[futures.index(future)]  # 找到对应的账号
            try:
                success = future.result()
                if not success:
                    retry_counts[acc['email']] += 1
                    if retry_counts[acc['email']] < MAX_RETRY:
                        logger.info(f"任务 {acc['email']} 失败，正在重试...")
                        # 重新提交失败的任务
                        executor.submit(__do_task, acc)
                    else:
                        logger.info(f"账号 {acc['email']} 达到最大重试次数，跳过")
            except Exception as e:
                logger.info(f"未知异常 {acc['email']} ：{e}")

    logger.info("所有任务完成")


if __name__ == "__main__":
    account_data = []
    with open("/home/lm/hyperbolic/mailJoin.csv", mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            account_data.append({
                "index": int(row["id"]),
                "wallet": row["wallet"],
                "wallet_addr": row["wallet_addr"],
                "email": row["email"],
                "passwd": row["passwd"],
                "passwd_new": row["passwd_new"],
                "register": int(row["register"]),
                "reset": int(row["reset"]),
                "transfer": int(row["transfer"])
            })
    # for acc in account_data:
    #     logger.info(acc)

    run_tasks(account_data)
