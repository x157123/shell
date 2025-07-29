#!/usr/bin/env python3
import asyncio
import time

import asyncssh
import os
import sys
from loguru import logger

# 并发量限制为 20
SEM = asyncio.Semaphore(40)

def read_data_list_file(file_path: str, check_exists: bool = True) -> list[str]:
    """读取文件，每行去重空并返回列表"""
    if check_exists and not os.path.exists(file_path):
        with open(file_path, 'w'):
            pass
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

# 文件追加
def append_date_to_file(file_path, data_str):
    with open(file_path, 'a') as file:
        file.write(data_str + '\n')




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
                    known_hosts=None,              # 自动信任未知主机密钥
                    keepalive_interval=30,         # 保持连接活跃
                    connect_timeout=10,            # 连接超时
                    compression_algs=['none'],     # 禁用压缩加速
                    encryption_algs=['aes128-ctr'] # 使用更快的加密算法
            ) as conn:
                # 批量执行清理命令
                cleanup_cmd = f"""
pkill -f {remote_path} || true
sleep 2
pkill -9 chrome || true
rm -f ~/.config/google-chrome/SingletonLock
rm -rf ~/.config/google-chrome/SingletonSocket
mkdir -p /home/ubuntu/task/hyper
"""
                await conn.run(cleanup_cmd, check=False)
                logger.info(f"[OK] {host} 清理完成")

                # 批量执行初始化和下载命令
                init_cmd = f"""
wget --no-check-certificate -O init.sh https://www.15712345.xyz/shell/hyper/new/chrome.sh && chmod +x init.sh && ./init.sh
curl -fsSL {script_url!r} -o {remote_path!r}
chmod +x {remote_path!r}
"""
                res = await conn.run(init_cmd, check=False)
                if res.stderr and ("curl" in res.stderr.lower() or "wget" in res.stderr.lower()):
                    logger.error(f"[ERROR] {host} 初始化或下载失败:\n{res.stderr}")
                    return
                logger.info(f"[OK] {host} 初始化和脚本下载完成")

                # 4) 执行脚本
                await conn.run(f"chown -R ubuntu:ubuntu /home/ubuntu/task/hyper", check=False)
                exec_cmd = f"sudo -u ubuntu -i nohup python3 {remote_path!r}"
                if param:
                    exec_cmd += f' --ip "{host}" --param "{param}" > /home/ubuntu/task/hyper/out.log 2>&1 &'
                logger.info(f"[→] {host} 执行：{exec_cmd}")
                res = await conn.run(exec_cmd, check=False)

                # 5) 输出
                stdout = res.stdout.strip()
                stderr = res.stderr.strip()
                if stdout:
                    logger.info(f"=== {host} STDOUT ===\n{stdout}")
                if stderr:
                    logger.info(f"=== {host} STDERR ===\n{stderr}")
                append_date_to_file("./ex_end.txt", host)
        except (asyncssh.Error, OSError) as e:
            logger.error(f"[EXCEPTION] {host}: {e}")

async def main():
    nodes = read_data_list_file(r'./test.txt')
    tasks: list[asyncio.Task] = []

    ex_list = read_data_list_file("./ex_end.txt", check_exists=True)

    for task in nodes:
        parts = task.split("|||")
        host = parts[0]
        if len(ex_list) > 0 and host in ex_list:
            logger.info(f'跳过服务器：{task}')
            continue
        port = 22292
        username = "root"
        password = "Mmscm716+"
        script_url = "https://www.15712345.xyz/shell/hyper/new/hyper.py"
        remote_path = "/home/ubuntu/task/hyper/start.py"
        param_input = parts[1]
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
