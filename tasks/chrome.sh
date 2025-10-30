#!/bin/bash

# 默认值
USER="ubuntu"
PASSWORD="Mmscm716+"
readonly CHROME_DEB="google-chrome-stable_current_amd64.deb"
#readonly CHROME_URL_OLD="https://github.com/x157123/ACL4SSR/releases/download/chro/google-chrome-stable_120.0.6099.224-1_amd64.deb"
readonly CHROME_URL_OLD="https://github.com/x157123/ACL4SSR/releases/download/v.1.0.15/google-chrome-stable_126.0.6478.126-1_amd64.deb"

# 错误处理函数
error_exit() {
    echo "ERROR: $1" >&2
    exit 1
}

# 日志函数
log_info() {
    echo "[INFO] $1"
}


# 检查端口是否在监听，返回 0 表示已监听，1 表示未监听
check_port() {
    local port=$1
    if lsof -i:$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_info "端口 $port 已在监听"
        return 0
    else
        log_info "端口 $port 未监听"
        return 1
    fi
}

install_chrome_120(){
    if ! dpkg-query -W google-chrome-stable >/dev/null 2>&1; then
        log_info "安装 Google Chrome..."
        wget -q -O "$CHROME_DEB" "$CHROME_URL_OLD" || error_exit "浏览器下载失败"
        sudo dpkg -i "$CHROME_DEB" || sudo apt-get install -f -y || error_exit "Google Chrome 安装失败"
        rm -f "$CHROME_DEB"
        sudo apt-mark hold google-chrome-stable
        log_info "Google Chrome 安装完成"

    else
        log_info "Google Chrome 已安装，跳过"
    fi
}

# 检查并安装 VNC
setup_vnc() {

    if ! command -v tightvncserver >/dev/null 2>&1; then
        log_info "tightvncserver 未安装，开始安装 VNC 及其依赖..."
        sudo apt-get install -y xfce4 xfce4-goodies tightvncserver xrdp expect sudo || error_exit "VNC 相关组件安装失败"
        log_info "VNC 安装完成"
    else
        log_info "tightvncserver 已安装，跳过安装"
    fi

    id "$USER" >/dev/null 2>&1 || {
        log_info "创建用户 $USER ..."
        useradd -m -s /bin/bash "$USER"
        echo "$USER:$PASSWORD" | chpasswd
    }

    # 检查 VNC 是否运行（改进匹配模式）
    if pgrep -f "Xtightvnc :$VNC_DISPLAY" >/dev/null && check_port "$VNC_PORT"; then
        log_info "VNC 显示号 :$VNC_DISPLAY 已运行且端口 $VNC_PORT 在监听，跳过启动"
    else
        log_info "VNC 未运行或端口 $VNC_PORT 未监听，重新启动..."
        # 清理旧进程
        pgrep -f "Xtightvnc :$VNC_DISPLAY" >/dev/null && {
            log_info "终止旧 VNC 进程..."
            tightvncserver -kill :$VNC_DISPLAY 2>/dev/null || true
        }
        # 将必要变量传递进 sudo 环境
        sudo -u "$USER" VNC_PASS="$PASSWORD" VNC_REAL_PORT="$VNC_PORT" VNC_REAL_DISPLAY="$VNC_DISPLAY" bash <<'INNEREOF'
        # 在这里引用外层传来的 VNC_PASS 和 VNC_REAL_PORT

        # 确保 ~/.vnc 文件夹存在，并设置正确权限
        mkdir -p "$HOME/.vnc"
        chmod 700 "$HOME/.vnc"

        # 构造 expect 脚本，用于初始化 VNC 密码
        EXPECT_SCRIPT=$(cat <<EOL
spawn tightvncserver :${VNC_REAL_DISPLAY} -rfbport ${VNC_REAL_PORT}
expect "Password:"
send "${VNC_PASS}\r"
expect "Verify:"
send "${VNC_PASS}\r"
expect "Would you like to enter a view-only password (y/n)?"
send "n\r"
expect eof
EOL
)
  sleep 2
  # 如果 VNC 服务器已经启动，先关闭以免重复配置
  tightvncserver -kill :${VNC_REAL_DISPLAY} >/dev/null 2>&1 || true
  sleep 2
  # 使用 expect 脚本自动输入密码（避免人工干预）
  expect -c "$EXPECT_SCRIPT"

  # 写入 xstartup 脚本，启动 Xfce4
  cat > "$HOME/.vnc/xstartup" <<'XSTARTUP'
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
XSTARTUP

  chmod +x "$HOME/.vnc/xstartup"

  # 为了确保 xstartup 配置生效，先关闭已有的 VNC 会话（如果有的话）
  tightvncserver -kill :${VNC_REAL_DISPLAY} >/dev/null 2>&1 || true

  # 最终启动 VNC 服务器，指定显示号、端口、分辨率和颜色深度
  tightvncserver :${VNC_REAL_DISPLAY} -rfbport ${VNC_REAL_PORT} -geometry 1920x1080 -depth 24
INNEREOF

    fi
}

install_wallet_phantom() {
  # 目录路径
  DIR="/home/$USER/extensions/phantom"
  # 文件下载地址
  TARGET_DIR="/home/$USER/extensions/"

#  if [ -d "$DIR" ]; then
#    log_info "钱包目录 $DIR 已存在，准备删除。"
#    rm -rf "$DIR"
#  fi

  # 判断目录是否存在
  if [ ! -d "$DIR" ]; then
    # 目录不存在，创建目录
    mkdir -p "$TARGET_DIR"
    log_info "钱包目录 $TARGET_DIR 已创建。"

    wget -q -O /tmp/phantom.tar "https://github.com/x157123/ACL4SSR/releases/download/v.1.0.8/phantom.tar" || error_exit "钱包下载失败"

    # 解压文件
    log_info "解压文件..."
    tar -xvf /tmp/phantom.tar -C "$TARGET_DIR"

    # 删除下载的 tar 文件
    rm /tmp/phantom.tar

    # 授权给 指定 用户
    log_info "授权目录 $DIR 给 $USER 用户..."
    chown -R "$USER":"$USER" "$DIR"

    log_info "授权完成。"

  fi
}


down_desc() {
    # 定义文件路径和下载URL的数组
    declare -A files=(
        ["/home/$USER/task/tasks/image_descriptions.txt"]="https://github.com/x157123/ACL4SSR/releases/download/v.1.0.11/image_descriptions.txt"
        ["/home/$USER/task/tasks/questions.txt"]="https://github.com/x157123/ACL4SSR/releases/download/v.1.0.12/questions.txt"
        ["/home/$USER/task/tasks/twitter_positive_replies.txt"]="https://github.com/x157123/ACL4SSR/releases/download/v.1.0.16/twitter_positive_replies.txt"
    )

    # 遍历所有文件
    for FILE_PATH in "${!files[@]}"; do
        URL="${files[$FILE_PATH]}"

        # 检查文件是否存在
        if [ -f "$FILE_PATH" ]; then
            log_info "文件已存在,跳过下载: $FILE_PATH"
        else
            log_info "文件不存在,开始下载: $FILE_PATH"

            # 确保父目录存在
            DIR_PARENT=$(dirname "$FILE_PATH")
            mkdir -p "$DIR_PARENT"

            # 下载文件
            wget -q -O "$FILE_PATH" "$URL" || error_exit "文件下载失败: $FILE_PATH"
            log_info "下载完成: $FILE_PATH"
        fi

        # 授权给指定用户
        log_info "授权文件 $FILE_PATH 给 $USER 用户..."
        chown "$USER":"$USER" "$FILE_PATH"
    done

    log_info "所有文件处理完成。"
}


install_wallet_dog() {
  # 目录路径
  DIR="/home/$USER/extensions/chrome-cloud"
  # 文件下载地址
  TARGET_DIR="/home/$USER/extensions/"

#  if [ -d "$DIR" ]; then
#    log_info "钱包目录 $DIR 已存在，准备删除。"
#    rm -rf "$DIR"
#  fi

  # 判断目录是否存在
  if [ ! -d "$DIR" ]; then
    # 目录不存在，创建目录
    mkdir -p "$TARGET_DIR"
    log_info "钱包目录 $TARGET_DIR 已创建。"

    wget -q -O /tmp/chrome-cloud.tar "https://github.com/x157123/ACL4SSR/releases/download/v.1.0.13/chrome-cloud.tar" || error_exit "钱包下载失败"

    # 解压文件
    log_info "解压文件..."
    tar -xvf /tmp/chrome-cloud.tar -C "$TARGET_DIR"

    # 删除下载的 tar 文件
    rm /tmp/chrome-cloud.tar

    # 授权给 指定 用户
    log_info "授权目录 $DIR 给 $USER 用户..."
    chown -R "$USER":"$USER" "$DIR"

    log_info "授权完成。"

  fi
}


install_edit_cookies() {
  # 目录路径
  DIR="/home/$USER/extensions/edit-cookies"
  # 文件下载地址
  TARGET_DIR="/home/$USER/extensions/"

#  if [ -d "$DIR" ]; then
#    log_info "钱包目录 $DIR 已存在，准备删除。"
#    rm -rf "$DIR"
#  fi

  # 判断目录是否存在
  if [ ! -d "$DIR" ]; then
    # 目录不存在，创建目录
    mkdir -p "$TARGET_DIR"
    log_info "钱包目录 $TARGET_DIR 已创建。"

    wget -q -O /tmp/edit-cookies.tar "https://github.com/x157123/ACL4SSR/releases/download/v.1.0.17/edit-cookies.tar" || error_exit "钱包下载失败"

    # 解压文件
    log_info "解压文件..."
    tar -xvf /tmp/edit-cookies.tar -C "$TARGET_DIR"

    # 删除下载的 tar 文件
    rm /tmp/edit-cookies.tar

    # 授权给 指定 用户
    log_info "授权目录 $DIR 给 $USER 用户..."
    chown -R "$USER":"$USER" "$DIR"

    log_info "授权完成。"

  fi
}




# 配置 XRDP
setup_xrdp() {
    log_info "配置 XRDP..."
    echo "startxfce4" > "/home/$USER/.xsession"
    chown "$USER:$USER" "/home/$USER/.xsession"
    if ! service xrdp status | grep -q "running"; then
        log_info "XRDP 未运行，启动服务..."
        service xrdp start || error_exit "XRDP 启动失败"
    fi
    log_info "XRDP 配置完成"
}

stop_services(){
    # 检查并清理特定 Chrome 调试端口
    PIDS=$(lsof -t -i:29541 -sTCP:LISTEN)
    if [ -n "$PIDS" ]; then
        log_info "29541 端口已被占用，终止占用该端口的进程：$PIDS"
        kill -9 "$PIDS"
        sleep 1
    fi
}


# 主执行流程
main() {
    # 必须以 root 运行
	if [ "$(id -u)" -ne 0 ]; then
		error_exit "此脚本需要以 root 权限运行，请使用 sudo 或以 root 用户执行"
	fi

  # 停止服务
	stop_services

  sudo mv /etc/apt/sources.list.d/google-chrome.list /etc/apt/sources.list.d/google-chrome.list.bak

	mkdir -p "/home/ubuntu/task/tasks/img"
  chown -R "$USER":"$USER" "/home/ubuntu/task/tasks/img"

  down_desc
	# 更新软件源并安装 Python 运行时及虚拟环境支持
	apt-get update \
		&& apt-get install -y \
		  fontconfig \
		  fonts-wqy-zenhei \
		  fonts-wqy-microhei \
			python3-pip \
			python3-venv \
			python3-tk \
			python3-dev \
			xclip \
		|| error_exit "Python 组件安装失败"

	# 升级 pip 并安装依赖包
	pip install --upgrade pip \
		|| error_exit "升级 pip 失败"
	pip install \
		pyautogui \
		drissionpage \
		pyperclip \
		web3 \
		loguru \
		|| error_exit "Python 包安装失败"

  install_chrome_120

  # 安装钱包
  install_wallet_dog
  install_wallet_phantom
  install_edit_cookies

  # 循环创建 :23 到 :27 的 VNC 会话
  for display in {23..25}; do
      port=$((5900 + display))
      log_info "=== 启动 VNC 会话 :$display (端口 $port) ==="
      VNC_DISPLAY="$display" VNC_PORT="$port" setup_vnc
  done

  # 配置并启动 XRDP（所有会话共用）
  setup_xrdp
}

main "$@"