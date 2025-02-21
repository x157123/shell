import time
from DrissionPage._base.chromium import Chromium
from DrissionPage._configs.chromium_options import ChromiumOptions
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


def configure_browser(user):
    """配置并启动浏览器"""
    co = (ChromiumOptions().set_local_port(9515)
          .set_paths(r"/opt/google/chrome/google-chrome")
          .add_extension(r"/home/" + user + "/extensions/chrome-cloud"))
    arguments = [
        "--accept-lang=en-US", "--no-first-run", "--force-color-profile=srgb",
        "--metrics-recording-only", "--password-store=basic", "--use-mock-keychain",
        "--export-tagged-pdf", "--disable-gpu", "--disable-web-security",
        "--disable-infobars", "--disable-popup-blocking", "--allow-outdated-plugins",
        "--deny-permission-prompts", "--disable-suggestions-ui", "--window-size=1920,1080",
        "--disable-mobile-emulation", "--user-data-dir=/tmp/nexus/userData/9516",
        "--disable-features=ServerSentEvents"
    ]

    for arg in arguments:
        co.set_argument(arg)

    co.set_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

    browser = Chromium(co)
    # tab = browser.new_tab(url="https://app.nexus.xyz")
    tab = browser.latest_tab
    return tab


def click_element(tab, xpath, timeout=2, interval=0.5):
    """
    尝试点击页面元素，若元素在超时时间内无法找到或点击失败则返回False。
    :param tab:        DrissionPage 或 Selenium 中的 tab 对象
    :param xpath:      要查找的元素的 XPath
    :param timeout:    最长等待时间（秒）
    :param interval:   每次重试的间隔时间（秒）
    :return:           bool
    """
    start_time = time.time()

    while True:
        # 如果超时则退出循环
        if time.time() - start_time > timeout:
            # logger.info(f"未在 {timeout} 秒内找到元素：{xpath}")
            return False
        # 在当前页面查找元素
        element = tab.ele(xpath)
        if element:
            # 找到元素后尝试点击
            try:
                element.click()
                # logger.info(f"成功点击元素：{xpath}")
                return True
            except Exception as e:
                # logger.error(f"未找到元素")
                return False
        time.sleep(interval)


def get_element(tab, xpath, timeout=2, interval=0.5):
    """
    尝试点击页面元素，若元素在超时时间内无法找到或点击失败则返回False。
    :param tab:        DrissionPage 或 Selenium 中的 tab 对象
    :param xpath:      要查找的元素的 XPath
    :param timeout:    最长等待时间（秒）
    :param interval:   每次重试的间隔时间（秒）
    :return:           bool
    """
    start_time = time.time()

    while True:
        # 如果超时则退出循环
        if time.time() - start_time > timeout:
            # logger.info(f"未在 {timeout} 秒内找到元素：{xpath}")
            return None
        # 在当前页面查找元素
        element = tab.ele(xpath)
        if element:
            # 找到元素后尝试点击
            try:
                return element
            except Exception as e:
                logger.error(f"点击元素 {xpath} 时发生异常：{e}")
        time.sleep(interval)


def get_clipboard_text(user_name: str, display: str):
    """从剪贴板获取文本"""
    time.sleep(3)  # Ensure clipboard content is updated

    # First, try to get the clipboard content using pyperclip
    clipboard_text = pyperclip.paste().strip()
    logger.info(f"Clipboard text: {clipboard_text}")
    if not clipboard_text:  # If clipboard is empty or None, fall back to xclip
        logger.info("Clipboard is empty or None. Trying xclip command.")
        # Dynamically build the command with the provided display and user name
        command = f"export DISPLAY=:{display}; sudo -u {user_name} xclip -o"
        try:
            result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
            clipboard_text = result.stdout.strip()
            # logger.info(f"Clipboard text from xclip: {clipboard_text}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error while getting clipboard content using xclip: {e}")
            clipboard_text = ""  # Set to empty string if there's an error with xclip

    # If we still have no clipboard content, log it
    if not clipboard_text:
        logger.warning("Failed to retrieve clipboard content.")

    return clipboard_text


def read_file(file_path):
    """从文件中读取内容并去除多余空白"""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError(f"文件未找到: {file_path}")


def decrypt_aes_ecb(secret_key, data_encrypted_base64, key):
    """
    解密 AES ECB 模式的 Base64 编码数据，
    去除 PKCS7 填充后直接返回 accountType 为 "hyper" 的记录中的 privateKey。
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

        # logger.info(f"获取数据中的 {key}: {decrypted_text}")

        # 解析 JSON 字符串为 Python 对象（通常为列表）
        data_list = json.loads(decrypted_text)

        # 遍历数组，查找 accountType 为 "hyper" 的第一个记录
        for item in data_list:
            if item.get('accountType') == 'nexusWallet':
                return item.get(key)

        # 没有找到匹配的记录，返回 None
        return None

    except Exception as e:
        raise ValueError(f"解密失败: {e}")


def get_info(server_id, account_type, public_key, private_key):
    return {
        "serverId": f"{server_id}",
        "accountType": f"{account_type}",
        "publicKey": f"{public_key}",
        "privateKey": f"{private_key}"
    }


def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def get_app_info_integral(serverId, appId, public_key, integral, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "publicKey": f"{public_key}",
        "integral": f"{integral}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def monitor_switch(tab, client, serverId, appId, user, display, public_key):
    num = random.randint(10, 20)
    i = 399
    while True:
        try:
            time.sleep(num)

            # 定位 class 属性中包含 'bg-[#ffffff]' 的 div 元素
            div_ele = tab.ele('x://div[contains(@class, "bg-[#ffffff]")]')

            # 判断元素是否存在，存在则执行点击操作
            if div_ele:
                div_ele.click(by_js=True)
                logger.info("离线，已执行点击操作。")
            else:
                logger.info("在线。")

            i += 1

            if i > 4:
                signup_ele = tab.ele('x://div[text()="Earnings"]')
                if signup_ele:
                    number_ele = tab.ele('x://div[contains(., "NEX points")]/preceding-sibling::div[1]')
                    if number_ele:
                        points = number_ele.text
                        logger.info('获取的数字：', points)

                        app_info = get_app_info_integral(serverId, appId, public_key, points, 2,
                                                         '运行中， 并到采集积分:' + str(points))
                        client.publish("appInfo", json.dumps(app_info))
                    else:
                        logger.info('未获取到积分')
                        client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 3, '未获取到积分: ')))

                    i = 0
                    logger.info("刷新页面。")
                    tab.reload()
        except Exception as e:
            client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 3, '检查过程中出现异常: ' + str(e))))


# 获取key
def push_key(tab, client, serverId, user, display):
    # 获取公钥：点击按钮后从剪贴板读取
    if click_element(tab, "x://p[text()='Public Key:']/following-sibling::div//button"):
        public_key = get_clipboard_text(user, display)
        # 获取私钥：点击按钮后从剪贴板读取
        if click_element(tab,
                         "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
            if click_element(tab, "x://button[contains(., 'copy current private key')]"):
                private_key = get_clipboard_text(user, display)
                logger.info(f"send key")
                # 保存私钥
                client.publish("hyperKey", json.dumps(get_info(serverId, "hyper", public_key, private_key)))
        return public_key
    return None


# 重置key
def reset_key(tab):
    # 获取私钥：点击按钮后从剪贴板读取
    logger.info(f"reset_key")
    if click_element(tab,
                     "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
        if click_element(tab, "x://button[normalize-space()='RESET KEY']"):
            if click_element(tab, "x://button[normalize-space()='RESET']"):
                time.sleep(2)
                click_element(tab, 'x://button[@role="switch" and @aria-checked="false"]', timeout=5)

    # 关闭私钥弹窗（如果存在）
    click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)


def main(client, serverId, appId, decryptKey, user, display):
    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + appId + '_user.json')
    # 解密并发送解密结果
    public_key = decrypt_aes_ecb(decryptKey, encrypted_data_base64, 'secretKey')

    if public_key is None:
        client.publish("appInfo",
                       json.dumps(get_app_info(serverId, appId, 3, '未绑定账号')))
        logger.info(f"未读取到账号")
        return

    # 启动浏览器
    logger.info(f"start")
    tab = configure_browser(user)
    logger.info(f"安装钱包")
    tab = setup_wallet(tab, public_key)
    time.sleep(3)
    tab = tab.browser.new_tab(url="https://app.nexus.xyz")

    # 定位 class 属性中包含 'bg-[#ffffff]' 的 div 元素
    div_ele = tab.ele('x://div[contains(@class, "bg-[#ffffff]")]')

    # 判断元素是否存在，存在则执行点击操作
    if div_ele:
        div_ele.click(by_js=True)
        logger.info("找到了包含 'bg-[#ffffff]' 的 div，已执行点击操作。")
    else:
        logger.info("未找到包含 'bg-[#ffffff]' 的 div。")

    # 点击 "Sign up to earn NEX" 元素
    signup_ele = tab.ele('x://div[text()="Sign up to earn NEX"]/ancestor::button')
    if signup_ele:
        signup_ele.click(by_js=True)
        # 根据实际情况调整等待时间，确保页面加载完成
        time.sleep(2)

        # 定位到包含 shadow DOM 的元素
        shadow_host = tab.ele('x://div[@data-testid="dynamic-modal-shadow"]')
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
                        myriad_pop(tab)
                        time.sleep(2)
                        myriad_pop(tab)
                        # 定位到包含 shadow DOM 的元素
                        shadow_host = tab.ele('x://div[@data-testid="dynamic-modal-shadow"]')
                        if shadow_host:
                            # 进入 shadow DOM
                            shadow_root = shadow_host.shadow_root
                            if shadow_root:
                                newtwork = shadow_root.ele('x://@button[data-testid="SelectNetworkButton"]')
                                if newtwork:
                                    newtwork.click(by_js=True)
                                    time.sleep(5)
                                    myriad_pop(tab)
                                    time.sleep(2)
                                    myriad_pop(tab)
                else:
                    logger.info("没有找到 'Signma' 元素。")
        else:
            logger.info("没有找到 'Continue with a wallet' 元素。")
    else:
        logger.info("没有找到 'Sign up to earn NEX' 元素。")

    time.sleep(3)
    logger.info("再次查看是否需要联网。")
    # 定位到包含 shadow DOM 的元素
    shadow_host = tab.ele('x://div[@data-testid="dynamic-modal-shadow"]')
    if shadow_host:
        # 进入 shadow DOM
        logger.info("找到122。")
        shadow_root = shadow_host.shadow_root
        if shadow_root:
            logger.info("找到12。")
            newtwork = shadow_root.ele('x://button[@data-testid="SelectNetworkButton"]')
            if newtwork:
                logger.info("找到1。")
                newtwork.click(by_js=True)
                time.sleep(2)
                myriad_pop(tab)
                time.sleep(2)
                myriad_pop(tab)
                time.sleep(3)
            else:
                logger.info("没有找到1。")
        else:
            logger.info("没有找到1。")
    else:
        logger.info("没有找到22。")

    time.sleep(3)
    logger.info("再次查看是否需要联网。")
    # 定位到包含 shadow DOM 的元素
    shadow_host = tab.ele('x://div[@data-testid="dynamic-modal-shadow"]')
    if shadow_host:
        # 进入 shadow DOM
        logger.info("找到12233。")
        shadow_root = shadow_host.shadow_root
        if shadow_root:
            logger.info("找到123。")
            newtwork = shadow_root.ele('x://button[.//span[text()="Continue"]]')
            if newtwork:
                logger.info("找到13。")
                newtwork.click(by_js=True)
            else:
                logger.info("没有找到13。")
        else:
            logger.info("没有找到13。")
    else:
        logger.info("没有找到223。")

    # 进入循环，持续监控切换按钮状态
    monitor_switch(tab, client, serverId, appId, user, display, public_key)



def myriad_pop(self):
    time.sleep(5)
    if len(self.browser.get_tabs(title="Signma")) > 0:
        pop_tab = self.browser.get_tab(title="Signma")
        back_path = 'x://*[@id="sign-root"]/div/div/section/main/div[1]/section[1]/div/button'
        conn_path = "tag:div@@class=jsx-3858486283 button_content@@text()=连接"
        sign_enable_path = (
            "tag:button@@class=jsx-3858486283 button large primaryGreen"
        )

        sign_blank_path = (
            "tag:div@@class=jsx-1443409666 subtext@@text()^希望您使用您的登录"
        )

        if pop_tab.url == 'chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/popup.html?page=%2Fdapp-permission':
            if pop_tab.ele(back_path) is not None:
                try:
                    pop_tab.ele(back_path).click()
                    time.sleep(2)
                except Exception as e:
                    logger.info(f"点击button失败")

            if pop_tab.ele(conn_path) is not None:
                try:
                    pop_tab.ele(conn_path).click()
                    time.sleep(3)
                except Exception as e:
                    logger.info(f"点击连接失败")
        elif "chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/popup.html?page=%2Fpersonal-sign":
            while pop_tab.wait.ele_displayed(sign_enable_path, timeout=3) is False:
                if pop_tab.wait.ele_displayed(sign_blank_path, timeout=3):
                    pop_tab.actions.move_to(sign_blank_path)
                    pop_tab.ele(sign_blank_path).click()
                    time.sleep(2)

            if pop_tab.ele(sign_enable_path) is not None:
                pop_tab.ele(sign_enable_path).click()


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


def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def setup_wallet(self, key):
    extensions = self.browser.new_tab(url="chrome://extensions/")
    time.sleep(3)

    toggle_ele = (
        extensions.ele(
            "x://html/body/extensions-manager"
        )  # /html/body/extensions-manager
        .shadow_root.ele('x://*[@id="viewManager"]')
        .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
        .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
        .shadow_root.ele("tag:cr-toggle@@id=enableToggle")
    )

    refresh_ele = (
        extensions.ele(
            "x://html/body/extensions-manager"
        )  # /html/body/extensions-manager
        .shadow_root.ele('x://*[@id="viewManager"]')
        .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
        .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
        .shadow_root.ele("tag:cr-icon-button@@id=dev-reload-button")
    )

    toggle_ele.attr("aria-pressed")
    if toggle_ele.attr("aria-pressed") == "false":
        toggle_ele.click()

    refresh_ele.click()

    time.sleep(2)
    wallet_tab = extensions.browser.new_tab(
        url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
    )

    time.sleep(3)
    index_input_path = (
        "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
    )
    wallet_tab.ele(index_input_path).input(key, clear=True)
    index_button_path = "tag:button@@id=existingWallet"
    index_set_button = wallet_tab.ele(index_button_path)

    index_set_button.click()

    return extensions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    args = parser.parse_args()

    # MQTT 配置
    BROKER = "150.109.5.143"
    PORT = 1883
    TOPIC = "appInfo"
    USERNAME = "userName"
    PASSWORD = "liuleiliulei"

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client(BROKER, PORT, USERNAME, PASSWORD, TOPIC)
    client.loop_start()
    # 启动网络循环
    main(client, args.serverId, args.appId, args.decryptKey, args.user, args.display)
