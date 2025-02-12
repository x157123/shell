#!/bin/bash

# 默认值
VNC_USER=""
VNC_PASSWORD=""
SERVER_ID=""
APP_ID=""
VNC_RFBPORT=25931   # <-- 在此处自定义要使用的 VNC 端口

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:s:a: --long VNC_USER:,VNC_PASSWORD:,serverId:,appId: -n 'initSystem.sh' -- "$@")
if [ $? != 0 ]; then
    echo "Failed to parse options."
    exit 1
fi
eval set -- "$TEMP"

# 处理命令行参数
while true; do
  case "$1" in
    --VNC_USER)
      VNC_USER="$2"
      shift 2
      ;;
    --VNC_PASSWORD)
      VNC_PASSWORD="$2"
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
      echo "Usage: $0 --VNC_USER VNC_USER --VNC_PASSWORD VNC_PASSWORD --serverId SERVER_ID --appId APP_ID"
      exit 1
      ;;
  esac
done

# 如果没有传递账号、密码、serverId 或 appId，打印错误信息并退出
if [ -z "$VNC_USER" ] || [ -z "$VNC_PASSWORD" ] || [ -z "$SERVER_ID" ] || [ -z "$APP_ID" ]; then
  echo "Usage: $0 --VNC_USER VNC_USER --VNC_PASSWORD VNC_PASSWORD --serverId SERVER_ID --appId APP_ID"
  exit 1
fi


###################################################
# 1. 更新系统软件源
###################################################
echo "=== [1/8] 更新系统软件源 ==="
sudo apt update -y

###################################################
# 2. 安装必要软件包
###################################################
echo "=== [2/8] 安装桌面与 VNC 相关软件包 ==="
sudo apt install -y \
    xfce4 xfce4-goodies \
    tigervnc-standalone-server \
    tigervnc-common \
    dbus-x11 \
    xauth \
    xfonts-base \
    curl

###################################################
# 3. 创建并配置 VNC 用户
###################################################
echo "=== [3/8] 创建 VNC 用户: $VNC_USER ==="
if ! id "$VNC_USER" &>/dev/null; then
    sudo adduser --disabled-password --gecos "" "$VNC_USER"
    echo "$VNC_USER:$VNC_PASSWORD" | sudo chpasswd
fi

###################################################
# 4. 初始化 VNC 密码
###################################################
echo "=== [4/8] 初始化 VNC 密码 ==="
# 确保 admin 用户对其 home 目录有读写权限
sudo chown -R $VNC_USER:$VNC_USER /home/$VNC_USER
# 创建 .vnc 目录（如果没有）
sudo -u "$VNC_USER" mkdir -p /home/"$VNC_USER"/.vnc

# 使用 vncpasswd -f 将明文密码转换为 VNC 加密密码
echo "$VNC_PASSWORD" | sudo -u "$VNC_USER" vncpasswd -f > /home/$VNC_USER/.vnc/passwd
sudo chmod 600 /home/$VNC_USER/.vnc/passwd

###################################################
# 5. 创建 xstartup 脚本
###################################################
echo "=== [5/8] 创建 xstartup 脚本 (启动 Xfce) ==="
cat << 'EOF' | sudo -u "$VNC_USER" tee /home/"$VNC_USER"/.vnc/xstartup >/dev/null
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
EOF

sudo chmod +x /home/"$VNC_USER"/.vnc/xstartup

###################################################
# 6. 创建并配置 systemd 服务文件
###################################################
echo "=== [6/8] 创建 systemd 服务文件: vncserver@${VNC_USER}.service ==="
sudo bash -c "cat > /etc/systemd/system/vncserver@${VNC_USER}.service" << EOT
[Unit]
Description=VNC Service for user ${VNC_USER}
After=syslog.target network.target

[Service]
Type=forking
User=${VNC_USER}
Group=${VNC_USER}
WorkingDirectory=/home/${VNC_USER}

PIDFile=/home/${VNC_USER}/.vnc/%H:${VNC_DISPLAY}.pid

ExecStartPre=-/usr/bin/vncserver -kill :${VNC_DISPLAY} > /dev/null 2>&1
ExecStart=/usr/bin/vncserver -depth 24 -geometry 1280x800 -rfbport ${VNC_RFBPORT} :${VNC_DISPLAY}
ExecStop=/usr/bin/vncserver -kill :${VNC_DISPLAY}

[Install]
WantedBy=multi-user.target
EOT

###################################################
# 7. 启动并设置开机自启
###################################################
echo "=== [7/8] 启动并设置开机自启 VNC 服务 ==="
sudo systemctl daemon-reload
sudo systemctl enable vncserver@"${VNC_USER}".service
sudo systemctl start vncserver@"${VNC_USER}".service

echo "======================================="
echo " TigerVNC 安装配置完成"
echo " 用户名:         ${VNC_USER}"
echo " 登录密码:       ${VNC_PASSWORD}"
echo " VNC Display:    :${VNC_DISPLAY}   (仅用于标识)"
echo " 监听端口:       ${VNC_RFBPORT}"
echo
echo " 请在防火墙/安全组中放行端口: ${VNC_RFBPORT}"
echo " 通过 '服务器IP:${VNC_RFBPORT}' 进行 VNC 连接"
echo "======================================="


###################################################
# 8. 安装NoVNC
###################################################
echo "=== [7/8] 安装 NoVNC 服务 ==="

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