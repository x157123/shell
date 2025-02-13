import subprocess
import time
import threading
import re

def run_command_blocking(cmd, print_output=True):
    """
    执行命令，等待命令执行结束，并返回输出内容。
    """
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if print_output:
        print(result.stdout)
    return result.stdout

def run_command_and_print(cmd, wait_for=None, print_output=True):
    """
    实时执行命令，打印输出。如果指定了 wait_for，当检测到该关键字时返回已收集的输出内容。
    """
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    collected_output = ""
    while True:
        line = process.stdout.readline()
        if line:
            collected_output += line
            if print_output:
                print(line.strip())
            if wait_for and wait_for in line:
                break
        if not line and process.poll() is not None:
            break
    process.wait()  # 确保进程退出
    return collected_output

def fetch_points():
    """
    定时任务：每隔 10 分钟执行一次 hive points 命令，并打印积分信息。
    """
    while True:
        print("\n===== 积分查询输出 =====")
        run_command_blocking("/root/.aios/aios-cli hive points")
        time.sleep(600)  # 600 秒 = 10 分钟

def main():
    # 1. 安装
    print("===== 执行安装 =====")
    install_output = run_command_blocking("curl https://download.hyper.space/api/install | bash")
    if "Installation completed successfully." not in install_output:
        print("安装失败或未检测到成功提示。")
        return
    print("安装成功！")

    # 2. 启动后端服务（后台运行，不阻塞）
    subprocess.Popen("/root/.aios/aios-cli start", shell=True)
    print("后端命令已启动。")
    time.sleep(5)  # 等待后端服务启动

    # 3. 下载大模型，等待输出中出现 "Download complete"
    print("开始下载大模型...")
    run_command_and_print(
        "/root/.aios/aios-cli models add hf:bartowski/Llama-3.2-1B-Instruct-GGUF:"
        "Llama-3.2-1B-Instruct-Q8_0.gguf", wait_for="Download complete"
    )
    print("下载完成！")

    # 4. 执行 infer 命令
    print("执行 infer 命令...")
    run_command_and_print(
        "/root/.aios/aios-cli infer --model hf:bartowski/Llama-3.2-1B-Instruct-GGUF:"
        "Llama-3.2-1B-Instruct-Q8_0.gguf --prompt 'What is 1+1 equal to?'"
    )
    print("推理命令执行完毕。")

    # 5. Hive 登录，提取 Public 和 Private Key
    print("开始 Hive 登录...")
    login_output = run_command_and_print("/root/.aios/aios-cli hive login", wait_for="Authenticated successfully!")
    public_key = None
    private_key = None
    public_match = re.search(r"Public:\s*(\S+)", login_output)
    private_match = re.search(r"Private:\s*(\S+)", login_output)
    if public_match:
        public_key = public_match.group(1)
    if private_match:
        private_key = private_match.group(1)
    print(f"Public Key: {public_key}")
    print(f"Private Key: {private_key}")

    # 6. 执行 hive whoami 命令
    print("执行 hive whoami 命令...")
    run_command_blocking("/root/.aios/aios-cli hive whoami")
    print("whoami 命令执行完毕。")

    # 7. 执行 hive select-tier 5 命令
    print("执行 hive select-tier 5 命令...")
    run_command_blocking("/root/.aios/aios-cli hive select-tier 5")
    print("select-tier 命令执行完毕。")

    # 8. 执行 hive connect 命令
    print("执行 hive connect 命令...")
    run_command_blocking("/root/.aios/aios-cli hive connect")
    print("connect 命令执行完毕。")

    # 9. 启动定时积分查询任务，每 10 分钟执行一次 hive points 命令
    points_thread = threading.Thread(target=fetch_points, daemon=True)
    points_thread.start()
    print("定时积分查询任务已启动，每隔 10 分钟获取一次积分。")

    # 保持主线程运行
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
