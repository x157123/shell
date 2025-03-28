import subprocess
from loguru import logger
import time


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


def main():
    # 1. 安装
    logger.info("===== 执行安装 =====")
    install_output = run_command_blocking("curl https://download.hyper.space/api/install | bash")
    if "Installation completed successfully." not in install_output:
        logger.info("安装失败或未检测到成功提示。")
        return
    logger.info("安装成功！")

    logger.info("===== 检测是否已启动 =====")
    status_output = run_command_blocking("/root/.aios/aios-cli status")
    if "Daemon running on" in status_output:
        logger.info("杀掉程序。")
        run_command_blocking("/root/.aios/aios-cli kill")
        time.sleep(10)  # 等待 10 秒
    logger.info("检查结束！")

    # 2. 启动后端服务（后台运行，不阻塞）
    subprocess.Popen("/root/.aios/aios-cli start", shell=True)
    logger.info("后端命令已启动。")
    time.sleep(5)  # 等待后端服务启动

    # 3. 下载大模型，等待输出中出现 "Download complete"
    logger.info("开始下载大模型...")
    run_command_and_print(
        "/root/.aios/aios-cli models add hf:bartowski/Llama-3.2-1B-Instruct-GGUF:Llama-3.2-1B-Instruct-Q8_0.gguf", wait_for="Download complete"
    )
    logger.info("下载完成！")


if __name__ == "__main__":
    main()