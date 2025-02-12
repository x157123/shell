#!/usr/bin/env bash
#
# 在 Ubuntu 22.04 上安装并配置 TigerVNC + Xfce
# 并将 VNC 监听端口改为自定义端口 (例如 25931)
#
# 使用方法：
#   chmod +x install_vnc.sh
#   sudo ./install_vnc.sh
#

set -e

###################################################
# 根据实际需要修改以下三项
###################################################
VNC_PASSWORD="*_Xsh]3Nmt*Bz5DyfN"      # VNC 密码（任意设）
VNC_USER="admin"         # 用于登录的系统用户
VNC_RFBPORT="25931"        # VNC Server真正监听的端口

# VNC 显示编号: 用来区分不同的 VNC 实例，通常用 :1、:2 等，
# 但和端口无直接关系；只要不冲突即可。
VNC_DISPLAY="1"


###################################################
# 1. 更新系统软件源
###################################################
echo "=== [1/7] 更新系统软件源 ==="
sudo apt update -y

###################################################
# 2. 安装必要软件包
###################################################
echo "=== [2/7] 安装桌面与 VNC 相关软件包 ==="
# 安装 Xfce 桌面和 TigerVNC
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
echo "=== [3/7] 创建 VNC 用户: $VNC_USER ==="
# 如果用户已存在，则可忽略此步骤或根据需求注释掉
if ! id "$VNC_USER" &>/dev/null; then
    sudo adduser --disabled-password --gecos "" "$VNC_USER"
    echo "$VNC_USER:$VNC_PASSWORD" | sudo chpasswd
fi

###################################################
# 4. 初始化 VNC 密码
###################################################
echo "=== [4/7] 初始化 VNC 密码 ==="
# 创建 .vnc 目录
sudo -u "$VNC_USER" mkdir -p /home/"$VNC_USER"/.vnc

# 使用 vncpasswd -f 将明文密码转换为 VNC 加密密码
sudo -u "$VNC_USER" bash -c "echo '$VNC_PASSWORD' | vncpasswd -f > /home/$VNC_USER/.vnc/passwd"
sudo chmod 600 /home/"$VNC_USER"/.vnc/passwd

###################################################
# 5. 创建 xstartup 脚本
###################################################
echo "=== [5/7] 创建 xstartup 脚本 (启动 Xfce) ==="
cat << 'EOF' | sudo -u "$VNC_USER" tee /home/"$VNC_USER"/.vnc/xstartup >/dev/null
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
EOF

sudo chmod +x /home/"$VNC_USER"/.vnc/xstartup

###################################################
# 6. 创建并配置 systemd 服务文件
###################################################
echo "=== [6/7] 创建 systemd 服务文件: vncserver@${VNC_USER}.service ==="
sudo bash -c "cat > /etc/systemd/system/vncserver@${VNC_USER}.service" << EOT
[Unit]
Description=VNC Service for user ${VNC_USER}
After=syslog.target network.target

[Service]
Type=forking
User=${VNC_USER}
Group=${VNC_USER}
WorkingDirectory=/home/${VNC_USER}

# PID 文件名字里仍然用 :${VNC_DISPLAY}，仅与 display 编号对应
PIDFile=/home/${VNC_USER}/.vnc/%H:${VNC_DISPLAY}.pid

# 启动前先尝试 kill（若未运行则忽略错误）
ExecStartPre=-/usr/bin/vncserver -kill :${VNC_DISPLAY} > /dev/null 2>&1

# 指定 -rfbport 为自定义端口(25931)，display 编号为 :1
ExecStart=/usr/bin/vncserver \
    -depth 24 -geometry 1280x800 \
    -rfbport ${VNC_RFBPORT} :${VNC_DISPLAY}

ExecStop=/usr/bin/vncserver -kill :${VNC_DISPLAY}

[Install]
WantedBy=multi-user.target
EOT

###################################################
# 7. 启动并设置开机自启
###################################################
echo "=== [7/7] 启动并设置开机自启 VNC 服务 ==="
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
