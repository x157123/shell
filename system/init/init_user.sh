#!/usr/bin/env bash

# 使用示例：
#   bash create_user.sh <username> <password>
# 若需要使新用户拥有 sudo 权限，取消下面的 usermod -aG sudo 行的注释即可。

# 检查是否提供了用户名和密码
if [ $# -lt 2 ]; then
  echo "用法: $0 <username> <password>"
  exit 1
fi

USER="$1"
PASSWORD="$2"

# 检查用户是否已存在
if id "$USER" &>/dev/null; then
    echo "用户 $USER 已存在，跳过创建步骤"
else
    echo "创建用户 $USER"
    # 创建用户，指定默认 shell 为 /bin/bash 并建立 home 目录
    useradd -m -s /bin/bash "$USER"

    # 设置密码
    echo "$USER:$PASSWORD" | chpasswd

    # 如果需要让此用户可使用 sudo，则取消下面一行的注释
    # usermod -aG sudo "$USER"

    echo "用户 $USER 创建完成，并已设置密码。"
fi

