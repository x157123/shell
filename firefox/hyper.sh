#!/bin/bash
# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""
DECRYPT_KEY=""

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:k:s:a: --long user:,password:,decryptKey:,serverId:,appId: -n 'startfirefox.sh' -- "$@")
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

pip3 install pycryptodome

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


# 如果 /opt/hyper.py 存在，则先删除旧文件
if [ -f /opt/hyper.py ]; then
    echo "/opt/hyper.py 已存在，正在删除旧文件..."
    rm -f /opt/hyper.py
fi

# 下载并执行远程 Python 脚本
echo "开始下载脚本：https://www.15712345.xyz/shell/firefox/hyper.py ..."
wget -O /opt/hyper.py https://www.15712345.xyz/shell/firefox/hyper.py
if [ ! -f /opt/hyper.py ]; then
    echo "脚本下载失败，请检查网络连接或 URL 是否正确。"
    exit 1
fi


#########################
# 检查并安装 Firefox 浏览器
#########################
if command -v firefox >/dev/null 2>&1; then
    echo "检测到 Firefox 浏览器已安装，跳过安装步骤。"
else
    echo "未检测到 Firefox 浏览器，开始安装..."

    # 移除可能安装的 snap 版 Firefox（忽略错误）
    sudo snap remove --purge firefox || true

    # ---------------------------
    # 1. 配置 GPG 密钥相关信息（自动生成，无需交互）
    # ---------------------------
    # 根据需要修改下面变量的值
    GPG_REAL_NAME="Your Name"
    GPG_EMAIL="your.email@example.com"
    GPG_PASSPHRASE="yourpassphrase"

    if gpg --list-keys "$GPG_EMAIL" 2>/dev/null | grep -q "$GPG_EMAIL"; then
        echo "检测到已有 GPG 密钥（邮箱: $GPG_EMAIL），跳过生成步骤。"
    else
        echo "未检测到 GPG 密钥，开始自动生成..."
        GPG_BATCH_FILE=$(mktemp)
        cat > "$GPG_BATCH_FILE" <<EOF
%echo Generating a basic OpenPGP key
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: ${GPG_REAL_NAME}
Name-Email: ${GPG_EMAIL}
Expire-Date: 0
Passphrase: ${GPG_PASSPHRASE}
%commit
%echo done
EOF
        gpg --batch --yes --gen-key "$GPG_BATCH_FILE"
        rm -f "$GPG_BATCH_FILE"
        echo "GPG 密钥生成完成。"
    fi

    # ---------------------------
    # 2. 导入 Mozilla 仓库的密钥
    # ---------------------------
    echo "导入 Mozilla 仓库的密钥..."
    sudo mkdir -p /etc/apt/keyrings
    wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg -O- | sudo tee /etc/apt/keyrings/packages.mozilla.org.asc > /dev/null

    echo "验证导入的密钥指纹："
    gpg -n -q --import --import-options import-show /etc/apt/keyrings/packages.mozilla.org.asc | \
      awk '/pub/{getline; gsub(/^ +| +$/,""); print "\n"$0"\n"}'

    # ---------------------------
    # 3. 添加 Mozilla 仓库
    # ---------------------------
    echo "添加 Mozilla 仓库..."
    echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" | \
      sudo tee /etc/apt/sources.list.d/mozilla.list > /dev/null

    # ---------------------------
    # 4. 提升 Mozilla 仓库优先级
    # ---------------------------
    echo "提升 Mozilla 仓库优先级..."
    sudo tee /etc/apt/preferences.d/mozilla > /dev/null <<EOF
Package: *
Pin: origin packages.mozilla.org
Pin-Priority: 1000
EOF

    # 再次移除可能的 snap 版 Firefox
    sudo snap remove firefox || true

    # ---------------------------
    # 5. 更新软件源并安装 Firefox
    # ---------------------------
    echo "更新软件源..."
    sudo apt update

    echo "安装 Firefox（Deb 版本）..."
    sudo apt install -y firefox

    echo "Firefox 安装成功！"
fi



echo "为 /opt/hyper.py 设置可执行权限..."
chmod +x /opt/hyper.py

# 如果用户传了 --user，则将文件属主改为该用户，同时后续用该用户执行
if [ -n "$USER" ]; then
    chown "$USER":"$USER" /opt/hyper.py
fi

# 查找 /opt/hyper.py 进程
pid=$(pgrep -f "python3 /opt/hyper.py")
if [ -n "$pid" ]; then
    # 获取进程组ID（PGID），去除前后空格
    pgid=$(ps -o pgid= "$pid" | tr -d ' ')
    echo "杀掉进程组 PGID: $pgid (PID: $pid)"
    # 杀掉整个进程组（注意负号表示进程组）
    kill -9 -"$pgid"
else
    echo "没有找到 /opt/hyper.py 进程"
fi

## 终止GeckoDriver进程
#if pkill -f geckodriver; then
#    echo "已终止GeckoDriver进程"
#fi
#
## 终止Firefox进程
#if pkill -f firefox; then
#    echo "已终止Firefox进程"
#fi

# 以特定用户启动 hyper
# 如果未指定 --user，则默认用 admin（或你想要的其它用户）
SUDO_USER="${USER:-admin}"

sudo -u "$SUDO_USER" -i bash <<EOF
# 内部脚本：用以特定用户的身份执行

# 设置 DISPLAY 环境变量（假设在 :1），根据实际情况修改
export DISPLAY=:1

# 执行远程 Python 脚本
echo "开始执行 /opt/hyper.py ..."
# 若需要脚本以该用户身份执行，使用 sudo -u。如果 python3 路径不一致，可改为绝对路径
nohup setsid python3 /opt/hyper.py --serverId "$SERVER_ID" --appId "$APP_ID" --decryptKey "$DECRYPT_KEY" > hyperOutput.log 2>&1 &

echo "脚本已在后台执行，日志输出至 /home/$SUDO_USER/hyperOutput.log"

EOF

echo -e "\n"
