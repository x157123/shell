#!/usr/bin/env python3
"""
批量连接服务器，初始化环境并启动脚本（异步版）

依赖：
    pip install asyncssh loguru
"""

from __future__ import annotations

import asyncio
import os
import shlex
import time
from pathlib import Path
from typing import List

import asyncssh
from loguru import logger

# ──────────────────── 全局配置 ────────────────────
SEM                = asyncio.Semaphore(4)          # 最大并发数
PORT               = 22292                          # SSH 端口
USERNAME           = "root"
PASSWORD           = os.getenv("SSH_PASS", "Mmscm716+")  # 建议改用环境变量
CONNECT_TIMEOUT    = 10                             # TCP 连接超时
LOGIN_TIMEOUT      = 15                             # SSH 握手 + 认证超时
KEEPALIVE_INTERVAL = 30                             # 保活心跳
MAX_RETRY          = 3                              # 每台主机的最大重试次数

SCRIPT_URL  = "https://www.15712345.xyz/shell/hyper/new/hyper.py"
REMOTE_PATH = "/home/ubuntu/task/hyper/start.py"


NEXUS_SCRIPT_URL  = "https://www.15712345.xyz/shell/nexus_25_07_08/task.py"
NEXUS_REMOTE_PATH = "/home/ubuntu/task/nexus/start.py"

CLEANUP_CMD = f"""\
pkill -f {shlex.quote(REMOTE_PATH)} || true
pkill -f {shlex.quote(NEXUS_REMOTE_PATH)} || true
sleep 2
rm -f ~/.config/google-chrome/SingletonLock
rm -rf ~/.config/google-chrome/SingletonSocket
mkdir -p /home/ubuntu/task/hyper
mkdir -p /home/ubuntu/task/nexus
"""

INIT_CMD = f"""\
wget --no-check-certificate -O init.sh https://www.15712345.xyz/shell/hyper/new/chrome.sh && \
chmod +x init.sh && ./init.sh
curl -fsSL {SCRIPT_URL} -o {shlex.quote(REMOTE_PATH)}
chmod +x {shlex.quote(REMOTE_PATH)}
curl -fsSL {NEXUS_SCRIPT_URL} -o {shlex.quote(NEXUS_REMOTE_PATH)}
chmod +x {shlex.quote(NEXUS_REMOTE_PATH)}
"""

# ──────────────────── 工具函数 ────────────────────
def read_data_list_file(path: str | Path, *, create_if_missing: bool = True) -> List[str]:
    """读取文件，剔除空行并返回列表。"""
    path = Path(path)
    if create_if_missing and not path.exists():
        path.touch()
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_data_to_file(path: str | Path, data: str) -> None:
    """向文件追加一行数据。"""
    path = Path(path)
    # 确保文件存在
    if not path.exists():
        path.touch()
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{data}\n")


# ──────────────────── 核心逻辑 ────────────────────
async def run_remote_script(host: str, param: str | None, nexus_param: str | None) -> None:
    """连接远端主机，完成清理、初始化、脚本启动。"""
    async with SEM:
        for attempt in range(1, MAX_RETRY + 1):
            try:
                logger.info(f"[{host}] 第 {attempt}/{MAX_RETRY} 次尝试连接…")
                async with asyncssh.connect(
                        host,
                        port=PORT,
                        username=USERNAME,
                        password=PASSWORD,
                        known_hosts=None,                 # 生产环境请改为指纹校验
                        connect_timeout=CONNECT_TIMEOUT,
                        login_timeout=LOGIN_TIMEOUT,
                        keepalive_interval=KEEPALIVE_INTERVAL,
                        compression_algs=["none"],
                        encryption_algs=["aes128-ctr"],
                ) as conn:
                    # 1) 清理环境
                    await conn.run(CLEANUP_CMD, check=False)
                    logger.info(f"[{host}] 环境清理完成")

                    # 2) 下载并安装脚本
                    res = await conn.run(INIT_CMD, check=False)
                    if res.exit_status != 0:
                        raise RuntimeError(f"初始化失败: {res.stderr.strip()}")
                    logger.info(f"[{host}] 初始化脚本完成")

                    # 3) 调整权限并执行
                    await conn.run("chown -R ubuntu:ubuntu /home/ubuntu/task/hyper", check=False)
                    await conn.run("chown -R ubuntu:ubuntu /home/ubuntu/task/nexus", check=False)
                    await conn.run("pkill -9 chrome", check=False)

                    exec_nexus_cmd = (
                        f"sudo -u ubuntu -i nohup python3 {shlex.quote(NEXUS_REMOTE_PATH)}"
                    )

                    if nexus_param:
                        exec_nexus_cmd += (
                            f" --ip {shlex.quote(host)} --param {shlex.quote(nexus_param)}"
                        )
                    exec_nexus_cmd += " > /home/ubuntu/task/nexus/out.log 2>&1 &"
                    await conn.run(exec_nexus_cmd, check=False)

                    time.sleep(1200)
                    await conn.run(f"pkill -f {shlex.quote(NEXUS_REMOTE_PATH)}", check=False)
                    await conn.run("pkill -9 chrome", check=False)

                    exec_cmd = (
                        f"sudo -u ubuntu -i nohup python3 {shlex.quote(REMOTE_PATH)}"
                    )

                    if param:
                        exec_cmd += (
                            f" --ip {shlex.quote(host)} --param {shlex.quote(param)}"
                        )
                    exec_cmd += " > /home/ubuntu/task/hyper/out.log 2>&1 &"

                    await conn.run(exec_cmd, check=False)
                    logger.success(f"[{host}] 脚本已启动")
                    append_data_to_file("ex_end.txt", host)
                    break  # 成功，跳出重试循环

            except asyncio.TimeoutError:
                if attempt == MAX_RETRY:
                    logger.error(f"[{host}] 连接超时，已重试 {MAX_RETRY} 次，放弃")
                else:
                    wait = 2 ** attempt
                    logger.warning(f"[{host}] 连接超时，{wait}s 后重试")
                    await asyncio.sleep(wait)

            except (asyncssh.Error, OSError, RuntimeError) as exc:
                logger.error(f"[{host}] 发生异常: {exc!s}")
                break


async def main() -> None:
    nodes       = read_data_list_file("task.txt")
    # finished    = set(read_data_list_file("ex_end.txt"))
    tasks: list[asyncio.Task] = []

    for record in nodes:
        host, *rest = record.split("|||")
        # if host in finished:
        #     logger.info(f"[{host}] 已完成，跳过")
        #     continue
        param = rest[0] if rest else None
        nexus_param = rest[1] if rest else None
        tasks.append(asyncio.create_task(run_remote_script(host, param, nexus_param)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    while True:
        asyncio.run(main())
