from DrissionPage import ChromiumPage, ChromiumOptions
import time
import pyperclip
import random
import json
from loguru import logger
import paho.mqtt.client as mqtt
import argparse

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

def get_points(tab):
    # 获取积分：点击按钮后从剪贴板读取
    if __click_ele(tab, "x://button[.//span[text()='Points']]"):
        time.sleep(15)  # 确保剪贴板内容更新
        # 定位到指定的 div 元素并获取其文本内容
        target_div = tab.ele("x://div[text()='Accumlated points']/following-sibling::div")
        # 获取该 div 中的文本
        text = target_div.text
        # logger.info(f"Text from the div: {text}")
        return text


def __click_ele(_page, xpath: str = '', loop: int = 5, must: bool = False,
                find_all: bool = False,
                index: int = -1) -> bool:
    loop_count = 1
    while True:
        # logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                _page.ele(locator=xpath).click()
            else:
                _page.eles(locator=xpath)[index].click()
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


def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def get_app_info_integral(serverId, appId, public_key, integral, operationType, integralE, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "publicKey": f"{public_key}",
        "integral": f"{integral}",
        "operationType": f"{operationType}",
        "integralE": f"{integralE}",
        "description": f"{description}",
    }

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


def monitor_switch(tab):
    total = 70
    error = 5
    num = random.randint(6, 8)
    while True:
        try:
            time.sleep(num)
            logger.info("sw")
            if __get_ele(page=tab, xpath='x://button[@role="switch"]', loop=2):
                if __click_ele(_page=tab, xpath='x://button[@role="switch" and @aria-checked="false"]', loop=2):
                    logger.info("not net")
                    error += 1
                else:
                    if __get_ele(page=tab, xpath='x://span[text()="Connected"]', loop=1):
                        logger.info("net")
                        if error > 0:
                            client.publish("appInfo",
                                           json.dumps(get_app_info(args.serverId, args.appId, 2, '已连接到主网络')))
                        error = 0

                        if total > 60:
                            # 获取积分 每循环60次检测 获取一次积分
                            points = get_points(tab)
                            # 关闭积分弹窗（如果存在）
                            __click_ele(tab, 'x://button[.//span[text()="Close"]]')
                            if points is not None and points != "":
                                app_info = get_app_info_integral(args.serverId, args.appId, im_public_key, points, 2, args.display,
                                                                 '运行中， 并到采集积分:' + str(points))
                                client.publish("appInfo", json.dumps(app_info))
                                logger.info(f"推送积分:{points}")
                                total = 0
                            elif total > 70:
                                logger.info(f"需要刷新页面。{total}")
                                total = 30
                                tab.refresh()
                if error == 9:
                    tab.refresh()
                    time.sleep(3)
                    logger.info("refresh page:")    # 关闭弹窗（如果存在）
                    __click_ele(tab, 'x://button[.//span[text()="Close"]]')

                if error == 10:
                    client.publish("appInfo",
                                   json.dumps(get_app_info(args.serverId, args.appId, 3, '检查过程中出现异常：未连接到主网络')))
                    error = 0
            else:
                logger.info("refresh")
                tab.refresh()

            total += 1
        except Exception as e:
            client.publish("appInfo", json.dumps(get_app_info(args.serverId, args.appId, 3, '检查过程中出现异常: ' + str(e))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    # parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    # parser.add_argument("--appId", type=str, help="应用ID", required=True)
    # parser.add_argument("--display", type=str, help="执行窗口", required=True)
    # parser.add_argument("--publicKey", type=str, help="公钥", required=True)
    # parser.add_argument("--privateKey", type=str, help="私钥", required=True)
    args = parser.parse_args()
    data_map = {}
    # .....................
    options = ChromiumOptions()
    # options.set_browser_path(r'C:\Users\liulei\Desktop\chrome-win\chrome.exe')
    options.set_browser_path('/usr/bin/chromium-browser')

    # ...............
    page = ChromiumPage(options)
    page.get('https://node.hyper.space/')

    args.serverId = '1'
    args.appId = '1'
    args.display = '5903'
    args.publicKey = 'J4BRHjFRNd438DcigpiooJd17FXdFuuXvYYzMhUpFyCN'
    args.privateKey = 'G9afgDMmmSnjNWAENgvyMK2dAEZmsFZCxDzy5Q6LcV3z'

    im_public_key = args.publicKey
    im_private_Key = args.privateKey

    time.sleep(5)
    if __click_ele(page, "x://p[text()='Public Key:']/following-sibling::div//button"):
        public_key = pyperclip.paste().strip()
        print(public_key)
        if public_key is not None and public_key != im_public_key:
            if __click_ele(page, "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
                if __click_ele(page, "x://div[contains(@class, 'cursor-text')]"):
                    print(f"write key")
                    page.actions.type(im_private_Key)
                    time.sleep(1)
                    # 确认导入
                    __click_ele(page, "x://button[normalize-space()='IMPORT KEY']")
                    time.sleep(5)
                    page.refresh()
                    time.sleep(3)
            # 关闭私钥弹窗（如果存在）
            __click_ele(_page=page, xpath='x://button[.//span[text()="Close"]]',loop=2)

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()

    # 进入循环，持续监控切换按钮状态
    monitor_switch(page)
