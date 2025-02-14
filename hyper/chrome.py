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


def configure_browser():
    """配置并启动浏览器"""
    co = ChromiumOptions().set_local_port(9515).set_paths(r"/opt/google/chrome/google-chrome")
    arguments = [
        "--accept-lang=en-US", "--no-first-run", "--force-color-profile=srgb",
        "--metrics-recording-only", "--password-store=basic", "--use-mock-keychain",
        "--export-tagged-pdf", "--disable-gpu", "--disable-web-security",
        "--disable-infobars", "--disable-popup-blocking", "--allow-outdated-plugins",
        "--deny-permission-prompts", "--disable-suggestions-ui", "--window-size=1920,1080",
        "--disable-mobile-emulation", "--user-data-dir=/tmp/DrissionPage/userData/9515",
        "--disable-features=ServerSentEvents"
    ]

    for arg in arguments:
        co.set_argument(arg)

    co.set_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

    browser = Chromium(co)
    tab = browser.new_tab(url="https://node.hyper.space/")
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


def get_clipboard_text():
    """从剪贴板获取文本"""
    time.sleep(1)  # 确保剪贴板内容更新
    clipboard_text = pyperclip.paste()
    # logger.info(f"Clipboard text: {clipboard_text}")
    return clipboard_text


def get_points(tab):
    # 获取积分：点击按钮后从剪贴板读取
    if click_element(tab, "x://button[.//span[text()='Points']]"):
        time.sleep(3)  # 确保剪贴板内容更新
        # 定位到指定的 div 元素并获取其文本内容
        target_div = tab.ele("x://div[text()='Accumlated points']/following-sibling::div")
        # 获取该 div 中的文本
        text = target_div.text
        # logger.info(f"Text from the div: {text}")
        return text


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


def monitor_switch(tab, client, serverId, appId, public_key_tmp):
    total = 0
    error = 5
    first = 0
    num = random.randint(60, 80)
    public_key = ''
    if public_key_tmp is None:
        first = 1
    else:
        public_key = public_key_tmp
    while True:
        try:
            time.sleep(num)

            if click_element(tab, 'x://button[@role="switch" and @aria-checked="false"]', timeout=5):
                logger.info("未连接到主网络")
                error += 1
            else:
                logger.info("已连接到主网络")
                if first > 0:
                    # 如果是第一次连接 推送key到服务器上
                    push_key(tab, client, serverId)
                    first = 0
                if error > 0:
                    client.publish("appInfo",
                                   json.dumps(get_app_info(serverId, appId, 2, '已连接到主网络')))
                    error = 0
                if total > 60:
                    # 获取积分 每循环60次检测 获取一次积分
                    points = get_points(tab)
                    # 关闭积分弹窗（如果存在）
                    click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)
                    if points is not None and points != "":
                        app_info = get_app_info_integral(serverId, appId, public_key, points, 2, '运行中， 并到采集积分:' + str(points))
                        client.publish("appInfo", json.dumps(app_info))
                        total = 0

            if error > 5:
                logger.info("检查过程中出现异常：未连接到主网络")
                if first > 0:
                    reset_key(tab)
                    client.publish("appInfo",
                                   json.dumps(get_app_info(serverId, appId, 3, '检查过程中出现异常：未连接到主网络,重置私钥')))
                else:
                    client.publish("appInfo",
                                   json.dumps(get_app_info(serverId, appId, 3, '检查过程中出现异常：未连接到主网络')))
                error = 0

            total += 1
        except Exception as e:
            client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 3, '检查过程中出现异常: ' + str(e))))


# 获取key
def push_key(tab, client, serverId):
    # 获取公钥：点击按钮后从剪贴板读取
    if click_element(tab, "x://p[text()='Public Key:']/following-sibling::div//button"):
        public_key = get_clipboard_text()
        # 获取私钥：点击按钮后从剪贴板读取
        if click_element(tab,
                         "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
            if click_element(tab, "x://button[contains(., 'copy current private key')]"):
                private_key = get_clipboard_text()
                logger.info(f"send key")
                # 保存私钥
                client.publish("hyperKey", json.dumps(get_info(serverId, "hyper", public_key, private_key)))
        time.sleep(2)
        click_element(tab, 'x://button[@role="switch" and @aria-checked="false"]', timeout=5)
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
    click_element(tab, 'x://button[@role="switch" and @aria-checked="false"]', timeout=5)

def main(client, serverId, appId, decryptKey):
    public_key = ""

    # 启动浏览器
    tab = configure_browser()

    # 关闭弹窗（如果存在）
    click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)

    # 切换按钮（将状态从未开启变为开启）
    click_element(tab, 'x://button[@role="switch" and @aria-checked="false"]', timeout=5)

    # 获取公钥：点击按钮后从剪贴板读取
    if click_element(tab, "x://p[text()='Public Key:']/following-sibling::div//button"):
        public_key = get_clipboard_text()

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + appId + '_user.json')
    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(decryptKey, encrypted_data_base64, 'publicKey')
    # logger.info(f"获取公共key {public_key} ---：{public_key_tmp}")
    if public_key_tmp is not None and public_key != public_key_tmp:
        if click_element(tab,
                         "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
            div_el = get_element(tab, "x://div[contains(@class, 'cursor-text')]", timeout=5)
            if div_el is not None:
                # 聚焦
                div_el.click()
                # 发送密钥
                private_Key = decrypt_aes_ecb(decryptKey, encrypted_data_base64, 'privateKey')
                logger.info(f"write key")
                tab.actions.type(private_Key)
                time.sleep(1)
                # 确认导入
                click_element(tab, "x://button[normalize-space()='IMPORT KEY']")

        # 关闭私钥弹窗（如果存在）
        click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)

    # 进入循环，持续监控切换按钮状态
    monitor_switch(tab, client, serverId, appId, public_key_tmp)




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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
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
    main(client, args.serverId, args.appId, args.decryptKey)
