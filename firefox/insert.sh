
#########################
# 检查并配置 geckodriver
#########################
# 设置 geckodriver 版本
GECKO_VERSION="0.36.0"
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

