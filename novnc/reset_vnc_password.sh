#!/bin/bash

VNC_PORT=25931   # <-- 在此处自定义要使用的 VNC 端口

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "用法：$0 <用户名> <新密码>"
  exit 1
fi

USER="$1"
PASSWORD="$2"
VNC_DISPLAY=":1"

# 必须以 root 执行，才能切换到指定 USER
if [ "$(whoami)" != "root" ]; then
  echo "必须以 root 用户执行此脚本。"
  exit 1
fi

echo "==== 停止 VNC 服务 ===="
sudo -u "$USER" tightvncserver -kill "$VNC_DISPLAY" >/dev/null 2>&1 || true

echo "==== 删除旧 VNC 密码文件 ===="
sudo -u "$USER" rm -f /home/"$USER"/.vnc/passwd

echo "==== 生成新密码并写入 ~/.vnc/passwd ===="
# -f: 从stdin读取密码后输出加密结果
# 这里用 echo 将新密码传入，然后重定向生成 ~/.vnc/passwd
echo "$PASSWORD" | sudo -u "$USER" vncpasswd -f > /home/"$USER"/.vnc/passwd

echo "==== 确保权限正确 ===="
chown "$USER":"$USER" /home/"$USER"/.vnc/passwd

# 确保权限正确
sudo -u "$USER" chmod 600 /home/"$USER"/.vnc/passwd

echo "==== 重新启动 VNC 服务 ===="
sudo -u "$USER" tightvncserver "$VNC_DISPLAY"

echo "==== VNC 密码已更新，服务已重启 ===="
echo "VNC Display: $VNC_DISPLAY"




echo "以新建用户的身份执行 VNC 配置:"
# 通过 sudo 以 admin 用户运行 bash，并传递环境变量 VNC_PASS 与 VNC_REAL_PORT
sudo -u "$USER" VNC_PASS="$PASSWORD" VNC_REAL_PORT="$VNC_PORT" bash <<'EOF'
# 这里采用 <<'EOF'，外层不展开其中的变量，下面所使用的变量由 sudo 环境传入

# 确保 ~/.vnc 文件夹存在，并设置正确权限
mkdir -p "$HOME/.vnc"
chmod 700 "$HOME/.vnc"

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
