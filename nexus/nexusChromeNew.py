import time
from DrissionPage import ChromiumPage, ChromiumOptions
import paho.mqtt.client as mqtt
import json
import argparse
from loguru import logger
import pyperclip
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import random
import subprocess
import os


evm_ext_id = "ohgmkpjifodfiomblclfpdhehohinlnn"


def read_file(file_path):
    """从文件中读取内容并去除多余空白"""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError(f"文件未找到: {file_path}")


def decrypt_aes_ecb(secret_key, data_encrypted_base64, accountType):
    """
    解密 AES ECB 模式的 Base64 编码数据，
    去除 PKCS7 填充后返回所有 accountType 为 "hyper" 的记录。
    """
    try:
        # Base64 解码
        encrypted_bytes = base64.b64decode(data_encrypted_base64)
        # 创建 AES 解密器
        cipher = AES.new(secret_key.encode('utf-8'), AES.MODE_ECB)
        # 解密数据
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        # 去除 PKCS7 填充（AES.block_size 默认为 16）
        decrypted_bytes = unpad(decrypted_bytes, AES.block_size)
        # 将字节转换为字符串
        decrypted_text = decrypted_bytes.decode('utf-8')

        # 解析 JSON 字符串为 Python 对象（通常为列表）
        data_list = json.loads(decrypted_text)

        # 使用 next() 获取第一个匹配项
        first_match = next((item for item in data_list if item.get('accountType') == accountType), None)

        # 返回第一个匹配的结果，如果没有则返回 None
        return first_match
    except Exception as e:
        # 记录错误日志
        logger.error(f"解密失败: {e}")
        return None



# =================================================   MQTT   ======================================

def create_mqtt_client(broker, port, username, password, topic):
    """
    创建并配置MQTT客户端，使用 MQTTv5 回调方式
    protocol=mqtt.MQTTv5 来避免旧版回调弃用警告
    """
    client = mqtt.Client(
        protocol=mqtt.MQTTv5,  # 指定使用 MQTTv5
        userdata={"topic": topic}  # 传递自定义数据
    )
    client.username_pw_set(username, password)

    # 注册回调函数（使用 v5 风格签名）
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # 尝试连接到 Broker
    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        raise ConnectionError(f"Error connecting to broker: {e}")

    return client


# ========== MQTT 事件回调函数（MQTTv5） ==========
def on_connect(client, userdata, flags, reason_code, properties=None):
    """
    当客户端与 Broker 建立连接后触发
    reason_code = 0 表示连接成功，否则为失败码
    """
    if reason_code == 0:
        logger.info("Connected to broker successfully.")
        # 仅发布消息，去除订阅
        pass
    else:
        logger.info(f"Connection failed with reason code: {reason_code}")


def on_disconnect(client, userdata, reason_code, properties=None):
    """
    当客户端与 Broker 断开连接后触发
    可以在此处进行自动重连逻辑
    """
    logger.info(f"Disconnected from broker, reason_code: {reason_code}")
    # 如果 reason_code != 0，则表示非正常断开
    while True:
        try:
            logger.info("Attempting to reconnect...")
            client.reconnect()
            logger.info("Reconnected successfully.")
            break
        except Exception as e:
            logger.info(f"Reconnect failed: {e}")
            time.sleep(5)  # 等待 5 秒后重试


def on_message(client, userdata, msg):
    """
    当收到订阅主题的新消息时触发
    v5 中的 on_message 参数与 v3.x 相同： (client, userdata, message)
    """
    logger.info(f"Message received on topic {msg.topic}: {msg.payload.decode()}")


# =================================================   MQTT   ======================================



# 打开浏览器
def __get_page(index, user, chrome_port, retry: int = 0):
    page = ChromiumPage(
        addr_or_opts=ChromiumOptions()
        .set_user_data_path(f"/home/{user}/task/test/{index}")
        .set_local_port(chrome_port)
        .add_extension(r"/home/ubuntu/extensions/chrome-cloud")
        .headless(on_off=False))

    page.set.window.max()
    return page

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
        # logger.info(f'获取元素{xpath}')
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


def monitor(pages, interval=300):
    bf = '0'
    """每隔 interval 秒，依次检查所有页面的速度并必要时重连"""
    while True:
        for nexus_page in pages:
            speed = __get_ele_value(page=nexus_page, xpath='x://*[@id="speed-display"]')
            if speed is None or speed == '0':
                logger.info('检测速度是为0,开启连接')
                __click_ele(page=nexus_page, xpath='x://*[@id="connect-toggle-button"]')
            else:
                points = __get_ele_value(page=nexus_page, xpath='x://div[@id="balance-display"]')
                logger.info(f'积分{points}')
                if bf != points:
                    app_info = get_app_info_integral(serverId, appId, public_key, points, 2,
                                                     '运行中， 并到采集积分:' + str(points))
                    bf = points
                    client.publish("appInfo", json.dumps(app_info))
        time.sleep(interval)


def get_app_info_integral(serverId, appId, public_key, integral, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "publicKey": f"{public_key}",
        "integral": f"{integral}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }

def get_email(tab):
    email_url = 'https://mail.dmail.ai/inbox'
    email_page = tab.browser.new_tab(url=email_url)
    email = None
    if __click_ele(email_page, xpath='x://span[text()="MetaMask"]', loop=2):
        __handle_signma_popup(page=page, count=3)
    if __click_ele(email_page, xpath='x://div[@data-title="Setting"]'):
        email = __get_ele_value(page=email_page, xpath='x://p[contains(., "Default Address")]/span[1]')
    email_page.close()
    return email


def get_email_code(tab):
    email_url = 'https://mail.dmail.ai/inbox'
    email_page = tab.browser.new_tab(url=email_url)
    if email_page.ele('x://span[text()="MetaMask"]'):
        __click_ele(email_page, xpath='x://span[text()="MetaMask"]')
        __handle_signma_popup(page=page, count=3)
    code = ''
    loop_count = 0
    while True:
        try:
            time.sleep(15)
            __click_ele(email_page, xpath='x://span[text()="Starred"]')
            time.sleep(3)
            __click_ele(email_page, xpath='x://span[text()="Inbox"]')
            time.sleep(3)
            __click_ele(email_page, xpath='x://div[contains(@class, "icon-refresh")]')
            time.sleep(3)
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--chromePort", type=str, help="执行浏览器端口", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    args = parser.parse_args()

    # MQTT 配置
    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + args.appId + '_user.json')
    # 解密并发送解密结果
    obj = decrypt_aes_ecb(args.decryptKey, encrypted_data_base64, "nexus")

    serverId = args.serverId
    appId = args.appId
    public_key = obj['secretKey']

    os.environ['DISPLAY'] = ':29'
    pages = []
    for offset in range(1, 2):
        port = 52559
        page = __get_page(index=offset, user='ubuntu', chrome_port=port, retry=1)

        __login_wallet(page=page, evm_id=public_key)

        nexus = page.new_tab(url='https://app.nexus.xyz')
        time.sleep(8)
        checkbox = __get_ele(page=nexus, xpath="x://input[@type='checkbox']")
        if checkbox.attr('checked') is not None:
            print("Battery saver 已经勾选，无需操作")
        else:
            print("Battery saver 未勾选，开始点击勾上")
            checkbox.click(by_js=True)

        shadow_host = nexus.ele('x://div[@id="dynamic-widget"]')
        if shadow_host:
            shadow_root = shadow_host.shadow_root
            if shadow_root:
                continue_button = __get_ele(page=shadow_root, xpath="x://button[@data-testid='ConnectButton']")
                if continue_button:
                    if __click_ele(page=shadow_root, xpath="x://button[@data-testid='ConnectButton']"):
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
                                    time.sleep(2)
                                    # 点击页面中显示 "Signma" 的元素
                                    signma_ele = shadow_root.ele('x://span[text()="Signma"]')
                                    if signma_ele:
                                        signma_ele.click(by_js=True)
                                        time.sleep(2)
                                        __handle_signma_popup(page=page,count=2)
                                        time.sleep(5)
                                else:
                                    logger.info("没有找到 'Signma' 元素。")
                        else:
                            logger.info("没有找到 'Continue with a wallet' 元素。")

        # 定位到包含 shadow DOM 的元素
        net_shadow_host = nexus.ele('x://div[@data-testid="dynamic-modal-shadow"]')
        if net_shadow_host:
            # 进入 shadow DOM
            net_shadow_root = net_shadow_host.shadow_root
            if net_shadow_root:
                newt_work = net_shadow_root.ele('x://button[@data-testid="SelectNetworkButton"]')
                if newt_work:
                    newt_work.click(by_js=True)
                    time.sleep(5)
                    __handle_signma_popup(page=page, count=2)

        # 判断是否需要验证邮箱
        email_shadow_host = nexus.ele('x://div[@data-testid="dynamic-modal-shadow"]')
        if email_shadow_host:
            email_shadow_root = email_shadow_host.shadow_root
            email = email_shadow_root.ele('x://input[@id="email"]')
            if email:
                em = get_email(nexus)
                email.input(em, clear=True)
                time.sleep(2)
                email_work = email_shadow_root.ele('x://button[.//span[text()="Continue"]]')
                if email_work:
                    logger.info("连接。")
                    email_work.click(by_js=True)
                    time.sleep(2)
                    # 获取邮箱验证码
                    code = get_email_code(nexus)
                    logger.info(f"获取到验证码{code}")
                    if code is not None and code != '':
                        logger.info('验证码')
                        em_shadow_host = nexus.ele('x://div[@data-testid="dynamic-modal-shadow"]')
                        em_shadow_root = em_shadow_host.shadow_root
                        for index, digit in enumerate(code):
                            input_box = em_shadow_root.ele(f'x://input[@data-testid="{index}"]')  # 选择对应输入框
                            if input_box:
                                logger.info(f'开始输入验证码{digit}')
                                input_box.click()  # 点击输入框
                                input_box.input(digit)  # 输入单个数字
                                time.sleep(0.2)  # 可选：稍微延迟，防止输入过快
        pages.append(nexus)
    monitor(pages=pages)



