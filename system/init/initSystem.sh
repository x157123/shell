#!/bin/bash

# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""
VNC_PORT=25931   # <-- 在此处自定义要使用的 VNC 端口

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:s:a: --long user:,password:,serverId:,appId: -n 'docker-entrypoint.sh' -- "$@")
if [ $? != 0 ]; then
    echo "Failed to parse options."
    exit 1
fi
eval set -- "$TEMP"

# 处理命令行参数
while true; do
  case "$1" in
    --user)
      USER="$2"
      shift 2
      ;;
    --password)
      PASSWORD="$2"
      shift 2
      ;;
    --serverId)
      SERVER_ID="$2"
      shift 2
      ;;
    --appId)
      APP_ID="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "Usage: $0 --user USER --password PASSWORD --serverId SERVER_ID --appId APP_ID"
      exit 1
      ;;
  esac
done

# 如果没有传递账号、密码、serverId 或 appId，打印错误信息并退出
if [ -z "$USER" ] || [ -z "$PASSWORD" ] || [ -z "$SERVER_ID" ] || [ -z "$APP_ID" ]; then
  echo "Usage: $0 --user USER --password PASSWORD --serverId SERVER_ID --appId APP_ID"
  exit 1
fi

# 设置 debconf 为非交互模式
export DEBIAN_FRONTEND=noninteractive

# 预先设置键盘配置默认值（避免安装过程中的交互）
echo 'keyboard-configuration keyboard-configuration/layoutcode string us'   | debconf-set-selections
echo 'keyboard-configuration keyboard-configuration/modelcode string pc105' | debconf-set-selections

# 更新包列表
echo "Updating package list..."

echo "Installing tar..."
apt-get update -y

echo "Installing gcc..."
apt-get install gcc -y

# 安装 tar
echo "安装 tar..."
apt-get install tar -y

# 安装 vim
echo "Installing vim..."
apt-get install vim -y

# 安装 wget
echo "Installing wget..."
apt-get install wget -y

# 安装 Python 3 和 pip
echo "Installing Python 3 and pip..."
apt-get install python3 -y
apt-get install python3-pip -y
apt-get install python3-devel -y 

# 安装 git
echo "Installing git..."
apt-get install git -y

# 确认 Python 和 pip 已安装
echo "Python and pip versions:"
python3 --version
pip3 --version

# 安装python 基础插件
echo "安装python 基础插件:"
# 安装python mqtt
pip3 install psutil requests
# 移除 needrestart 软件包（可选操作，防止安装时各种提示）
pip3 install paho-mqtt
# 安装selenium
pip3 install selenium


echo "安装桌面环境和远程访问工具:"
# 安装桌面环境和远程访问工具
apt-get install -y \
    xfce4 \
    xfce4-goodies \
    tightvncserver \
    xrdp \
    expect \
    sudo

# 创建用户（如果不存在）
if id "$USER" &>/dev/null; then
    echo "用户 $USER 已存在，跳过创建步骤"
else
    echo "创建用户 $USER"
    useradd -m -s /bin/bash "$USER"
    echo "$USER:$PASSWORD" | chpasswd
    # 如需让此用户可使用 sudo，则取消下面行的注释
    # usermod -aG sudo "$USER"
fi

echo "以新建用户的身份执行 VNC 配置:"
# 以新建用户的身份执行 VNC 配置
sudo -u "$USER" bash <<EOF
# 设置 VNC 密码（使用 expect 脚本自动输入密码）
VNC_PASS="$PASSWORD"
VNC_REAL_PORT="$VNC_PORT"

# 创建 .vnc 文件夹（如果还不存在）
mkdir -p "\$HOME/.vnc"
chmod 700 "\$HOME/.vnc"

EXPECT_SCRIPT=\$(cat <<EOL
spawn tightvncserver :1 -rfbport \$VNC_REAL_PORT
expect "Password:"
send "\$VNC_PASS\r"
expect "Verify:"
send "\$VNC_PASS\r"
expect "Would you like to enter a view-only password (y/n)?"
send "n\r"
expect eof
EOL
)

# 如果已经启动过 VNC，需要先 kill 防止重复设置
tightvncserver -kill :1 >/dev/null 2>&1 || true

expect -c "\$EXPECT_SCRIPT"

# 配置 ~/.vnc/xstartup 以使用 XFCE 桌面环境
cat > "\$HOME/.vnc/xstartup" <<XSTARTUP
#!/bin/bash
xrdb \$HOME/.Xresources
startxfce4 &
XSTARTUP

chmod +x "\$HOME/.vnc/xstartup"

# 为了确保 xstartup 生效，先启动、再关闭一次
tightvncserver -kill :1

# 最终重新启动 VNC Server，端口依旧使用 \$VNC_REAL_PORT
tightvncserver :1 -rfbport \$VNC_REAL_PORT -geometry 1280x800 -depth 24
EOF

# XRDP 默认配置使用 /etc/xrdp/startwm.sh
# 这里在用户主目录写入 .xsession，确保 XRDP 会话也使用 XFCE4
echo "startxfce4" > /home/$USER/.xsession
chown $USER:$USER /home/$USER/.xsession

echo "=== 安装和配置已完成 ==="
echo "Server ID: $SERVER_ID"
echo "App ID: $APP_ID"

if ! pgrep -f "tightvncserver :1" > /dev/null; then
    echo "VNC尚未启动，正在启动..."
    sudo -u "$USER" tightvncserver :1 -rfbport $VNC_PORT -geometry 1280x800 -depth 24 &
else
    echo "VNC已在运行，跳过启动。"
fi

if ! service xrdp status | grep -q "running"; then
    echo "XRDP未运行，正在启动..."
    service xrdp start
else
    echo "XRDP已在运行。"
fi

# 检查是否已经存在 noVNC 目录
if [ -d "noVNC" ]; then
    echo "noVNC directory already exists. Skipping git clone."
else
    echo "Downloading noVNC repository..."
    git clone https://github.com/novnc/noVNC.git
fi

# 检查 novnc_proxy 是否已经在运行

if pgrep -f "novnc_proxy" > /dev/null
then
    echo "noVNC proxy is already running."
else
    echo "Starting noVNC proxy..."
    nohup ./noVNC/utils/novnc_proxy --vnc localhost:$VNC_PORT --listen 26380 &> /dev/null &
    echo "noVNC proxy started in the background."
fi

echo -e "\n"

# 检查 sendSystem.py 是否已存在，如果存在则删除
if [ -f "sendSystem.py" ]; then
    echo "sendSystem.py 文件已存在，正在删除..."
    rm -f sendSystem.py
fi

cat > sendSystem.py <<EOF
import psutil
import paho.mqtt.client as mqtt
import json
import time
import argparse

def get_server_info(server_id):
    """获取服务器的CPU、内存和磁盘信息"""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_size = round(memory.total / 1024 / 1024, 2)  # 转换为 MB
    memory_available = round(memory.available / 1024 / 1024, 2)  # 转换为 MB
    disk = psutil.disk_usage('/')
    disk_size = round(disk.total / 1024 / 1024, 2)  # 转换为 MB
    disk_available = round(disk.free / 1024 / 1024, 2)  # 转换为 MB

    return {
        "id": f"{server_id}",
        "cpuUsage": f"{cpu_usage}",
        "memorySize": f"{memory_size}",
        "memoryAvailable": f"{memory_available}",
        "diskSize": f"{disk_size}",
        "diskAvailable": f"{disk_available}"
    }

def create_mqtt_client(broker, port, username, password, topic):
    """
    创建并配置MQTT客户端，使用 MQTTv5 回调方式
    protocol=mqtt.MQTTv5 来避免旧版回调弃用警告
    """
    client = mqtt.Client(
        protocol=mqtt.MQTTv5,         # 指定使用 MQTTv5
        userdata={"topic": topic}     # 传递自定义数据
    )
    client.username_pw_set(username, password)

    # 注册回调函数（使用 v5 风格签名）
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # 尝试连接到 Broker
    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        raise ConnectionError(f"Error connecting to broker: {e}")

    return client

# ========== MQTT 事件回调函数（MQTTv5） ==========

def on_connect(client, userdata, flags, reason_code, properties=None):
    """
    当客户端与 Broker 建立连接后触发
    reason_code = 0 表示连接成功，否则为失败码
    """
    if reason_code == 0:
        print("Connected to broker successfully.")
        # 订阅主题（从 userdata 中获取）
        client.subscribe(userdata["topic"])
    else:
        print(f"Connection failed with reason code: {reason_code}")

def on_disconnect(client, userdata, reason_code, properties=None):
    """
    当客户端与 Broker 断开连接后触发
    可以在此处进行自动重连逻辑
    """
    print(f"Disconnected from broker, reason_code: {reason_code}")
    # 如果 reason_code != 0，则表示非正常断开
    while True:
        try:
            print("Attempting to reconnect...")
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # 等待 5 秒后重试

def on_message(client, userdata, msg):
    """
    当收到订阅主题的新消息时触发
    v5 中的 on_message 参数与 v3.x 相同： (client, userdata, message)
    """
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")

# ========== 主程序入口 ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启动服务器信息推送脚本")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    args = parser.parse_args()

    # MQTT 配置
    BROKER = "150.109.5.143"
    PORT = 1883
    TOPIC = "systemInfo"
    USERNAME = "userName"
    PASSWORD = "liuleiliulei"

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client(BROKER, PORT, USERNAME, PASSWORD, TOPIC)
    client.loop_start()  # 启动网络循环

    try:
        while True:
            # 获取服务器信息并发送
            server_info = get_server_info(args.serverId)
            client.publish(TOPIC, json.dumps(server_info))
            time.sleep(60)  # 每 60 秒发送一次
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        client.loop_stop()
        client.disconnect()


EOF

chmod +x ./sendSystem.py

# 检查是否已经启动
PID=$(ps -ef | grep sendSystem.py | grep -v "grep" | awk '{print $2}')

if [ -n "$PID" ]; then
  echo "Script is already running with PID: $PID. Killing it..."
  kill -9 $PID
else
  echo "Script is not running."
fi

# 启动脚本
echo "Starting the script..."
nohup python3 ./sendSystem.py --serverId "$SERVER_ID" --appId "$APP_ID"  > sendSysOutput.log 2>&1 &
echo "Failed to start the script."
