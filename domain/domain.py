import argparse
from loguru import logger
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import json
import subprocess




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
            if item.get('accountType') == 'domain':
                return item.get(key)

        # 没有找到匹配的记录，返回 None
        return None

    except Exception as e:
        raise ValueError(f"解密失败: {e}")




def main(appId, decryptKey):

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + appId + '_user.json')
    # 解密并发送解密结果
    domain = decrypt_aes_ecb(decryptKey, encrypted_data_base64, 'remarks')
    if domain is not None:
        logger.info(domain)
        # 1) 执行 bash <(wget -qO- -o- https://git.io/v2ray.sh)
        #   由于用到了 <(...) 进程替换，我们需要指定 shell='True' 并指定 executable='/bin/bash'
        subprocess.run("bash <(wget -qO- -o- https://git.io/v2ray.sh)", shell=True, executable='/bin/bash')

        # 2) v2ray del
        subprocess.run("v2ray del", shell=True)

        # 3) v2ray add ws \"{dns}\" 8d653735-cd42-4e35-b5e7-9d3724009ef0
        subprocess.run(f'v2ray add ws {domain} 8d653735-cd42-4e35-b5e7-9d3724009ef0', shell=True)

        # 4) v2ray change ws port 22291
        subprocess.run("v2ray change ws port 22291", shell=True)


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
    main(args.appId, args.decryptKey)
