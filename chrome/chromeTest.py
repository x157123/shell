import time
from DrissionPage._base.chromium import Chromium
from DrissionPage._configs.chromium_options import ChromiumOptions
from DrissionPage._base.wait import Wait
import paho.mqtt.client as mqtt
import json
import argparse
from loguru import logger
import pyperclip


def configure_browser():
    """配置并启动浏览器"""
    co = ChromiumOptions().set_local_port(9515).set_paths(r"/opt/google/chrome/google-chrome")
    arguments = [
        "--accept-lang=en-US", "--no-first-run", "--force-color-profile=srgb",
        "--metrics-recording-only", "--password-store=basic", "--use-mock-keychain",
        "--export-tagged-pdf", "--disable-gpu", "--disable-web-security",
        "--disable-infobars", "--disable-popup-blocking", "--allow-outdated-plugins",
        "--deny-permission-prompts", "--disable-suggestions-ui", "--window-size=1920,1080",
        "--disable-mobile-emulation", "--user-data-dir=/path/to/your/user/data/directory"
    ]

    for arg in arguments:
        co.set_argument(arg)

    co.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

    browser = Chromium(co)
    tab = browser.new_tab(url="https://node.hyper.space/")
    return tab


def click_element(tab, xpath, timeout=2):
    """点击页面元素，若元素不存在则返回False"""
    try:
        element = Wait(tab, timeout=timeout).until(xpath)
        element.click()
        logger.info(f"Clicked the element: {xpath}")
        return True
    except TimeoutError:
        logger.info(f"No element found for XPath: {xpath} within {timeout} seconds.")
        return False
    except Exception as e:
        logger.error(f"Error while clicking element {xpath}: {e}")
        return False


def get_clipboard_text():
    """从剪贴板获取文本"""
    time.sleep(1)  # 确保剪贴板内容更新
    clipboard_text = pyperclip.paste()
    logger.info(f"Clipboard text: {clipboard_text}")
    return clipboard_text


def get_points(tab):
    # 获取积分：点击按钮后从剪贴板读取
    if click_element(tab, "x://button[.//span[text()='Points']]"):
        time.sleep(3)  # 确保剪贴板内容更新
        # 定位到指定的 div 元素并获取其文本内容
        target_div = tab.ele("x://div[text()='Accumlated points']/following-sibling::div")
        # 获取该 div 中的文本
        text = target_div.text
        logger.info(f"Text from the div: {text}")


def main():
    # 启动浏览器
    tab = configure_browser()

    # 关闭弹窗（如果存在）
    click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)

    # 切换按钮（将状态从未开启变为开启）
    click_element(tab, 'x://button[@role="switch" and @aria-checked="false"]', timeout=5)

    # 获取公钥：点击按钮后从剪贴板读取
    if click_element(tab, "x://p[contains(text(), 'Public Key:')]/following-sibling::div//button"):
        public_key = get_clipboard_text()

    # 获取私钥：点击按钮后从剪贴板读取
    if click_element(tab, "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
        if click_element(tab, "//button[contains(., 'copy current private key')]"):
            private_key = get_clipboard_text()

    # 关闭私钥弹窗（如果存在）
    click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)

    # 获取积分:
    get_points(tab)



def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }



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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="启动服务器信息推送脚本")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    args = parser.parse_args()

    # MQTT 配置
    BROKER = "150.109.5.143"
    PORT = 1883
    TOPIC = "appInfo"
    USERNAME = "userName"
    PASSWORD = "liuleiliulei"

    # 创建 MQTT 客户端
    client = create_mqtt_client(BROKER, PORT, USERNAME, PASSWORD, TOPIC)
    client.loop_start()
    
    try:
        main()
        while True:
            time.sleep(60)  # 每 60 秒发送一次
            # 获取应用信息并发送
            app_info = get_app_info(args.serverId, args.appId, 2, '运行中，获取相应数据')
            client.publish(TOPIC, json.dumps(app_info))
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        client.loop_stop()
        client.disconnect()

