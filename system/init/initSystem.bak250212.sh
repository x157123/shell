#!/bin/bash

# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""
VNC_PORT=25931   # <-- 在此处自定义要使用的 VNC 端口

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:s:a: --long user:,password:,serverId:,appId: -n 'initSystem.sh' -- "$@")
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
# 通过 sudo 以 admin 用户运行 bash，并传递环境变量 VNC_PASS 与 VNC_REAL_PORT
sudo -u "$USER" VNC_PASS="$PASSWORD" VNC_REAL_PORT="$VNC_PORT" bash <<'EOF'
# 这里采用 <<'EOF'，外层不展开其中的变量，下面所使用的变量由 sudo 环境传入

# 确保 ~/.vnc 文件夹存在，并设置正确权限
mkdir -p /home/"$USER"/.vnc
chmod 700 /home/"$USER"/.vnc

# 构造 expect 脚本，注意这里的 here‐doc 使用未引用的 EOL，这样内层 bash 会展开 VNC_PASS 与 VNC_REAL_PORT
EXPECT_SCRIPT=$(cat <<EOL
spawn tightvncserver :1 -rfbport ${VNC_REAL_PORT}
expect "Password:"
send "${VNC_PASS}\r"
expect "Verify:"
send "${VNC_PASS}\r"
expect "Would you like to enter a view-only password (y/n)?"
send "n\r"
expect eof
EOL
)

# 如果 VNC 服务器已经启动，先关闭以免重复配置
tightvncserver -kill :1 >/dev/null 2>&1 || true

# 使用 expect 脚本自动输入密码（不用人工干预）
expect -c "$EXPECT_SCRIPT"

# 配置 ~/.vnc/xstartup 以启动 XFCE 桌面环境
cat > "$HOME/.vnc/xstartup" <<'XSTARTUP'
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
XSTARTUP

chmod +x "$HOME/.vnc/xstartup"

# 为了确保 xstartup 配置生效，先关闭已有的 VNC 会话（如果有的话）
tightvncserver -kill :1 >/dev/null 2>&1 || true

# 最终启动 VNC 服务器，指定显示号、端口、分辨率和颜色深度
tightvncserver :1 -rfbport ${VNC_REAL_PORT} -geometry 1280x800 -depth 24
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
