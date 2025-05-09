#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from DrissionPage import ChromiumPage
import threading
import paho.mqtt.client as mqtt
import time
import json
import base64
import subprocess
import argparse
from loguru import logger
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

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


def read_file(file_path):
    """从文件中读取内容并去除多余空白"""
    try:
        # logger.info(f"读取文件: {file_path}")
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

        logger.info(data_list)

        # 创建结果列表，收集所有 accountType 为 "hyper" 的记录
        result = [item for item in data_list if item.get('accountType') == accountType]

        # 返回结果列表，如果没有匹配项则返回空列表
        return result
    except Exception as e:
        # 记录错误日志
        logger.error(f"解密失败: {e}")
        return []


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




def poll_element(tab, public_key, key, endpoint, port):

    total = 70
    error = 5
    _init = 0

    while True:
        try:
            logger.info(f"{port}:{public_key}:检测状态")
            if __get_ele(page=tab, xpath='x://button[@role="switch"]', loop=2):
                if _init == 0 and __click_ele(tab, "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
                    if __click_ele(tab, "x://div[contains(@class, 'cursor-text')]"):
                        logger.info(f"{port}:{public_key}:设置密钥")
                        tab.actions.type(key)
                        time.sleep(1)
                        # 确认导入
                        __click_ele(tab, "x://button[normalize-space()='IMPORT KEY']")
                        time.sleep(5)
                        tab.refresh()
                        time.sleep(3)
                        _init = 1
                    # 关闭私钥弹窗（如果存在）
                    __click_ele(_page=tab, xpath='x://button[.//span[text()="Close"]]', loop=2)

                if __click_ele(_page=tab, xpath='x://button[@role="switch" and @aria-checked="false"]', loop=2):
                    logger.info(f"{port}:{public_key}:未连接到网络")
                    error += 1
                else:
                    if __get_ele(page=tab, xpath='x://span[text()="Connected"]', loop=1):
                        logger.info(f"{port}:{public_key}:已连接网络")
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
                                app_info = get_app_info_integral(args.serverId, args.appId, public_key, points, 2, port,
                                                                 '运行中， 并到采集积分:' + str(points))
                                client.publish("appInfo", json.dumps(app_info))
                                logger.info(f"{port}:{public_key}:推送积分:{points}")
                                total = 0
                            elif total > 70:
                                logger.info(f"{port}:{public_key}:需要刷新页面。{total}")
                                total = 30
                                tab.refresh()
                    else:
                        logger.info(f"{port}:{public_key}:正在连接网络")
                        error += 1
                if error == 9:
                    logger.info(f"{port}:{public_key}:刷新页面")    # 关闭弹窗（如果存在）
                    tab.refresh()
                    time.sleep(3)
                    __click_ele(tab, 'x://button[.//span[text()="Close"]]')

                if error >= 10:
                    client.publish("appInfo",
                                   json.dumps(get_app_info(args.serverId, args.appId, 3, '检查过程中出现异常：未连接到主网络')))
                    error = 0
            else:
                logger.info(f"{port}:{public_key}:页面加载失败，刷新页面")
                tab.refresh()
        except Exception as e:
            print(f'[{key} | {endpoint}] 抓取失败: {e}')
        time.sleep(POLL_INTERVAL)


def _run(cmd: list[str], *, silent: bool = True) -> subprocess.CompletedProcess:
    """运行命令并返回 CompletedProcess；silent=True 时吞掉输出。"""
    kwargs = {}
    if silent:
        kwargs |= dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.run(cmd, check=False, text=True, **kwargs)


def start_chrome_in_container(index):
    """docker exec -d nodex_N /root/start_chrome_vnc.sh"""
    container = f'node{index}'

    try:
        # ① 查询运行状态（Running=true/false）
        running = subprocess.check_output(
            ['docker', 'inspect', '-f', '{{.State.Running}}', container],
            text=True
        ).strip().lower()
    except subprocess.CalledProcessError:
        raise RuntimeError(f'[init] 容器 {container} 不存在，请先创建')

    # ② 若未运行则启动
    if running != 'true':
        print(f'[init] 容器 {container} 未启动，执行 docker start ...')
        subprocess.check_call(['docker', 'start', container])
        print(f'[init] 容器 {container} 已启动')
        time.sleep(5)

    cmd = ['docker', 'exec', '-d', container, '/root/start_chrome_vnc.sh']
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f'[init] 已在容器 {container} 启动 /root/start_chrome_vnc.sh')
    except subprocess.CalledProcessError as e:
        print(f'[init] 容器 {container} 执行失败: {e}')
        raise


def main():
    threads = []

    # ③ 同时拿到序号(标签)和端口
    for idx, (key, port) in enumerate(zip(public_key_tmp, PORTS), start=1):
        endpoint = f'{HOST}:{port}'
        try:
            start_chrome_in_container(idx)
            time.sleep(20)
            page = ChromiumPage(addr_or_opts=endpoint)
            page.get(URL)
            print(f'[{key["publicKey"]} | {endpoint}] 打开成功 → {page.title}')

            t = threading.Thread(
                target=poll_element,
                args=(page, key["publicKey"], key["privateKey"], endpoint, port),
                daemon=True
            )
            t.start()
            threads.append(t)

        except Exception as err:
            print(f'[{key["publicKey"]} | {endpoint}] 连接失败: {err}')

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print('退出中…')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    args = parser.parse_args()
    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + args.appId + '_user.json')
    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(args.decryptKey, encrypted_data_base64, 'hyper')

    logger.info(f'我现在数据量{len(public_key_tmp)}')

    URL = 'https://node.hyper.space'
    HOST = '127.0.0.1'

    # ① 你的“任务数组”——内容按需修改
    # keys = ['2SBckLEM279e5ypQqJkmAxo2rkQJbtoWRUeB1zcsgzXd', '73F8jwu5CWUSmwJtDoaBCEekPkMqwsACadZ3ascttp8L', 'FNmB49DFeakiZetyuvihqJDE2Wf1jHTbDKhRYbWaMDUC', '561WbUqLhRqwQa3ioiLVTxUCyar9yAWXEBjedEwQ9txP', '2N9z9sTu5ExmKEHdo73U1q2HStunvVrscWxLyz69h74y', 'DF1Hkm5MpSW1UCFYQFSfZHciKpd5qe945rR4VMuBdXsk']
    # keys = []

    BASE_PORT = 6901
    PORTS = [BASE_PORT + i for i in range(len(public_key_tmp))]         # 动态生成 [6901, 6902, ...]

    POLL_INTERVAL = 70     # 3 分钟

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()
    if len(public_key_tmp) > 0:
        public_key_tmp.sort(key=lambda item: item['id'])
        for index, item in enumerate(public_key_tmp):
            # keys.append(item["publicKey"])
            logger.info(f'启动公钥:{item["publicKey"]}')
        main()
