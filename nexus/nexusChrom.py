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
          .add_extension(r"/home/"+user+"/extensions/chrome-cloud"))
    arguments = [
        "--accept-lang=en-US", "--no-first-run", "--force-color-profile=srgb",
        "--metrics-recording-only", "--password-store=basic", "--use-mock-keychain",
        "--export-tagged-pdf", "--disable-gpu", "--disable-web-security",
        "--disable-infobars", "--disable-popup-blocking", "--allow-outdated-plugins",
        "--deny-permission-prompts", "--disable-suggestions-ui", "--window-size=1920,1080",
        "--disable-mobile-emulation", "--user-data-dir=/tmp/nexus/userData/9515",
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
            if item.get('accountType') == 'hyper':
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


def monitor_switch(tab, client, serverId, appId, user, display):
    total = 58
    error = 5
    first = 0
    num = random.randint(10, 20)

    while True:
        try:
            time.sleep(num)

            # 1. 先定位到外部 div（class 中包含 "transition-transform"）
            # 2. 在该 div 内部查找 class 中包含 "invert" 的 img
            xpath_for_invert_img = (
                'x://div[contains(@class, "transition-transform")]'
                '//img[contains(@class, "invert")]'
            )

            # 等待并获取该 img 元素
            invert_img_ele = tab.ele(xpath_for_invert_img)

            if invert_img_ele:
                logger.info("找到外部 div 内带 'invert' class 的 img，执行点击...")
                invert_img_ele.click()
                logger.info("点击完毕。")
            else:
                logger.info("未能在外部 div 中找到带 'invert' class 的 img，可能无需点击或请检查定位。")

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
    public_key = ""
    # 启动浏览器
    logger.info(f"start")
    tab = configure_browser(user)
    logger.info(f"安装钱包")
    tab = setup_wallet(tab, 37826)
    time.sleep(20)
    tab = tab.browser.new_tab(url="https://app.nexus.xyz")

    # 点击 "Sign up to earn NEX" 元素
    signup_ele = tab.ele('//div[text()="Sign up to earn NEX"]')
    if signup_ele:
        signup_ele.click()
        # 根据实际情况调整等待时间，确保页面加载完成
        time.sleep(2)

        # 点击 "Continue with a wallet" 元素
        wallet_ele = tab.ele('//p[contains(text(), "Continue with a wallet")]')
        if wallet_ele:
            wallet_ele.click()
            time.sleep(2)
            # 点击页面中显示 "Signma" 的元素
            signma_ele = tab.ele('//span[text()="Signma"]')
            if signma_ele:
                signma_ele.click()
            else:
                print("没有找到 'Signma' 元素。")
        else:
            print("没有找到 'Continue with a wallet' 元素。")
    else:
        print("没有找到 'Sign up to earn NEX' 元素。")

    # 进入循环，持续监控切换按钮状态
    monitor_switch(tab, client, serverId, appId, user, display)


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
        print("Connected to broker successfully.")
        # 仅发布消息，去除订阅
        pass
    else:
        print(f"Connection failed with reason code: {reason_code}")


def on_disconnect(client, userdata, reason_code, properties=None):
    """
    当客户端与 Broker 断开连接后触发
    可以在此处进行自动重连逻辑
    """
    print(f"Disconnected from broker, reason_code: {reason_code}")
    # 如果 reason_code != 0，则表示非正常断开
    while True:
        try:
            print("Attempting to reconnect...")
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # 等待 5 秒后重试


def on_message(client, userdata, msg):
    """
    当收到订阅主题的新消息时触发
    v5 中的 on_message 参数与 v3.x 相同： (client, userdata, message)
    """
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")


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

    return extensions;


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
