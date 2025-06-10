#!/usr/bin/env python3
import paramiko
import sys
import os


def run_remote_script(
        host: str,
        port: int,
        username: str,
        password: str,
        script_url: str,
        remote_path: str,
        param: str | None = None
):
    # 1) 建立 SSH 连接
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, port=port, username=username, password=password)

    # 2) 在远端用 curl 抓取脚本
    curl_cmd = f"curl -fsSL {script_url!r} -o {remote_path!r}"
    stdin, stdout, stderr = ssh.exec_command(curl_cmd)
    err = stderr.read().decode()
    if err:
        print(f"[ERROR] 下载脚本失败:\n{err}", file=sys.stderr)
        ssh.close()
        sys.exit(1)
    print(f"[OK] 已下载脚本到 {remote_path}")

    # 3) 给脚本可执行权限
    chmod_cmd = f"chmod +x {remote_path!r}"
    ssh.exec_command(chmod_cmd)

    # 4) 执行脚本
    exec_cmd = f"python3 {remote_path!r}"
    if param:
        # 注意在远端 shell 中正确转义
        exec_cmd += f" --param \"{param}\""
    print(f"[→] 执行命令：{exec_cmd}")
    stdin, stdout, stderr = ssh.exec_command(exec_cmd, get_pty=True)

    # 5) 输出结果
    out = stdout.read().decode()
    err = stderr.read().decode()
    print("=== STDOUT ===")
    print(out)
    print("=== STDERR ===")
    print(err)

    ssh.close()


def read_data_list_file(file_path, check_exists=True):
    # 如果需要检查文件是否存在，且文件不存在，则创建文件
    if check_exists and not os.path.exists(file_path):
        with open(file_path, 'w'):  # 创建文件并关闭
            pass  # 创建空文件
    with open(file_path, "r") as file:
        questions = file.readlines()
    # 过滤掉空白行并去除每行末尾的换行符
    return [question.strip() for question in questions if question.strip()]


def main():
    nodes = read_data_list_file(r'C:\Users\liulei\Desktop\service\07\test.csv')

    for task in nodes:
        parts = task.split(",")

        host = parts[3].strip()
        port = 22292
        username = "root"
        password = "Mmscm716+"
        script_url = "https://www.15712345.xyz/shell/vpn/ubuntu_vm_ws_tls_py.py"
        remote_path = "/tmp/remote_script.py"

        param_input = parts[5].strip()
        param = param_input if param_input else None

        run_remote_script(
            host, port, username, password, script_url, remote_path, param
        )


if __name__ == "__main__":
    main()
