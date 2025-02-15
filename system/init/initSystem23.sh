#!/bin/bash

##############################################################################
# initSystem.sh
# --------------
# 使用方法示例：
#   sudo ./initSystem.sh \
#       --user admin \
#       --password 'MyP@ssw0rd' \
#       --serverId 123 \
#       --appId 456
#
# 该脚本将：
# 1. 安装基础工具 (tar, gcc, vim, wget, python3, pip3, git等)
# 2. 安装并配置 TightVNC (端口默认 25931) + Xfce4 桌面环境
# 3. 安装 XRDP 并启动 (默认监听3389端口，可使用 Windows远程桌面或任何 RDP 客户端)
# 4. 安装并启动 noVNC (通过浏览器访问)
##############################################################################

# 默认 VNC 端口
VNC_PORT=25931   # 在此可自定义要使用的 VNC 端口

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:s:a: \
  --long user:,password:,serverId:,appId: \
  -n 'initSystem.sh' -- "$@")

if [ $? -ne 0 ]; then
    echo "Failed to parse options."
    exit 1
fi
eval set -- "$TEMP"

# 定义空变量用于存储命令行参数
VNCUSER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""

# 处理命令行参数
while true; do
  case "$1" in
    --user)
      VNCUSER="$2"
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
      echo "用法: $0 --user <USER> --password <PASSWORD> --serverId <SERVER_ID> --appId <APP_ID>"
      exit 1
      ;;
  esac
done

# 如果没有传递账号、密码、serverId 或 appId，打印错误信息并退出
if [ -z "$VNCUSER" ] || [ -z "$PASSWORD" ] || [ -z "$SERVER_ID" ] || [ -z "$APP_ID" ]; then
  echo "用法: $0 --user <USER> --password <PASSWORD> --serverId <SERVER_ID> --appId <APP_ID>"
  exit 1
fi

# 设置 debconf 为非交互模式
export DEBIAN_FRONTEND=noninteractive

# 预先设置键盘配置默认值（避免安装过程中的交互）
echo 'keyboard-configuration keyboard-configuration/layoutcode string us'   | debconf-set-selections
echo 'keyboard-configuration keyboard-configuration/modelcode string pc105' | debconf-set-selections

##############################################################################
# 更新并安装基础软件
##############################################################################
echo "Updating package list..."
apt-get update -y

echo "Installing tar, gcc, vim, wget..."
apt-get install -y tar gcc vim wget

echo "Installing Python 3 and pip..."
apt-get install -y python3 python3-pip python3-dev

echo "Installing git..."
apt-get install -y git

echo "Installing other dependencies..."
apt-get install -y psmisc

# 打印 Python & pip 版本
echo "Python and pip versions:"
python3 --version
pip3 --version

# 安装 Python 基础插件
echo "Installing Python libraries..."
pip3 install --no-cache-dir psutil requests paho-mqtt selenium

##############################################################################
# 安装桌面环境、VNC、XRDP等
##############################################################################
echo "Installing xfce4, xfce4-goodies, tightvncserver, xrdp, expect, sudo..."
apt-get install -y \
    xfce4 \
    xfce4-goodies \
    tightvncserver \
    xrdp \
    expect \
    sudo

##############################################################################
# 创建用户
##############################################################################
if id "$VNCUSER" &>/dev/null; then
    echo "用户 $VNCUSER 已存在，跳过创建步骤"
else
    echo "创建用户 $VNCUSER ..."
    useradd -m -s /bin/bash "$VNCUSER"
    echo "$VNCUSER:$PASSWORD" | chpasswd
    # 如果需要让此用户可使用 sudo，则取消下面行的注释
    # usermod -aG sudo "$VNCUSER"
fi

sleep 2

##############################################################################
# 以新建用户身份执行 VNC 配置
##############################################################################
echo "开始以新建用户($VNCUSER)的身份执行 VNC 配置..."

# 将必要变量传递进 sudo 环境
sudo -u "$VNCUSER" VNC_PASS="$PASSWORD" VNC_REAL_PORT="$VNC_PORT" bash <<'INNEREOF'
  # 在这里引用外层传来的 VNC_PASS 和 VNC_REAL_PORT

  # 确保 ~/.vnc 文件夹存在，并设置正确权限
  mkdir -p "$HOME/.vnc"
  chmod 700 "$HOME/.vnc"

  # 构造 expect 脚本，用于初始化 VNC 密码
  EXPECT_SCRIPT=$(cat <<EOL
spawn tightvncserver :23 -rfbport ${VNC_REAL_PORT}
expect "Password:"
send "${VNC_PASS}\r"
expect "Verify:"
send "${VNC_PASS}\r"
expect "Would you like to enter a view-only password (y/n)?"
send "n\r"
expect eof
EOL
)
  sleep 2
  # 如果 VNC 服务器已经启动，先关闭以免重复配置
  tightvncserver -kill :23 >/dev/null 2>&1 || true
  sleep 2
  # 使用 expect 脚本自动输入密码（避免人工干预）
  expect -c "$EXPECT_SCRIPT"

  # 写入 xstartup 脚本，启动 Xfce4
  cat > "$HOME/.vnc/xstartup" <<'XSTARTUP'
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
XSTARTUP

  chmod +x "$HOME/.vnc/xstartup"

  # 为了确保 xstartup 配置生效，先关闭已有的 VNC 会话（如果有的话）
  tightvncserver -kill :23 >/dev/null 2>&1 || true

  # 最终启动 VNC 服务器，指定显示号、端口、分辨率和颜色深度
  tightvncserver :23 -rfbport ${VNC_REAL_PORT} -geometry 1920x1080 -depth 24
INNEREOF

##############################################################################
# XRDP 配置：让 XRDP 使用 Xfce4
##############################################################################
echo "Configuring XRDP..."
echo "startxfce4" > /home/$VNCUSER/.xsession
chown $VNCUSER:$VNCUSER /home/$VNCUSER/.xsession

# 如 XRDP 未运行，则启动
if ! service xrdp status | grep -q "running"; then
    echo "XRDP未运行，正在启动..."
    service xrdp start
    sleep 10
else
    echo "XRDP已在运行。"
fi

##############################################################################
# 检查 VNC 是否在运行，如没有则启动
##############################################################################
echo "检查 VNC 是否正在运行..."
if ! pgrep -f "tightvncserver :23" > /dev/null; then
    echo "VNC 尚未运行，正在启动..."
    sudo -u "$VNCUSER" tightvncserver :23 -rfbport $VNC_PORT -geometry 1920x1080 -depth 24 &
    sleep 10  # 等待 VNC 启动并绑定端口
else
    echo "VNC 已在运行，跳过启动。"
fi

##############################################################################
# 安装 & 启动 noVNC
##############################################################################
if [ -d "noVNC" ]; then
    echo "noVNC 目录已存在，跳过 git clone。"
else
    echo "Downloading noVNC repository..."
    git clone https://github.com/novnc/noVNC.git
fi

echo "检查 noVNC 是否正在运行..."
if pgrep -f "novnc_proxy" > /dev/null; then
    echo "noVNC proxy 已在运行。"
else
    echo "Starting noVNC proxy..."
    nohup ./noVNC/utils/novnc_proxy \
        --vnc localhost:$VNC_PORT \
        --listen 26380 \
        &> /dev/null &
    echo "noVNC proxy started in the background (listening on port 26380)."
fi

##############################################################################
# 最后输出信息
##############################################################################
echo "=== 安装和配置已完成 ==="
echo -e "\n"