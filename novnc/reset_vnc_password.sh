#!/bin/bash

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
