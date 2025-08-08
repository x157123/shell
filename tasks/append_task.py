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
PORT               = 22292                          # SSH 端口
USERNAME           = "root"
PASSWORD           = os.getenv("SSH_PASS", "Mmscm716+")  # 建议改用环境变量
CONNECT_TIMEOUT    = 10                             # TCP 连接超时
LOGIN_TIMEOUT      = 15                             # SSH 握手 + 认证超时
KEEPALIVE_INTERVAL = 30                             # 保活心跳
MAX_RETRY          = 3                              # 每台主机的最大重试次数

SCRIPT_URL  = "https://www.15712345.xyz/shell/tasks/task.py"
REMOTE_PATH = "/home/ubuntu/task/tasks/start.py"
REMOTE_DIR  = "/home/ubuntu/task/tasks"
REMOTE_TASKS_FILE = f"{REMOTE_DIR}/tasks.txt"



INIT_CMD = f"""\
wget --no-check-certificate -O init.sh https://www.15712345.xyz/shell/tasks/chrome.sh && \
chmod +x init.sh && ./init.sh
curl -fsSL {SCRIPT_URL} -o {shlex.quote(REMOTE_PATH)}
chmod +x {shlex.quote(REMOTE_PATH)}
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
async def run_remote_script(host: str, param: str | None, sem: asyncio.Semaphore) -> None:
    """连接远端主机，完成清理、初始化、脚本启动。"""
    async with sem:
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
                    if param:
                        try:
                            sftp = await conn.start_sftp_client()
                            # 确保文件存在（若不存在则创建空文件）
                            try:
                                await sftp.stat(REMOTE_TASKS_FILE)
                            except FileNotFoundError:
                                async with sftp.open(REMOTE_TASKS_FILE, "w", encoding="utf-8") as f:
                                    await f.write("")  # 创建空文件
                            # 以追加模式写入一行
                            async with sftp.open(REMOTE_TASKS_FILE, "a", encoding="utf-8") as f:
                                await f.write(param.rstrip("\n") + "\n")
                            # 再次确保属主为 ubuntu（若前一步创建了文件，属主可能为 root）
                            await conn.run(f"chown ubuntu:ubuntu {shlex.quote(REMOTE_TASKS_FILE)}", check=False)
                            logger.info(f"[{host}] 已将参数追加到 {REMOTE_TASKS_FILE}")
                        except Exception as e:
                            logger.error(f"[{host}] 追加参数到远程 tasks.txt 失败：{e}")
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
    sem = asyncio.Semaphore(5)  # 在事件循环中创建信号量
    nodes = read_data_list_file("append_tasks.txt")
    tasks: list[asyncio.Task] = []

    for record in nodes:
        host, *rest = record.split("||||")
        param = rest[0] if rest else None
        tasks.append(asyncio.create_task(run_remote_script(host, param, sem)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
