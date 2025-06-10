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
import time
from loguru import logger
import requests
from pathlib import Path


def run(cmd: str):
    """封装 subprocess.run，用于执行 shell 命令并失败退出"""
    logger.info(f"[INFO] Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        logger.info(f"[ERROR] Command failed ({result.returncode}): {cmd}", file=sys.stderr)
        sys.exit(result.returncode)


def issue_with_retry(domain: str, acme_path: str, retry_interval: int = 5):
    """
    用 standalone 模式申请证书，失败时每隔 retry_interval 秒重试
    并流式打印 acme.sh 输出。
    """
    cmd = f"{acme_path} --issue -d {domain} --standalone"
    while True:
        logger.info(f"[INFO] 尝试签发证书：{cmd}")
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            logger.info(line, end="")
        ret = proc.wait()
        if ret == 0:
            logger.info("[INFO] 证书签发成功。")
            break
        else:
            logger.info(f"[WARN] 证书签发失败 (退出码 {ret})，{retry_interval} 秒后重试...", file=sys.stderr)
            run(f"{acme_path} --set-default-ca --server letsencrypt")
            time.sleep(retry_interval)


def in_node():

    # 配置项：根据需要修改
    EMAIL = f"xiaomin{random.randint(1000, 5000)}@126.com"
    X_RAY_DIR = "/etc/xray"
    HOME = os.path.expanduser("~")
    ACME = os.path.join(HOME, ".acme.sh", "acme.sh")
    CERT_DIR = os.path.join(HOME, ".acme.sh", f"{domain}_ecc")

    # 1. 安装依赖
    run("apt update")
    run("apt install -y curl socat")

    # 定义脚本路径和参数列表
    script_path = './xray_vmess.sh'
    # servers = ['10.3.1.1', '10.3.2.2', '10.3.3.3']
    script_url = 'https://www.15712345.xyz/shell/vpn/xray_vmess.sh'
    # 1. 如果已存在旧脚本，先删除
    _script_path = Path('./xray_vmess.sh')
    if _script_path.exists():
        logger.info(f"{_script_path} 已存在，先删除旧文件")
        _script_path.unlink()
    resp = requests.get(script_url)
    resp.raise_for_status()  # 如果下载失败会抛异常
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(resp.text)

    # 2. 安装 acme.sh（如果已安装则跳过）
    if not os.path.isfile(ACME):
        run("curl https://get.acme.sh | sh")
    else:
        logger.info(f"[INFO] acme.sh 已存在：{ACME}")

    private_key = os.path.join(X_RAY_DIR, 'private.key')

    if os.path.exists(private_key):
        logger.info('跳过安装证书')
    else:
        # 3. 注册账户
        run(f"{ACME} --register-account -m {EMAIL}")

        logger.info(f'领取证书{domain}')
        
        # 4. 签发证书，失败时重试
        issue_with_retry(domain, ACME, retry_interval=5)

        # 5. 安装证书到 Xray 目录
        os.makedirs(X_RAY_DIR, exist_ok=True)
        run(
            f"{ACME} --installcert -d {domain} "
            f"--key-file      {X_RAY_DIR}/private.key "
            f"--fullchain-file {X_RAY_DIR}/cert.crt"
        )

    # 6. 打印安装结果
    logger.info("\n====== 证书安装完成 ======")
    logger.info(f"私钥路径：{X_RAY_DIR}/private.key")
    logger.info(f"证书路径：{X_RAY_DIR}/cert.crt")
    logger.info(f"原始证书：{CERT_DIR}/{domain}.cer")
    logger.info(f"中间 CA  ：{CERT_DIR}/ca.cer")
    logger.info(f"完整链  ：{CERT_DIR}/fullchain.cer")
    logger.info("===========================")

    # 确保脚本可执行
    subprocess.run(['chmod', '+x', script_path], check=True)

    # 执行脚本并捕获输出
    subprocess.run([script_path] + nodes, capture_output=True, text=True)


def out_node():

    # 1. 安装依赖
    run("apt update")
    run("apt install -y curl socat")

    # 定义脚本路径和参数列表
    script_path = './xray_socks.sh'
    # servers = ['10.3.1.1', '10.3.2.2', '10.3.3.3']
    script_url = 'https://www.15712345.xyz/shell/vpn/xray_socks.sh'
    # 1. 如果已存在旧脚本，先删除
    _script_path = Path('./xray_socks.sh')
    if _script_path.exists():
        logger.info(f"{_script_path} 已存在，先删除旧文件")
        _script_path.unlink()
    resp = requests.get(script_url)
    resp.raise_for_status()  # 如果下载失败会抛异常
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(resp.text)

    # 确保脚本可执行
    subprocess.run(['chmod', '+x', script_path], check=True)

    # 执行脚本并捕获输出
    subprocess.run([script_path], capture_output=True, text=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--param", type=str, help="参数")
    args = parser.parse_args()

    # 拆分
    s = args.param
    if s is not None:
        domain, *nodes = s.split("|")

        # 输出验证
        print("domain =", domain)
        print("nodes  =", nodes)

        # 确保以 root 身份运行
        if os.geteuid() != 0:
            logger.info("请以 root 身份运行此脚本。", file=sys.stderr)
            sys.exit(1)
        in_node()
    else:
        out_node()

