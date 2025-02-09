#!/bin/bash
# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:s:a: --long user:,password:,serverId:,appId: -n 'startfirefox.sh' -- "$@")
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

#########################
# 检查并安装 selenium
#########################
if pip3 show selenium > /dev/null 2>&1; then
    echo "selenium 已安装，跳过安装步骤。"
else
    echo "selenium 未安装，开始安装..."
    pip3 install selenium
fi

#########################
# 检查并配置 geckodriver
#########################
# 设置 geckodriver 版本
GECKO_VERSION="0.35.0"
FILE_NAME="geckodriver-v${GECKO_VERSION}-linux64.tar.gz"
DOWNLOAD_URL="https://github.com/mozilla/geckodriver/releases/download/v${GECKO_VERSION}/${FILE_NAME}"

if [ -x /usr/local/bin/geckodriver ]; then
    echo "geckodriver 已存在，跳过下载和配置步骤。"
else
    echo "正在下载 geckodriver 版本 ${GECKO_VERSION}..."
    wget "${DOWNLOAD_URL}"
    
    if [ ! -f "${FILE_NAME}" ]; then
        echo "下载 ${FILE_NAME} 失败，请检查网络连接或 URL 是否正确。"
        exit 1
    fi

    echo "正在解压 ${FILE_NAME}..."
    tar -xvf "${FILE_NAME}"

    echo "将解压后的 geckodriver 移动到 /usr/local/bin 并添加执行权限..."
    sudo mv geckodriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/geckodriver

    echo "验证 geckodriver 是否安装成功："
    geckodriver --version
fi

# 如果 /opt/firefox.py 存在，则先删除旧文件
if [ -f /opt/firefox.py ]; then
    echo "/opt/firefox.py 已存在，正在删除旧文件..."
    rm -f /opt/firefox.py
fi

# 下载并执行远程 Python 脚本
echo "开始下载脚本：https://www.15712345.xyz/yml/prod/firefox.py ..."
wget -O /opt/firefox.py https://www.15712345.xyz/yml/prod/firefox.py
if [ ! -f /opt/firefox.py ]; then
    echo "脚本下载失败，请检查网络连接或 URL 是否正确。"
    exit 1
fi

echo "为 /opt/firefox.py 设置可执行权限..."
chmod +x /opt/firefox.py

# 如果用户传了 --user，则将文件属主改为该用户，同时后续用该用户执行
if [ -n "$USER" ]; then
    chown "$USER":"$USER" /opt/firefox.py
fi


# 以特定用户启动 firefox
# 如果未指定 --user，则默认用 admin（或你想要的其它用户）
SUDO_USER="${USER:-admin}"

sudo -u "$SUDO_USER" -i bash <<'EOF'
# 内部脚本：用以特定用户的身份执行


# 设置 DISPLAY 环境变量（假设在 :1），根据实际情况修改
export DISPLAY=:1


# 执行远程 Python 脚本
echo "开始执行 /opt/firefox.py ..."
# 若需要脚本以该用户身份执行，使用 sudo -u。如果 python3 路径不一致，可改为绝对路径
nohup sudo -u "$SUDO_USER" -i python3 /opt/firefox.py --serverId "$SERVER_ID" --appId "$APP_ID" > firefoxOutput.log 2>&1 &

echo "脚本已在后台执行，日志输出至 firefoxOutput.log"

EOF

