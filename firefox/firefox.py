import time
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import paho.mqtt.client as mqtt
import json
import argparse

def open_chrome():

    # 确认我们要使用 Firefox 的 Capabilities
    caps = DesiredCapabilities.FIREFOX.copy()
    
    # 连接到已经在 9515 端口监听的 geckodriver
    driver = webdriver.Remote(
        command_executor='http://127.0.0.1:9515',
        desired_capabilities=caps
    )

    # 打开某个网站
    driver.get("https://node.hyper.space/")

    # 暂停 5 秒等待页面加载
    time.sleep(5)



def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def create_mqtt_client(broker, port, username, password, topic):
    """创建并配置MQTT客户端"""
    client = mqtt.Client(userdata={"topic": topic})
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        raise ConnectionError(f"Error connecting to broker: {e}")

    return client

# MQTT 事件回调函数
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker successfully")
        client.subscribe(userdata["topic"])
    else:
        print(f"Connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    print("Disconnected from broker")
    while True:
        try:
            print("Attempting to reconnect...")
            client.reconnect()
            print("Reconnected successfully")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # 等待 5 秒后重试

def on_message(client, userdata, msg):
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")


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
        open_chrome()
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

