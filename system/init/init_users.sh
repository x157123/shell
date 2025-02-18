#!/bin/bash
# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""
DECRYPT_KEY=""
# 默认 VNC 端口
VNC_PORT=5923   # 在此可自定义要使用的 VNC 端口

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:k:s:a: --long user:,password:,decryptKey:,serverId:,appId: -n 'startChrome.sh' -- "$@")
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
        -k|--decryptKey)
            DECRYPT_KEY=$2
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


# 检查用户是否已存在
if id "$USER" &>/dev/null; then
    echo "用户 $USER 已存在，更新密码..."
    echo "$USER:$PASSWORD" | chpasswd
    echo "用户 $USER 的密码已更新。"
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

