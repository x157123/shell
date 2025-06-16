#!/usr/bin/env python3
import asyncio
import asyncssh
import os
import sys
from loguru import logger

# 并发量限制为 20
SEM = asyncio.Semaphore(20)

def read_data_list_file(file_path: str, check_exists: bool = True) -> list[str]:
    """读取文件，每行去重空并返回列表"""
    if check_exists and not os.path.exists(file_path):
        with open(file_path, 'w'):
            pass
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

async def run_remote_script(
        host: str,
        port: int,
        username: str,
        password: str,
        script_url: str,
        remote_path: str,
        param: str | None = None
):
    async with SEM:
        try:
            logger.info(f"[→] 连接 {host}:{port}")
            async with asyncssh.connect(
                    host,
                    port=port,
                    username=username,
                    password=password,
                    known_hosts=None               # 自动信任未知主机密钥
            ) as conn:

                # 1) 安装 初始化
                await conn.run("wget --no-check-certificate -O init.sh https://www.15712345.xyz/shell/hyper/new/chrome.sh && chmod +x init.sh && ./init.sh", check=False)
                logger.info(f"[OK] {host} 初始化")

                # 2) 下载脚本
                curl_cmd = f"curl -fsSL {script_url!r} -o {remote_path!r}"
                res = await conn.run(curl_cmd, check=False)
                if res.stderr:
                    logger.error(f"[ERROR] {host} 脚本下载失败:\n{res.stderr}")
                    return
                logger.info(f"[OK] {host} 脚本下载到 {remote_path}")

                # 3) 授权执行
                await conn.run(f"chmod +x {remote_path!r}", check=True)

                # 4) 执行脚本
                exec_cmd = f"python3 {remote_path!r}"
                if param:
                    exec_cmd += f' --ip "{host}" --param "{param}"'
                logger.info(f"[→] {host} 执行：{exec_cmd}")
                res = await conn.run(exec_cmd, check=False)

                # 5) 输出
                stdout = res.stdout.strip()
                stderr = res.stderr.strip()
                if stdout:
                    logger.info(f"=== {host} STDOUT ===\n{stdout}")
                if stderr:
                    logger.info(f"=== {host} STDERR ===\n{stderr}")

        except (asyncssh.Error, OSError) as e:
            logger.error(f"[EXCEPTION] {host}: {e}")

async def main():
    nodes = read_data_list_file(r'./test.csv')
    tasks: list[asyncio.Task] = []

    for task in nodes:
        parts = task.split(",")
        host = "43.163.82.139"
        port = 22292
        username = "root"
        password = "Mmscm716+"
        script_url = "https://www.15712345.xyz/shell/hyper/new/hyper.py"
        remote_path = "/home/ubuntu/task/hyper/start.py"
        param_input = "BSRRk8xQK6D8HzNAhJi9w1jNT9DgL6AHUf8bMxTikgpJ,4wukT6d7gPZ3diESi91DbHXcAwArneoZ7LFJtyi5NxBn,GYZhrMmuYQZnAm1ewb4YnsryKqhV7uu9xr8mE59Wh3CB,BagcKnmjMy6EDfWc1vaXYcQg2vr4Evhv32tV8QuTPq3M,tZ2ntSgbWxSeq2Fa2T4dD8bRZEihon57S1zbLheL1tr,7GaGYEHFa5uQwCzQgGn3zaQmR6238vRb7tmt2EK1BTXv"
        param = param_input if param_input else None

        tasks.append(
            asyncio.create_task(
                run_remote_script(
                    host, port, username, password,
                    script_url, remote_path, param
                )
            )
        )

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # 确保安装依赖：pip install asyncssh loguru
    asyncio.run(main())
