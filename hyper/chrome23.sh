#!/bin/bash
# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:s:a: --long user:,password:,serverId:,appId: -n 'startChrome.sh' -- "$@")
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


# 安装 Google Chrome（可选，如需浏览器功能）
if ! dpkg -l | grep -q "google-chrome-stable"; then
    echo "=== 安装 Google Chrome ==="
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    if [ ! -f google-chrome-stable_current_amd64.deb ]; then
        echo "Google Chrome 下载失败"
        exit 1
    fi
    apt-get install -y ./google-chrome-stable_current_amd64.deb
    rm -f google-chrome-stable_current_amd64.deb
fi


# 如果 /opt/chrome.py 存在，则先删除旧文件
if [ -f /opt/chrome.py ]; then
    echo "/opt/chrome.py 已存在，正在删除旧文件..."
    rm -f /opt/chrome.py
fi

# 下载并执行远程 Python 脚本
echo "开始下载脚本：https://www.15712345.xyz/shell/hyper/chrome.py ..."
wget -O /opt/chrome.py https://www.15712345.xyz/shell/hyper/chrome.py
if [ ! -f /opt/chrome.py ]; then
    echo "脚本下载失败，请检查网络连接或 URL 是否正确。"
    exit 1
fi

echo "为 /opt/chrome.py 设置可执行权限..."
chmod +x /opt/chrome.py

# 如果用户传了 --user，则将文件属主改为该用户，同时后续用该用户执行
if [ -n "$USER" ]; then
    chown "$USER":"$USER" /opt/chrome.py
fi

# 根据实际需求决定 drissionpage 的安装位置
# 如果你希望以系统方式安装，可保留在外部安装
# 如果想让指定用户安装，则放到 sudo -u $USER -i 环境中执行
echo "安装/升级 drissionpage ..."
pip3 install --upgrade drissionpage

# 安装剪切板
apt-get install xclip

# 安装其他插件
pip3 install --no-cache-dir psutil requests paho-mqtt selenium pycryptodome

# 以特定用户启动 chrome
# 如果未指定 --user，则默认用 admin（或你想要的其它用户）
SUDO_USER="${USER:-admin}"

sudo -u "$SUDO_USER" -i bash <<'EOF'
# 内部脚本：用以特定用户的身份执行

# 检查 9515 端口是否被占用
PIDS=$(lsof -t -i:9515 -sTCP:LISTEN)
if [ -n "$PIDS" ]; then
    echo "9515 端口已被占用，终止占用该端口的进程：$PIDS"
    # 强制终止进程（请确保被终止的进程确实为 chrome，否则可能误杀其它进程）
    kill -9 $PIDS
    sleep 1
fi

# 如果存在已命名为 chrome 的 screen 会话，则关闭该会话（确保全新启动）
if screen -list | grep -q "\.chrome"; then
    echo "关闭现有的 screen 会话 chrome"
    screen -S chrome -X quit
fi

# 设置 DISPLAY 环境变量，根据实际情况修改
export DISPLAY=:23

echo "启动 google-chrome —— 使用远程调试模式监听 9515 端口..."
screen -dmS chrome bash -c "export DISPLAY=:23; google-chrome --remote-debugging-port=9515 --no-first-run --disable-web-security"
# screen -dmS chrome bash -c "export DISPLAY=:23; google-chrome --remote-debugging-port=9515 --no-first-run --disable-gpu-blocklist --disable-software-rasterizer=false --use-gl=swiftshader --enable-features=Vulkan --enable-unsafe-webgpu"

MAX_WAIT=30   # 最大等待时间，单位秒
counter=0
while ! lsof -i:9515 -sTCP:LISTEN >/dev/null 2>&1; do
    sleep 1
    counter=$((counter+1))
    if [ $counter -ge $MAX_WAIT ]; then
        echo "等待 google-chrome 启动超时！"
        exit 1
    fi
done

echo "google-chrome 已成功启动，9515 端口正在监听。"

# 执行远程 Python 脚本
echo "开始执行 /opt/chrome.py ..."
nohup python3 /opt/chrome.py --serverId "$SERVER_ID" --appId "$APP_ID" --decryptKey "$DECRYPT_KEY" --user "$SUDO_USER"> hyperOutput.log 2>&1 &
EOF

# 执行远程 Python 脚本
echo "开始执行 /opt/chrome.py ..."
# 若需要脚本以该用户身份执行，使用 sudo -u。如果 python3 路径不一致，可改为绝对路径
nohup sudo -u "$SUDO_USER" -i python3 /opt/chrome.py --serverId "$SERVER_ID" --appId "$APP_ID" > chromeOutput.log 2>&1 &

echo "脚本已在后台执行，日志输出至 chromeOutput.log"
