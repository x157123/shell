import subprocess
import time
import re
import argparse
from loguru import logger
import json
import zlib
import base64
import os

def run_command_blocking(cmd, print_output=True):
    """
    执行命令，等待命令执行结束，并返回输出内容。
    """
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if print_output:
        logger.info(result.stdout)
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
                logger.info(line.strip())
            if wait_for and wait_for in line:
                break
        if not line and process.poll() is not None:
            break
    process.wait()  # 确保进程退出
    return collected_output



def read_last_n_lines(file_path, n):
    """读取文件最后 n 行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # 使用 collections.deque 高效读取最后 n 行
            from collections import deque
            lines = deque(file, maxlen=n)
            return list(lines)
    except FileNotFoundError:
        logger.info(f"错误：文件 {file_path} 未找到。")
        return []
    except Exception as e:
        logger.info(f"读取文件时发生错误：{e}")
        return []


def check_reconnect_signal(lines, target_string):
    """检查指定字符串是否在行列表中"""
    for line in lines:
        if target_string in line:
            return True
    return False

def start():

    # install_output = run_command_blocking("curl https://download.hyper.space/api/install | bash")
    # if "Installation completed successfully." not in install_output:
    #     logger.info("安装失败或未检测到成功提示。")
    # logger.info("安装成功！")

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

    # Hive 登录，提取 Public 和 Private Key
    logger.info("开始 Hive 登录...")
    run_command_and_print("/root/.aios/aios-cli hive login", wait_for="Authenticated successfully!")

    # if public_key is not None:
    #     logger.info("已配置了key...")
    # else:

    # 6. 获取key执行 hive whoami 命令
    logger.info("执行 hive whoami 命令...")
    login_output = run_command_blocking("/root/.aios/aios-cli hive whoami")
    public_key = None
    private_key = None
    public_match = re.search(r"Public:\s*(\S+)", login_output)
    private_match = re.search(r"Private:\s*(\S+)", login_output)
    if public_match:
        public_key = public_match.group(1)
    if private_match:
        private_key = private_match.group(1)

    with open("/root/.config/hyperspace/key.pem", "r", encoding="utf-8") as file:
        key_content = file.read()

    logger.info(f"Public Key: {public_key}")
    logger.info(f"Private Key: {private_key}")
    # logger.info(f"key_content: {key_content}")
    logger.info("whoami 命令执行完毕。")

    # 7. 执行 hive select-tier 5 命令
    logger.info("执行 hive select-tier 5 命令...")
    run_command_blocking("/root/.aios/aios-cli hive select-tier 5")
    logger.info("select-tier 命令执行完毕。")

    # 8. 执行 hive connect 命令
    logger.info("执行 hive connect 命令...")
    run_command_blocking("/root/.aios/aios-cli hive connect")
    logger.info("connect 命令执行完毕。")


def restart():
    logger.info("===== 检测是否已启动 =====")
    status_output = run_command_blocking("/root/.aios/aios-cli status")
    if "Daemon running on" in status_output:
        logger.info("杀掉程序。")
        run_command_blocking("/root/.aios/aios-cli kill")
        time.sleep(10)  # 等待 10 秒
    logger.info("检查结束！")

    logger.info("开始 Hive 登录...")
    run_command_and_print("/root/.aios/aios-cli hive login", wait_for="Authenticated successfully!")

    logger.info("执行 hive connect 命令...")
    run_command_blocking("/root/.aios/aios-cli hive connect")
    logger.info("connect 命令执行完毕。")

def decompress_data(compressed_b64):
    # 先进行 base64 解码，得到压缩后的 bytes
    compressed = base64.b64decode(compressed_b64)
    # 解压得到原始 JSON 字符串
    json_str = zlib.decompress(compressed).decode('utf-8')
    # 将 JSON 字符串转换回字典
    data = json.loads(json_str)
    return data


def ensure_key_file(expected_content, key_path="/root/.config/hyperspace/key.pem"):
    """
    确保密钥文件存在且内容匹配，不存在时自动创建
    返回: (文件存在状态, 内容匹配状态)
    """
    # 预处理输入内容
    expected = expected_content.strip()

    # 验证PEM格式有效性
    if not (expected.startswith("-----BEGIN PRIVATE KEY-----") and
            expected.endswith("-----END PRIVATE KEY-----")):
        raise ValueError("Invalid PEM private key format")

    # 自动创建目录（处理多级嵌套路径）
    key_dir = os.path.dirname(key_path)
    try:
        os.makedirs(key_dir, mode=0o700, exist_ok=True)  # 确保目录权限安全
    except PermissionError:
        logger.info(f"权限不足，无法创建目录 {key_dir}")
        return False, False
    except Exception as e:
        logger.info(f"目录创建失败: {str(e)}")
        return False, False

    # 检查文件存在性
    file_exists = os.path.exists(key_path)
    content_matched = False

    try:
        # 文件存在时验证内容
        if file_exists:
            with open(key_path, "r", encoding="utf-8") as f:
                actual = f.read().strip()
                content_matched = (actual == expected)
                if not content_matched:
                    # 如果内容不匹配，删除旧的密钥文件
                    os.remove(key_path)
                    logger.info(f"旧密钥文件 {key_path} 已被删除。")

                    # 创建并写入新的密钥文件
                    temp_path = key_path + ".tmp"
                    with open(temp_path, "w", encoding="utf-8") as f:
                        f.write(expected + "\n")  # 确保末尾换行符

                    # 设置严格权限（仅用户可读）
                    os.chmod(temp_path, 0o600)
                    os.rename(temp_path, key_path)  # 原子操作
                    logger.info(f"已创建新密钥文件1: {key_path}")
                    return
        # 文件不存在时创建并写入
        else:
            # 原子写入模式：先写入临时文件再重命名
            temp_path = key_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(expected + "\n")  # 确保末尾换行符

            # 设置严格权限（仅用户可读）
            os.chmod(temp_path, 0o600)
            os.rename(temp_path, key_path)  # 原子操作

            logger.info(f"已创建新密钥文件2: {key_path}")
            return

    except PermissionError:
        logger.info(f"权限不足，无法操作文件 {key_path}")
        return file_exists, False
    except Exception as e:
        logger.info(f"文件操作异常: {str(e)}")
        return file_exists, False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--data", type=str, help="数据", required=True)
    args = parser.parse_args()
    logger.info(f"===== 启动 ====={args.data}")
    restored_data = decompress_data(args.data)
    logger.info(f"恢复后的数据：{restored_data['public_key']}")
    logger.info(f"恢复后的数据：{restored_data['private_key']}")
    logger.info(f"恢复后的数据：{restored_data['remarks']}")
    ensure_key_file(restored_data['remarks'])
    time.sleep(10)
    start()
    # 等待20S
    time.sleep(20)
    num = 10
    count = 0
    # 获取积分
    while True:
        try:
            num += 1
            # 读取最后 3 行
            last_lines = read_last_n_lines('/tmp/hyperCliOutput.log', 3)
            if last_lines:
                # 查找是否网络连接失败 Sending reconnect signal
                if check_reconnect_signal(last_lines, 'Sending reconnect signal'):
                    logger.info(f"未连接网络。重新连接->{num}")
                    start()
                else:
                    count = 0
                    logger.info(f"已连接网络。->{num}")

            if num > 10:
                logger.info("\n===== 积分查询输出 =====")
                login_output = run_command_blocking("/root/.aios/aios-cli hive points")
                points = None
                public_match = re.search(r"Points:\s*(\S+)", login_output)
                if public_match:
                    points = public_match.group(1)

                if not points or points == "None":
                    logger.info("获取积分失败,重新启动。")
                    start()
                else:
                    count = 0
                    num = 0
                    logger.info(f"points: {points}")
                    logger.info("获取积分完成。")
            time.sleep(360)
        except Exception as e:
            logger.info("异常。")