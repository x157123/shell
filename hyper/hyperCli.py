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
    public_key = start(client, serverId, appId, decryptKey, user, display)
    # 等待20S
    time.sleep(20)
    num = 10
    count = 0
    # 获取积分
    while True:
        try:
            num += 1
            # 读取最后 3 行
            last_lines = read_last_n_lines('/root/hyperCliOutput.log', 3)
            if last_lines:
                # 查找是否网络连接失败 Sending reconnect signal
                if check_reconnect_signal(last_lines, 'Sending reconnect signal'):
                    logger.info(f"未连接网络。重新连接->{num}")
                    count += 1
                    if count > 2:
                        restart()
                else:
                    count = 0
                    logger.info(f"已连接网络。->{num}")

            if num > 10:
                num = 0
                logger.info("\n===== 积分查询输出 =====")
                login_output = run_command_blocking("/root/.aios/aios-cli hive points")
                points = None
                public_match = re.search(r"Points:\s*(\S+)", login_output)
                if public_match:
                    points = public_match.group(1)

                if not points or points == "None":
                    logger.info("获取积分失败,重新启动。")
                    count += 1
                    if count > 2:
                        restart()
                        num = 7
                else:
                    count = 0
                    logger.info(f"points: {points}")
                    app_info = get_app_info_integral(serverId, appId, public_key, points, 2,
                                                     '运行中， 并到采集积分:' + str(points))
                    client.publish("appInfo", json.dumps(app_info))
                    logger.info("获取积分完成。")
            time.sleep(360)
        except Exception as e:
            client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 3, '检查过程中出现异常: ' + str(e))))


def read_last_n_lines(file_path, n):
    """读取文件最后 n 行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # 使用 collections.deque 高效读取最后 n 行
            from collections import deque
            lines = deque(file, maxlen=n)
            return list(lines)
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 未找到。")
        return []
    except Exception as e:
        print(f"读取文件时发生错误：{e}")
        return []


def check_reconnect_signal(lines, target_string):
    """检查指定字符串是否在行列表中"""
    for line in lines:
        if target_string in line:
            return True
    return False


def restart():
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

    # 3. 下载大模型，等待输出中出现 "Download complete"
    logger.info("开始下载大模型...")
    run_command_and_print(
        "/root/.aios/aios-cli models add hf:bartowski/Llama-3.2-1B-Instruct-GGUF:Llama-3.2-1B-Instruct-Q8_0.gguf", wait_for="Download complete"
    )
    logger.info("下载完成！")

    # # 4. 执行 infer 命令 测试模型
    # logger.info("执行 infer 命令 测试模型...")
    # run_command_and_print(
    #     "/root/.aios/aios-cli infer --model hf:bartowski/Llama-3.2-1B-Instruct-GGUF:Llama-3.2-1B-Instruct-Q8_0.gguf --prompt 'What is 1+1 equal to?'"
    # )
    # logger.info("推理命令执行完毕。")

    # 5. 执行 hive login 命令
    # Hive 登录，提取 Public 和 Private Key
    logger.info("开始 Hive 登录...")
    run_command_and_print("/root/.aios/aios-cli hive login", wait_for="Authenticated successfully!")


    # 7. 执行 hive select-tier 5 命令
    logger.info("执行 hive select-tier 5 命令...")
    run_command_blocking("/root/.aios/aios-cli hive select-tier 5")
    logger.info("select-tier 命令执行完毕。")

    # 8. 执行 hive connect 命令
    logger.info("执行 hive connect 命令...")
    run_command_blocking("/root/.aios/aios-cli hive connect")
    logger.info("connect 命令执行完毕。")


def start(client, serverId, appId, decryptKey, user, display):
    # # 1. 安装
    # logger.info("===== 执行安装 =====")
    # install_output = run_command_blocking("curl https://download.hyper.space/api/install | bash")
    # if "Installation completed successfully." not in install_output:
    #     logger.info("安装失败或未检测到成功提示。")
    #     return
    # logger.info("安装成功！")
    #
    # run_command_blocking("sudo chown -R root:root /root/.aios")

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

    # 3. 下载大模型，等待输出中出现 "Download complete"
    logger.info("开始下载大模型...")
    run_command_and_print(
        "/root/.aios/aios-cli models add hf:bartowski/Llama-3.2-1B-Instruct-GGUF:Llama-3.2-1B-Instruct-Q8_0.gguf", wait_for="Download complete"
    )
    logger.info("下载完成！")

    # # 4. 执行 infer 命令 测试模型
    # logger.info("执行 infer 命令 测试模型...")
    # run_command_and_print(
    #     "/root/.aios/aios-cli infer --model hf:bartowski/Llama-3.2-1B-Instruct-GGUF:Llama-3.2-1B-Instruct-Q8_0.gguf --prompt 'What is 1+1 equal to?'"
    # )
    # logger.info("推理命令执行完毕。")

    # 5. 关联密钥
    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + appId + '_user.json')
    # 解密并发送解密结果
    pem = decrypt_aes_ecb(decryptKey, encrypted_data_base64, "remarks")
    publicKey = decrypt_aes_ecb(decryptKey, encrypted_data_base64, "publicKey")

    # if pem is not None:
    #     logger.info("publicKey" + pem)
    # if publicKey is not None:
    #     logger.info("publicKey" + publicKey)

    # if private_key is not None:
    #     file_path = "/path/to/your/file.txt"
    #     with open(file_path, "w", encoding="utf-8") as file:
    #         file.write(private_key)

    # Hive 登录，提取 Public 和 Private Key
    logger.info("开始 Hive 登录...")
    run_command_and_print("/root/.aios/aios-cli hive login", wait_for="Authenticated successfully!")

    # if public_key is not None:
    #     logger.info("已配置了key...")
    # else:

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
    # if publicKey is None and public_key != publicKey:
    client.publish("hyperCli", json.dumps(get_info(serverId, "hyperCli", public_key, private_key, key_content)))

    # 7. 执行 hive select-tier 5 命令
    logger.info("执行 hive select-tier 5 命令...")
    run_command_blocking("/root/.aios/aios-cli hive select-tier 5")
    logger.info("select-tier 命令执行完毕。")

    # 8. 执行 hive connect 命令
    logger.info("执行 hive connect 命令...")
    run_command_blocking("/root/.aios/aios-cli hive connect")
    logger.info("connect 命令执行完毕。")
    return public_key

def get_info(server_id, account_type, public_key, private_key, key_content):
    return {
        "serverId": f"{server_id}",
        "accountType": f"{account_type}",
        "publicKey": f"{public_key}",
        "privateKey": f"{private_key}",
        "remarks": f"{key_content}"
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
