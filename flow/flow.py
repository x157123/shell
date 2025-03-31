import argparse
import time

from loguru import logger
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import paho.mqtt.client as mqtt
import json
import subprocess
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.lighthouse.v20200324 import lighthouse_client, models



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

def read_file(file_path):
    """从文件中读取内容并去除多余空白"""
    try:
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

        # 使用 next() 获取第一个匹配项
        first_match = next((item for item in data_list if item.get('accountType') == accountType), None)

        # 返回第一个匹配的结果，如果没有则返回 None
        return first_match
    except Exception as e:
        # 记录错误日志
        logger.error(f"解密失败: {e}")
        return None


def run_command_blocking(cmd, print_output=True):
    """
    执行命令，等待命令执行结束，并返回输出内容。
    """
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if print_output:
        print(result.stdout)
    return result.stdout


def get_flow(mq_client, serverId, appId, public_key, private_key, account, secret_key, num, stat=0):
    try:
        # 实例化一个认证对象，入参需要传入腾讯云账户 SecretId 和 SecretKey，此处还需注意密钥对的保密
        # 代码泄露可能会导致 SecretId 和 SecretKey 泄露，并威胁账号下所有资源的安全性
        # 以下代码示例仅供参考，建议采用更安全的方式来使用密钥
        # 请参见：https://cloud.tencent.com/document/product/1278/85305
        # 密钥可前往官网控制台 https://console.cloud.tencent.com/cam/capi 进行获取
        cred = credential.Credential(public_key, private_key)  #  tx2_sg
        # 实例化一个http选项，可选的，没有特殊需求可以跳过
        httpProfile = HttpProfile()
        httpProfile.endpoint = "lighthouse.tencentcloudapi.com"

        # 实例化一个client选项，可选的，没有特殊需求可以跳过
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        # 实例化要请求产品的client对象,clientProfile是可选的
        client = lighthouse_client.LighthouseClient(cred, secret_key, clientProfile)

        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.DescribeInstancesTrafficPackagesRequest()
        params = {
            "InstanceIds": [account]
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个DescribeInstancesTrafficPackagesResponse的实例，与请求对象对应
        resp = client.DescribeInstancesTrafficPackages(req)
        # 输出json格式的字符串回包
        # logger.info(resp.to_json_string())

        # 解析 JSON 数据
        parsed_data = json.loads(resp.to_json_string())

        # 提取相关信息
        traffic_used = parsed_data["InstanceTrafficPackageSet"][0]["TrafficPackageSet"][0]["TrafficUsed"]
        traffic_package_total = parsed_data["InstanceTrafficPackageSet"][0]["TrafficPackageSet"][0][
            "TrafficPackageTotal"]

        # 计算流量使用百分比
        traffic_usage_percentage = (traffic_used / traffic_package_total) * 100

        logger.info(f"流量使用百分比: {traffic_usage_percentage:.2f}%")
        if traffic_usage_percentage > 90:
            logger.info("流量已超过90%")
            if stat == 1 or stat == 3:
                subprocess.run("v2ray stop", shell=True)
                mq_client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 3, f"流量使用百分比: {traffic_usage_percentage:.2f}%")))
            stat = 0
        else:
            logger.info("流量未超过90%")
            if stat == 0 or stat == 3:
                status_output = run_command_blocking("/root/.aios/aios-cli status")
                if "stopped" in status_output:
                    print("启动流量")
                    subprocess.run("v2ray start", shell=True)
                    stat = 1
        if num >= 60:
            logger.info('推送数据')
            mq_client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 0, f"{traffic_usage_percentage:.2f}")))
        return stat
    except TencentCloudSDKException as err:
        print(err)


def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def main(serverId, appId, decryptKey):
    stat = 3
    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + appId + '_user.json')
    # 解密并发送解密结果
    db = decrypt_aes_ecb(decryptKey, encrypted_data_base64, 'flow_examine')

    if db is None:
        logger.info(f"未读取到相关信息")
        return
    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()
    num = 60  # 五小时推送一次，5分钟检查一次
    while True:
        # public_key, private_key, account, secret_key
        try:
            stat = get_flow(client, serverId, appId, db['publicKey'], db['privateKey'], db['account'], db['secretKey'], num, stat)
        except Exception as e:
            client.publish("appInfo", json.dumps(get_app_info(serverId, appId, 3, '检查过程中出现异常: ' + str(e))))
        time.sleep(300)
        num += 1
        if num > 60:
            num = 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    parser.add_argument("--chromePort", type=str, help="浏览器端口", required=True)
    args = parser.parse_args()

    # 启动网络循环
    main(args.serverId, args.appId, args.decryptKey)
