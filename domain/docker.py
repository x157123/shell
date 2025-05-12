#!/usr/bin/env python3
"""
自动化申请并安装 acme.sh 证书到 Xray 目录的脚本，失败时每隔 5 秒重试
依赖：curl, socat, acme.sh
用法：以 root 身份运行，本脚本将在 /etc/xray 下生成 private.key 和 cert.crt
"""
import argparse
import os
import random
import subprocess
import sys
import json
import time
from loguru import logger
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


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


def run(cmd: str):
    """封装 subprocess.run，用于执行 shell 命令并失败退出"""
    print(f"[INFO] Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[ERROR] Command failed ({result.returncode}): {cmd}", file=sys.stderr)
        sys.exit(result.returncode)


def issue_with_retry(domain: str, acme_path: str, retry_interval: int = 5):
    """
    用 standalone 模式申请证书，失败时每隔 retry_interval 秒重试
    并流式打印 acme.sh 输出。
    """
    cmd = f"{acme_path} --issue -d {domain} --standalone"
    while True:
        print(f"[INFO] 尝试签发证书：{cmd}")
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")
        ret = proc.wait()
        if ret == 0:
            print("[INFO] 证书签发成功。")
            break
        else:
            print(f"[WARN] 证书签发失败 (退出码 {ret})，{retry_interval} 秒后重试...", file=sys.stderr)
            time.sleep(retry_interval)


def generate_config(socks_port, vmess_port, x_ray_dir):
    cfg = {
        "inbounds": [
            {
                "port": socks_port,
                "listen": "0.0.0.0",
                "protocol": "socks",
                "settings": {"auth": "password", "udp": True,
                             "accounts": [{"user": "userb", "pass": "test"}]}
            },
            {
                "port": vmess_port,
                "listen": "0.0.0.0",
                "protocol": "vmess",
                "settings": {"clients": [{"id": "05dc4fd1-9348-48a2-8040-9d95220638cd", "alterId": 0, "level": 1}]},
                "streamSettings": {
                    "network": "ws",
                    "security": "tls",
                    "tlsSettings": {"certificates": [{
                        "certificateFile": "/etc/xray/cert.crt",
                        "keyFile": "/etc/xray/private.key"
                    }]},
                    "wsSettings": {"path": "/05dc4fd1-9348-48a2-8040-9d95220638cd", "headers": {"Host": domain}}
                }
            }
        ],
        "outbounds": [{"protocol": "freedom", "settings": {}}]
    }
    os.makedirs(x_ray_dir, exist_ok=True)
    config_path = os.path.join(x_ray_dir, "config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 生成配置文件：{config_path}")


def main():
    # 配置项：根据需要修改
    EMAIL = f"x1{random.randint(10000, 50000)}@126.com"
    X_RAY_DIR = "/etc/xray"
    HOME = os.path.expanduser("~")
    ACME = os.path.join(HOME, ".acme.sh", "acme.sh")
    CERT_DIR = os.path.join(HOME, ".acme.sh", f"{domain}_ecc")

    # 1. 安装依赖
    run("apk update")
    run("apk add --no-cache curl socat")

    # 2. 安装 acme.sh（如果已安装则跳过）
    if not os.path.isfile(ACME):
        run("curl https://get.acme.sh | sh")
    else:
        print(f"[INFO] acme.sh 已存在：{ACME}")

    # 3. 注册账户
    run(f"{ACME} --register-account -m {EMAIL}")

    # 4. 签发证书，失败时重试
    issue_with_retry(domain, ACME, retry_interval=5)

    # 5. 安装证书到 Xray 目录
    os.makedirs(X_RAY_DIR, exist_ok=True)
    run(
        f"{ACME} --installcert -d {domain} "
        f"--key-file      {X_RAY_DIR}/private.key "
        f"--fullchain-file {X_RAY_DIR}/cert.crt"
    )

    generate_config(20000, 22291, X_RAY_DIR)

    # 6. 打印安装结果
    print("\n====== 证书安装完成 ======")
    print(f"私钥路径：{X_RAY_DIR}/private.key")
    print(f"证书路径：{X_RAY_DIR}/cert.crt")
    print(f"原始证书：{CERT_DIR}/{domain}.cer")
    print(f"中间 CA  ：{CERT_DIR}/ca.cer")
    print(f"完整链  ：{CERT_DIR}/fullchain.cer")
    print("===========================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    parser.add_argument("--chromePort", type=str, help="浏览器端口", required=True)
    args = parser.parse_args()

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + args.appId + '_user.json')
    # 解密并发送解密结果
    domain = decrypt_aes_ecb(args.decryptKey, encrypted_data_base64, 'remarks')
    # domain = "test1.15712345.xyz"
    # 确保以 root 身份运行
    if os.geteuid() != 0:
        print("请以 root 身份运行此脚本。", file=sys.stderr)
        sys.exit(1)
    main()
    # generate_config(20000, 22291, "/etc/xray")

