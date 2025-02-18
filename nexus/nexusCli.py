import subprocess
import time
import re
import paho.mqtt.client as mqtt
import json
import argparse
import base64
from loguru import logger
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def run_command_blocking(cmd, print_output=True):
    """
    执行命令，等待命令执行结束，并返回输出内容。
    """
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if print_output:
        print(result.stdout)
    return result.stdout


def run_command_and_print(cmd, wait_for=None, print_output=True):
    """
    实时执行命令，打印输出。如果指定了 wait_for，当检测到该关键字时返回已收集的输出内容。
    """
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    collected_output = ""
    while True:
        line = process.stdout.readline()
        if line:
            collected_output += line
            if print_output:
                print(line.strip())
            if wait_for and wait_for in line:
                break
        if not line and process.poll() is not None:
            break
    process.wait()  # 确保进程退出
    return collected_output


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


def write_to_file(file_path, content):
    """
    将给定的内容写入到指定的文件中。
    """
    try:
        with open(file_path, 'w') as file:
            file.write(content)
        logger.info(f"内容成功写入到 {file_path}")
    except Exception as e:
        logger.info(f"写入文件时发生错误: {e}")


def main(client, serverId, appId, decryptKey, user, display):

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + appId + '_user.json')
    # 获取密钥
    private_Key = decrypt_aes_ecb(decryptKey, encrypted_data_base64, 'privateKey')

    if private_Key is None:
        logger.info("未绑定密钥。")
    else:
        logger.info(f"绑定密钥。{private_Key}")
    # 1. 安装
    logger.info("===== 执行安装 =====")
    install_output = run_command_blocking("curl https://cli.nexus.xyz/ | sh")
    if "Installation completed successfully." not in install_output:
        logger.info("安装失败或未检测到成功提示。")
        return
    logger.info("安装成功！")

    # 获取积分
    while True:
        try:
            # app_info = get_app_info_integral(serverId, appId, private_Key, points, 2, '运行中， 并到采集积分:' + str(points))
            # client.publish("appInfo", json.dumps(app_info))
            time.sleep(30)
            logger.info("测试！")
        except Exception as e:
            client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 3, '检查过程中出现异常: ' + str(e))))

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
            if item.get('accountType') == 'hyperCli':
                return item.get(key)

        # 没有找到匹配的记录，返回 None
        return None

    except Exception as e:
        raise ValueError(f"解密失败: {e}")


if __name__ == "__main__":
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

    # 创建 MQTT 客户端
    client = create_mqtt_client(BROKER, PORT, USERNAME, PASSWORD, TOPIC)
    client.loop_start()
    main(client, args.serverId, args.appId, args.decryptKey, args.user, args.display)
