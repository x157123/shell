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
from pathlib import Path
from typing import List, Optional

import asyncssh
from loguru import logger

# ──────────────────── 全局配置 ────────────────────
PORT               = 22292                           # SSH 端口
USERNAME           = "root"
PASSWORD           = os.getenv("SSH_PASS", "Mmscm716+")  # 建议改用环境变量
CONNECT_TIMEOUT    = 10                              # TCP 连接超时
LOGIN_TIMEOUT      = 15                              # SSH 握手 + 认证超时
KEEPALIVE_INTERVAL = 30                              # 保活心跳
MAX_RETRY          = 3                               # 每台主机的最大重试次数
CONCURRENCY        = 5

REMOTE_DIR         = "/home/ubuntu/task/tasks"
REMOTE_TASKS_FILE  = f"{REMOTE_DIR}/tasks.txt"

# ──────────────────── 工具函数 ────────────────────
def read_data_list_file(path: str | Path, *, create_if_missing: bool = True) -> List[str]:
    """读取文件，剔除空行并返回列表。"""
    path = Path(path)
    if create_if_missing and not path.exists():
        path.touch()
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def append_data_to_file(path: str | Path, data: str) -> None:
    """向本地文件追加一行数据。"""
    path = Path(path)
    if not path.exists():
        path.touch()
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{data}\n")

# ──────────────────── 远程写入 ────────────────────
async def _append_param_via_sftp(conn: asyncssh.SSHClientConnection, param: str) -> None:
    """
    通过 SFTP 以追加方式把 param 写到远端 tasks.txt。
    修复点：
      - 使用 bytes 写入（asyncssh 的 SFTP 不支持 encoding=）
      - 确保目录存在
      - 文件不存在时先创建空文件
      - 写入成功后 chown 给 ubuntu:ubuntu
    """
    # 确保目录存在
    await conn.run(f"mkdir -p {shlex.quote(REMOTE_DIR)}", check=False)

    sftp = await conn.start_sftp_client()
    try:
        # 若文件不存在则先创建空文件
        try:
            await sftp.stat(REMOTE_TASKS_FILE)
        except FileNotFoundError:
            f = await sftp.open(REMOTE_TASKS_FILE, pflags=asyncssh.sftp.SSH_FXF_WRITE | asyncssh.sftp.SSH_FXF_CREAT)
            try:
                await f.write(b"")
            finally:
                await f.close()

        # 以追加模式打开并写 bytes
        f = await sftp.open(
            REMOTE_TASKS_FILE,
            pflags=asyncssh.sftp.SSH_FXF_APPEND | asyncssh.sftp.SSH_FXF_WRITE
        )
        try:
            data = (param.rstrip("\n") + "\n").encode("utf-8")
            await f.write(data)
        finally:
            await f.close()

        # 再确保属主（避免首次由 root 创建后权限不对）
        await conn.run(f"chown ubuntu:ubuntu {shlex.quote(REMOTE_TASKS_FILE)}", check=False)

    finally:
        # 关闭 SFTP 客户端
        await sftp.exit()

# ──────────────────── 核心逻辑 ────────────────────
async def run_remote_script(host: str, param: Optional[str], sem: asyncio.Semaphore) -> None:
    """连接远端主机，把 param 追加进 tasks.txt（若有），成功才记 ex_end.txt。"""
    async with sem:
        for attempt in range(1, MAX_RETRY + 1):
            try:
                logger.info(f"[{host}] 第 {attempt}/{MAX_RETRY} 次尝试连接…")
                async with asyncssh.connect(
                        host,
                        port=PORT,
                        username=USERNAME,
                        password=PASSWORD,
                        known_hosts=None,                  # 生产环境建议做指纹校验
                        connect_timeout=CONNECT_TIMEOUT,
                        login_timeout=LOGIN_TIMEOUT,
                        keepalive_interval=KEEPALIVE_INTERVAL,
                        compression_algs=["none"],
                        encryption_algs=["aes128-ctr"],
                ) as conn:
                    # 有参数则写；没有参数也算成功（仅打点）
                    if param:
                        try:
                            await _append_param_via_sftp(conn, param)
                            logger.info(f"[{host}] 已将参数追加到 {REMOTE_TASKS_FILE}")
                        except Exception as e:
                            # 写入失败 -> 触发重试
                            raise RuntimeError(f"追加参数到远程 tasks.txt 失败：{e}") from e

                    # 只有连接+写入都成功才计入完成
                    append_data_to_file("ex_end.txt", host)
                    logger.success(f"[{host}] 完成")
                    break  # 成功，跳出重试循环

            except asyncio.TimeoutError:
                if attempt == MAX_RETRY:
                    logger.error(f"[{host}] 连接超时，已重试 {MAX_RETRY} 次，放弃")
                else:
                    wait = 2 ** attempt
                    logger.warning(f"[{host}] 连接超时，{wait}s 后重试")
                    await asyncio.sleep(wait)

            except (asyncssh.Error, OSError, RuntimeError) as exc:
                # RuntimeError 可能来自写入失败；asyncssh.Error 来自 SSH/SFTP 层
                if attempt == MAX_RETRY:
                    logger.error(f"[{host}] 发生异常且到达最大重试：{exc!s}")
                else:
                    wait = 2 ** attempt
                    logger.warning(f"[{host}] 异常：{exc!s}，{wait}s 后重试")
                    await asyncio.sleep(wait)

async def main() -> None:
    sem = asyncio.Semaphore(CONCURRENCY)

    # 输入文件：每行格式 host||||param   （param 可省略）
    nodes = read_data_list_file("append_tasks.txt")

    tasks: list[asyncio.Task] = []
    for record in nodes:
        # 健壮性：跳过空行（上游已过滤），解析异常保护
        try:
            host, *rest = record.split("||||")
            host = host.strip()
            if not host:
                logger.warning(f"行解析失败（空 host），跳过：{record!r}")
                continue
            param = rest[0].strip() if rest else None
        except Exception:
            logger.warning(f"行解析异常，跳过：{record!r}")
            continue

        tasks.append(asyncio.create_task(run_remote_script(host, param or None, sem)))

    if tasks:
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
