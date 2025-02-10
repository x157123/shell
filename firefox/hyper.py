import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import paho.mqtt.client as mqtt
import json
import time
import argparse
import requests

def wait_and_click(driver, xpath, wait_time=10, description="元素", sleep_after=0):
    """
    等待指定的元素可点击，点击后返回 True，否则返回 False

    :param driver: Selenium webdriver 对象
    :param xpath: 元素的 XPath 定位表达式
    :param wait_time: 最大等待时间（秒）
    :param description: 元素的描述，用于日志输出
    :param sleep_after: 点击前额外等待时间（秒）
    :return: 布尔值，表示点击是否成功
    """
    try:
        element = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        if sleep_after:
            time.sleep(sleep_after)
        element.click()
        print(f"{description} 已点击。")
        return True
    except TimeoutException:
        print(f"未找到 {description}，或 {description} 未在限定时间内可点击。")
    except Exception as e:
        print(f"点击 {description} 时出错: {e}")
    return False


def get_clipboard_text(driver):
    """
    通过执行异步 JavaScript 从剪贴板中读取文本
    :param driver: Selenium webdriver 对象
    :return: 剪贴板中的文本
    """
    try:
        text = driver.execute_async_script("""
            const callback = arguments[arguments.length - 1];
            if (navigator.clipboard && navigator.clipboard.readText) {
                navigator.clipboard.readText()
                    .then(text => callback(text))
                    .catch(err => callback("读取剪贴板失败: " + err));
            } else {
                callback("当前浏览器不支持 Clipboard API");
            }
        """)
        return text
    except Exception as e:
        print(f"获取剪贴板内容时出错: {e}")
        return ""


def close_popup(driver):
    """
    等待并点击包含隐藏文本 "Close" 的按钮
    """
    xpath = '//button[.//span[text()="Close"]]'
    # 点击前等待 2 秒，确保页面渲染稳定
    return wait_and_click(driver, xpath, wait_time=10, description="Close 按钮", sleep_after=2)


def toggle_switch(driver):
    """
    等待并点击状态为未开启（aria-checked="false"）的切换按钮
    :return: 点击成功返回 True，否则返回 False
    """
    xpath = '//button[@role="switch" and @aria-checked="false"]'
    if wait_and_click(driver, xpath, wait_time=10, description="切换按钮"):
        print("切换按钮已点击，等待开启。")
        return True
    return False


def retrieve_public_key(driver):
    """
    点击页面上的“获取公钥”按钮，并通过剪贴板读取公钥
    :return: 获取到的公钥字符串
    """
    xpath = "//p[contains(text(), 'Public Key:')]/following-sibling::div//button"
    if wait_and_click(driver, xpath, wait_time=10, description="获取公钥按钮", sleep_after=1):
        print("正在获取公钥...")
        return get_clipboard_text(driver)
    return ""


def click_outer_button(driver):
    """
    点击外层容器内与“Public Key:”相关联的按钮
    """
    xpath = ("//div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]"
             "/button")
    wait_and_click(driver, xpath, wait_time=10, description="外层 div 平级的 button")


def retrieve_private_key(driver):
    """
    点击页面上的“获取私钥”按钮，并通过剪贴板读取私钥
    :return: 获取到的私钥字符串
    """
    xpath = "//button[contains(., 'copy current private key')]"
    if wait_and_click(driver, xpath, wait_time=10, description="获取私钥按钮", sleep_after=1):
        print("正在获取私钥...")
        return get_clipboard_text(driver)
    return ""


def monitor_switch(driver, client, serverId, appId):
    """
    循环检查切换按钮的状态，如果状态为未开启则点击切换按钮，
    同时统计连续未连接主网络的次数，并在异常超过一定次数时输出提示
    """
    total = 0
    count = 0
    while True:
        try:
            time.sleep(10)
            switch_button = driver.find_element(By.XPATH, "//button[@role='switch']")
            state = switch_button.get_attribute("aria-checked")
            if state == "true":
                print("已连接到主网络。")
                if total > 0 or count > 100:
                    app_info = get_app_info(serverId, appId, 2, '运行中，连接成功。')
                    client.publish(TOPIC, json.dumps(app_info))
                    count = 0
                total = 0
                count += 0
            else:
                if toggle_switch(driver):
                    if total > 5:
                        print("检查过程中出现异常：五分钟未连接到主网络")
                        app_info = get_app_info(serverId, appId, 3, '检查过程中出现异常：五分钟未连接到主网络')
                        client.publish(TOPIC, json.dumps(app_info))
                        total = 0
                    else:
                        print("检查过程中未连接到主网络:", total)
                        total += 1
        except Exception as e:
            print("检查过程中出现异常：", e)
            time.sleep(30)


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
        # 订阅主题（从 userdata 中获取）
        client.subscribe(userdata["topic"])
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


def post_info(url, server_id, public_key, private_key):
    """
    向指定的 URL 发送 POST 请求，参数以 JSON 格式传递
    """
    data = get_info(server_id, public_key, private_key)
    try:
        response = requests.post(url, json=data)  # 使用 json 参数，requests 会自动设置 Content-Type 为 application/json
        response.raise_for_status()  # 如果响应状态码不是 200 系列，将抛出异常
        return response.json()     # 返回解析后的 JSON 数据（前提是接口返回 JSON 格式数据）
    except requests.RequestException as e:
        print("请求发生异常：", e)
        return None


def main(client, serverId, appId):
    # 设置自定义下载目录（例如 /your/download/directory）
    profile_path  = "D://data/firefoxData"
    # 加载指定的 Firefox 配置文件
    profile = FirefoxProfile(profile_path)

    # 创建 Options 对象，并设置 profile
    options = Options()
    options.profile = profile

    # 初始化浏览器驱动并打开目标页面
    driver = webdriver.Firefox(options=options)
    driver.get("https://node.hyper.space")

    # 关闭弹窗（如果存在）
    close_popup(driver)

    # 切换按钮（将状态从未开启变为开启）
    toggle_switch(driver)

    # 获取公钥：点击按钮后从剪贴板读取
    public_key = retrieve_public_key(driver)
    print("公钥：", public_key)

    # 点击与公钥相关联的外层按钮（如有特殊逻辑需要执行）
    click_outer_button(driver)

    # 获取私钥：点击按钮后从剪贴板读取
    private_key = retrieve_private_key(driver)
    print("私钥：", private_key)

    # 发送公钥 私钥 需要更改为接口
    # post_info("http://localhost:4200/api/cloud-automation/accountInfo/save/hyper", serverId, public_key, private_key)
    client.publish('hyperKey', json.dumps(get_info(args.serverId,"hyper", public_key, private_key)))
    # 关闭弹窗（如果再次出现）
    close_popup(driver)

    # 进入循环，持续监控切换按钮状态
    monitor_switch(driver, client, serverId, appId)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
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
    main(client, args.serverId, args.appId)
