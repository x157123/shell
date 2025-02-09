#!/usr/bin/env bash
#
# 用途：使用当前具有 sudo 权限的用户来初始化/修改 root 密码，
#       并允许 root 使用密码远程登录。

# 1. 判断是否传入了 root 新密码
if [ $# -ne 1 ]; then
    echo "用法: $0 <new-root-password>"
    exit 1
fi

NEW_ROOT_PASS="$1"

# 2. 设置 root 密码
echo "正在设置 root 密码为：$NEW_ROOT_PASS"
# 这里使用 chpasswd，等效方式也可以用 `passwd`，示例如下:
#  echo -e "$NEW_ROOT_PASS\n$NEW_ROOT_PASS" | sudo passwd root
# 但 chpasswd 更简洁
echo "root:${NEW_ROOT_PASS}" | sudo chpasswd
if [ $? -ne 0 ]; then
    echo "设置 root 密码失败，请检查当前用户是否拥有 sudo 权限。"
    exit 1
fi

# 3. 修改 SSH 配置文件：PermitRootLogin 和 PasswordAuthentication
echo "修改 /etc/ssh/sshd_config，允许 root 使用密码登录..."
sudo sed -i 's/^\(#\)\?\(PermitRootLogin\).*/PermitRootLogin yes/g' /etc/ssh/sshd_config
sudo sed -i 's/^\(#\)\?\(PasswordAuthentication\).*/PasswordAuthentication yes/g' /etc/ssh/sshd_config

# 4. 重启 SSH 服务
echo "重启 SSH 服务..."
sudo systemctl restart ssh

# 5. 提示信息
echo "----------------------------------------------"
echo "已将 root 密码重置为：$NEW_ROOT_PASS"
echo "并已启用 SSH 密码登录 (root)。"
echo "警告：此举存在较大安全风险，请务必谨慎使用。"
echo "----------------------------------------------"
