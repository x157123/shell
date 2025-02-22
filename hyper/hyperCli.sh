#!/bin/bash
# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""
DECRYPT_KEY=""

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:k:s:a: --long user:,password:,decryptKey:,serverId:,appId: -n 'startChrome.sh' -- "$@")
if [ $? != 0 ]; then
    echo "Failed to parse options."
    exit 1
fi
eval set -- "$TEMP"

while true; do
    case "$1" in
        -u|--user)
            USER=$2
            shift 2
            ;;
        -p|--password)
            PASSWORD=$2
            shift 2
            ;;
        -k|--decryptKey)
            DECRYPT_KEY=$2
            shift 2
            ;;
        -s|--serverId)
            SERVER_ID=$2
            shift 2
            ;;
        -a|--appId)
            APP_ID=$2
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Internal error!"
            exit 1
            ;;
    esac
done

# 如果没有传递 serverId 或 appId，打印错误信息并退出
if [ -z "$SERVER_ID" ] || [ -z "$APP_ID" ]; then
  echo "Usage: $0 --serverId SERVER_ID --appId APP_ID [--user USER] [--password PASSWORD]"
  exit 1
fi

# 如果没有传递 user，则可以在此提醒（可选）
if [ -z "$USER" ]; then
  echo "Warning: --user 未指定，将默认以 admin 身份执行相关操作（如需特定用户，请使用 --user）"
fi

# 安装其他插件
pip3 install psutil requests paho-mqtt selenium pycryptodome loguru pyperclip

sudo mkdir -p /opt/hyper/

# 查找运行中的 hyperCli.py 进程（使用完整命令匹配）
pids=$(pgrep -f "python3 /opt/hyper/hyperCli.py")
if [ -n "$pids" ]; then
    echo "检测到正在运行的实例: $pids，准备终止..."
    # 注意：kill -9 是强制终止，可根据实际情况换成 kill
    kill -9 $pids
fi

# 如果 /opt/hyper/hyperCli.py 存在，则先删除旧文件
if [ -f /opt/hyper/hyperCli.py ]; then
    echo "/opt/hyper/hyperCli.py 已存在，正在删除旧文件..."
    rm -f /opt/hyper/hyperCli.py
fi

DIR="/home/ubuntu/.aios/aios-cli"
# 判断目录是否存在
if [ ! -f "$DIR" ]; then

    # 下载并执行远程 Python 脚本
    echo "开始下载脚本：https://www.15712345.xyz/shell/hyper/chrome.py ..."
    wget -O /opt/hyper/hyperCli.py https://www.15712345.xyz/shell/hyper/hyperCli.py
    if [ ! -f /opt/hyper/hyperCli.py ]; then
        echo "脚本下载失败，请检查网络连接或 URL 是否正确。"
        exit 1
    fi

    echo "为 /opt/hyper/hyperCli.py 设置可执行权限..."
    chmod +x /opt/hyper/hyperCli.py


    # 执行远程 Python 脚本
    echo "开始执行 /opt/hyper/hyperCli.py ..."
    nohup python3 /opt/hyper/hyperCli.py --serverId "$SERVER_ID" --appId "$APP_ID" --decryptKey "$DECRYPT_KEY" --user "$USER" --display "$window"> hyperChromeOutput.log 2>&1 &

    echo "脚本已在后台执行，日志输出至 hyperCli.log"

else

    if [ -f /root/.aios/aios-cli ]; then
        /root/.aios/aios-cli kill
    fi

    # 下载并执行远程 Python 脚本
    echo "开始下载脚本：https://www.15712345.xyz/shell/hyper/hyperUbuntCli.py ..."
    wget -O /opt/hyper/hyperCli.py https://www.15712345.xyz/shell/hyper/hyperUbuntCli.py
    if [ ! -f /opt/hyper/hyperCli.py ]; then
        echo "脚本下载失败，请检查网络连接或 URL 是否正确。"
        exit 1
    fi
    sudo chown -R ubuntu:ubuntu /opt

    echo "为 /opt/hyper/hyperCli.py 设置可执行权限..."
    chmod +x /opt/hyper/hyperCli.py

    # 执行远程 Python 脚本
    echo "开始执行 /opt/hyper/hyperCli.py ..."
    sudo -u "$USER" -i nohup python3 /opt/hyper/hyperCli.py --serverId "$SERVER_ID" --appId "$APP_ID" --decryptKey "$DECRYPT_KEY" --user "$USER" --display "$window"> hyperChromeOutput.log 2>&1 &


    echo "脚本已在后台执行，日志输出至 hyperCli.log"

fi

