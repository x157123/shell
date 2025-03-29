import csv
import time
import json
import zlib
import base64
import subprocess
import base58
import argparse
from Crypto.Cipher import AES
from loguru import logger
from Crypto.Util.Padding import unpad
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


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



def compress_data(data):
    # 校验字符串是否正常
    set_pem_data(data)
    # 将字典转换为 JSON 字符串
    json_str = json.dumps(data)
    # 压缩 JSON 字符串（生成 bytes）
    compressed = zlib.compress(json_str.encode('utf-8'))
    # 将压缩后的 bytes 编码成 base64 字符串，便于传输和保存
    compressed_b64 = base64.b64encode(compressed).decode('utf-8')
    return compressed_b64


def set_pem_data(data):
    # 首先判断 data 是否有 remarks 属性，并且 remarks 是字符串类型
    if 'remarks' in data and isinstance(data['remarks'], str) and data['remarks'].strip():
        # 如果存在且去除空白后非空字符串，就执行相应逻辑
        # print("remarks 属性存在且有效:", data['remarks'])
        print("remarks 属性存在且有效")
        # 这里可以加入其他的处理逻辑
    else:
        print("remarks 属性不存在重新生成")

        # 解码Base58私钥为字节
        private_key_bytes = base58.b58decode(data['privateKey'])

        # 从私钥字节创建Ed25519私钥对象
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)

        # 从私钥生成公钥
        public_key = private_key.public_key()

        # 序列化为PKCS8格式的PEM文件（包含私钥信息）
        pem_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # 序列化为X.509格式的PEM文件（包含公钥信息）
        pem_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # 去掉PEM头尾并提取Base64编码的内容
        private_key_base64 = pem_private_key.decode('ascii').strip().split('\n')[1:-1]  # Remove BEGIN and END lines
        public_key_base64 = pem_public_key.decode('ascii').strip().split('\n')[1:-1]  # Remove BEGIN and END lines


        # 输出合并后的Base64结果
        private_str = ''.join(private_key_base64)
        public_str = ''.join(public_key_base64)


        output_private_str = "MFECAQEw" + private_str[8:]
        output_public_str = "gS" + public_str[14:]
        begin_str = "-----BEGIN PRIVATE KEY-----"
        end_str = "-----END PRIVATE KEY-----"

        public_key_pem = begin_str + "\n" + output_private_str + "\n" + output_public_str + "\n" + end_str

        data['remarks'] = public_key_pem


# 函数：启动容器应用
def run_shell_script(data, ip_suffix):
    # 定义脚本路径
    script_path = '/opt/runNodePort.sh'

    # 调用 shell 脚本并传递参数
    try:
        result = subprocess.run([script_path, data, str(ip_suffix)], check=True, capture_output=True, text=True)

        # 获取脚本的输出
        print("Shell script output:")
        print(result.stdout)

        # 获取脚本的错误输出（如果有）
        if result.stderr:
            print("Shell script error output:")
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running the script: {e}")
        print(f"Return code: {e.returncode}")
        print(f"Error output: {e.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    parser.add_argument("--chromePort", type=str, help="浏览器端口", required=True)
    all_args = parser.parse_args()
    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + all_args.appId + '_user.json')
    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(all_args.decryptKey, encrypted_data_base64, 'hyperDocker')

    if len(public_key_tmp) > 0:
        start_id = 20000  # 设置起始ID
        for index, item in enumerate(public_key_tmp):
            time.sleep(200)
            item['id'] = start_id + index  # 将ID设置为序号，从20000开始
            data = compress_data(item)
            run_shell_script(data, item['id'])