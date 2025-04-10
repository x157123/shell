import subprocess
import time
import re
import argparse
from loguru import logger
import json
import zlib
import base64
import os
import paho.mqtt.client as mqtt


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



def run_command_blocking(cmd, print_output=True):
    """
    执行命令，等待命令执行结束，并返回输出内容。
    """
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if print_output:
        logger.info(result.stdout)
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
                logger.info(line.strip())
            if wait_for and wait_for in line:
                break
        if not line and process.poll() is not None:
            break
    process.wait()  # 确保进程退出
    return collected_output



def read_last_n_lines(file_path, n):
    """读取文件最后 n 行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # 使用 collections.deque 高效读取最后 n 行
            from collections import deque
            lines = deque(file, maxlen=n)
            return list(lines)
    except FileNotFoundError:
        logger.info(f"错误：文件 {file_path} 未找到。")
        return []
    except Exception as e:
        logger.info(f"读取文件时发生错误：{e}")
        return []


def check_reconnect_signal(lines, target_string):
    """检查指定字符串是否在行列表中"""
    for line in lines:
        if target_string in line:
            return True
    return False


def get_app_info_integral(serverId, appId, public_key, integral, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "publicKey": f"{public_key}",
        "integral": f"{integral}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def start():
    # install_output = run_command_blocking("curl https://download.hyper.space/api/install | bash")
    # if "Installation completed successfully." not in install_output:
    #     logger.info("安装失败或未检测到成功提示。")
    # logger.info("安装成功！")

    logger.info("===== 检测是否已启动 =====")
    status_output = run_command_blocking("/root/.aios/aios-cli status")
    if "Daemon running on" in status_output:
        logger.info("杀掉程序。")
        run_command_blocking("/root/.aios/aios-cli kill")
        time.sleep(10)  # 等待 10 秒
    logger.info("检查结束！")

    # 2. 启动后端服务（后台运行，不阻塞）
    subprocess.Popen("/root/.aios/aios-cli start", shell=True)
    logger.info("后端命令已启动。")
    time.sleep(5)  # 等待后端服务启动

    # Hive 登录，提取 Public 和 Private Key
    logger.info("开始 Hive 登录...")
    run_command_and_print("/root/.aios/aios-cli hive login", wait_for="Authenticated successfully!")

    # if public_key is not None:
    #     logger.info("已配置了key...")
    # else:

    # time.sleep(2)
    # # 导入私钥
    # logger.info("导入私钥...")
    # subprocess.Popen("/root/.aios/aios-cli hive import-keys /root/.config/hyperspace/imp.pem", shell=True)

    time.sleep(5)

    # 6. 获取key执行 hive whoami 命令
    logger.info("执行 hive whoami 命令...")
    login_output = run_command_blocking("/root/.aios/aios-cli hive whoami")
    public_key = None
    private_key = None
    public_match = re.search(r"Public:\s*(\S+)", login_output)
    private_match = re.search(r"Private:\s*(\S+)", login_output)
    if public_match:
        public_key = public_match.group(1)
    if private_match:
        private_key = private_match.group(1)

    with open("/root/.config/hyperspace/key.pem", "r", encoding="utf-8") as file:
        key_content = file.read()

    logger.info(f"Public Key: {public_key}")
    logger.info(f"Private Key: {private_key}")
    # logger.info(f"key_content: {key_content}")
    logger.info("whoami 命令执行完毕。")

    # 7. 执行 hive select-tier 5 命令
    logger.info("执行 hive select-tier 5 命令...")
    run_command_blocking("/root/.aios/aios-cli hive select-tier 5")
    logger.info("select-tier 命令执行完毕。")

    # 8. 执行 hive connect 命令
    logger.info("执行 hive connect 命令...")
    run_command_blocking("/root/.aios/aios-cli hive connect")
    logger.info("connect 命令执行完毕。")


def restart():
    logger.info("===== 检测是否已启动 =====")
    status_output = run_command_blocking("/root/.aios/aios-cli status")
    if "Daemon running on" in status_output:
        logger.info("杀掉程序。")
        run_command_blocking("/root/.aios/aios-cli kill")
        time.sleep(10)  # 等待 10 秒
    logger.info("检查结束！")

    logger.info("开始 Hive 登录...")
    run_command_and_print("/root/.aios/aios-cli hive login", wait_for="Authenticated successfully!")

    logger.info("执行 hive connect 命令...")
    run_command_blocking("/root/.aios/aios-cli hive connect")
    logger.info("connect 命令执行完毕。")

def decompress_data(compressed_b64):
    # 先进行 base64 解码，得到压缩后的 bytes
    compressed = base64.b64decode(compressed_b64)
    # 解压得到原始 JSON 字符串
    json_str = zlib.decompress(compressed).decode('utf-8')
    # 将 JSON 字符串转换回字典
    data = json.loads(json_str)
    return data


def set_proxy(proxy):
    # # 定义文件路径
    # env_file_path = '/etc/environment'
    #
    # # 读取现有的 /etc/environment 文件内容
    # with open(env_file_path, 'r') as file:
    #     lines = file.readlines()
    #
    # # 删除已有的 http_proxy 和 https_proxy 设置（不区分大小写）
    # lines = [line for line in lines if not re.match(r'^[Hh][Tt][Tt][Pp]_proxy=', line) and not re.match(r'^[Hh][Tt][Tt][Pp][Ss]_proxy=', line)]
    #
    # # 添加新的代理配置
    # lines.append(f'http_proxy="http://{proxy}"\n')
    # lines.append(f'https_proxy="http://{proxy}"\n')
    #
    # # 将修改后的内容写回到 /etc/environment 文件
    # with open(env_file_path, 'w') as file:
    #     file.writelines(lines)
    #
    # print("代理设置已更新")

    # 使用 subprocess 调用 source 命令重新加载环境变量
    # subprocess.run(["source", "/etc/environment"], shell=True)
    print("环境变量已重新加载")


def create_key_file(expected_content, key_path="/root/.config/hyperspace/imp.pem"):
    file_exists = os.path.exists(key_path)
    expected = expected_content.strip()
    try:
        # 文件存在时验证内容
        if file_exists:
            os.remove(key_path)
            logger.info(f"旧密钥文件 {key_path} 已被删除。")

        # 原子写入模式：先写入临时文件再重命名
        temp_path = key_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(expected + "\n")  # 确保末尾换行符

        # 设置严格权限（仅用户可读）
        os.chmod(temp_path, 0o600)
        os.rename(temp_path, key_path)  # 原子操作

        logger.info(f"已创建新密钥文件2: {key_path}")

    except PermissionError:
        logger.info(f"权限不足，无法操作文件 {key_path}")
        return file_exists, False
    except Exception as e:
        logger.info(f"文件操作异常: {str(e)}")
        return file_exists, False


def ensure_key_file(expected_content, key_path="/root/.config/hyperspace/key.pem"):
    """
    确保密钥文件存在且内容匹配，不存在时自动创建
    返回: (文件存在状态, 内容匹配状态)
    """
    # 预处理输入内容
    expected = expected_content.strip()

    # 验证PEM格式有效性
    if not (expected.startswith("-----BEGIN PRIVATE KEY-----") and
            expected.endswith("-----END PRIVATE KEY-----")):
        raise ValueError("Invalid PEM private key format")

    # 检查文件存在性
    file_exists = os.path.exists(key_path)

    try:
        # 文件存在时验证内容
        if file_exists:
            # 如果内容不匹配，删除旧的密钥文件
            os.remove(key_path)
        # 原子写入模式：先写入临时文件再重命名
        temp_path = key_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(expected + "\n")  # 确保末尾换行符

        # 设置严格权限（仅用户可读）
        os.chmod(temp_path, 0o600)
        os.rename(temp_path, key_path)  # 原子操作

        logger.info(f"已创建新密钥文件2: {key_path}")
        return
    except Exception as e:
        logger.info(f"文件操作异常: {str(e)}")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--data", type=str, help="数据", required=True)
    args = parser.parse_args()

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()

    logger.info(f"===== 启动 ====={args.data}")
    restored_data = decompress_data(args.data)
    logger.info(f"恢复后的数据：{restored_data['publicKey']}")
    logger.info(f"恢复后的数据：{restored_data['privateKey']}")
    logger.info(f"恢复后的数据：{restored_data['remarks']}")
    
    ensure_key_file(restored_data['remarks'])

    time.sleep(20)
    start()
    # 等待20S
    time.sleep(20)
    num = 10
    count = 0
    # 获取积分
    while True:
        try:
            num += 1
            # 读取最后 3 行
            last_lines = read_last_n_lines('/opt/hyperCloudCli.log', 3)
            if last_lines:
                # 查找是否网络连接失败 Sending reconnect signal
                if check_reconnect_signal(last_lines, 'Sending reconnect signal'):
                    logger.info(f"未连接网络。重新连接->{num}")
                    start()
                else:
                    count = 0
                    logger.info(f"已连接网络。->{num}")

            if num > 10:
                logger.info("\n===== 积分查询输出 =====")
                login_output = run_command_blocking("/root/.aios/aios-cli hive points")
                points = None
                public_match = re.search(r"Points:\s*(\S+)", login_output)
                if public_match:
                    points = public_match.group(1)

                if not points or points == "None":
                    logger.info("获取积分失败,重新启动。")
                    start()
                else:
                    count = 0
                    num = 0
                    logger.info(f"points: {points}")
                    app_info = get_app_info_integral('0', '0', restored_data['publicKey'], points, 2,
                                                     '运行中， 并到采集积分:' + str(points))
                    client.publish("appInfo", json.dumps(app_info))
                    logger.info("获取积分完成。")
            time.sleep(360)
        except Exception as e:
            logger.info("异常。")