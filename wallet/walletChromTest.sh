#!/bin/bash

# 脚本描述: 用于配置和管理 Chrome 浏览器的自动化环境，支持多实例 VNC 配置和动态端口

# 常量定义
readonly APT_PACKAGES=("net-tools" "fontconfig" "fonts-wqy-zenhei" "fonts-wqy-microhei" "lsof" "python3-tk" "python3-dev" "libu2f-udev" "expect")  # 添加 lsof
readonly PYTHON_PACKAGES=("psutil" "requests" "paho-mqtt" "selenium" "pycryptodome" "loguru" "pyperclip" "drissionpage" "pyautogui")
readonly DEPENDENCIES=("curl" "wget" "git" "pip3" "lsof" "expect")  # 依赖命令
readonly CHROME_DEB="google-chrome-stable_current_amd64.deb"
readonly CHROME_URL="https://dl.google.com/linux/direct/$CHROME_DEB"
readonly CHROME_BAK_URL="https://www.15712345.xyz/chrome/$CHROME_DEB"
readonly CHROME_URL_OLD="https://github.com/x157123/ACL4SSR/releases/download/chro/google-chrome-stable_120.0.6099.224-1_amd64.deb"
readonly WALLET_URL="https://github.com/x157123/ACL4SSR/releases/download/v1.0.0/chrome-cloud.tar"
readonly EDGE_URL="https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_133.0.3065.82-1_amd64.deb?brand=M102"
readonly PYTHON_SCRIPT_DIR="/opt/"  # 目录
readonly DEFAULT_VNC_DISPLAY=23       # 默认显示号
readonly VNC_BASE_PORT=5900           # VNC 基础端口
readonly NOVNC_BASE_PORT=26300        # noVNC 基础端口
readonly CHROME_DEBUG_BASE_PORT=9515  # Chrome 调试基础端口

# 默认值
USER="${USER:-admin}"
PASSWORD="${PASSWORD:-default_password}"
SERVER_ID=""
APP_ID=""
DECRYPT_KEY="${DECRYPT_KEY:-default_password}"
VNC_DISPLAY="${VNC_DISPLAY:-$DEFAULT_VNC_DISPLAY}"
FILE_NAME=""
PYTHON_SCRIPT_URL=""

# 错误处理函数
error_exit() {
    echo "ERROR: $1" >&2
    # 清理临时文件
    [ -f "$CHROME_DEB" ] && rm -f "$CHROME_DEB"
    exit 1
}

# 日志函数
log_info() {
    echo "[INFO] $1"
}

# 检查命令是否成功
check_command() {
    if [ $? -ne 0 ]; then
        error_exit "$1"
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



# 主执行流程
main() {
    if [ "$(id -u)" -ne 0 ]; then
        error_exit "此脚本需要 root 权限运行，请使用 sudo 或以 root 用户执行"
    fi

    setup_vnc
    setup_xrdp

}

main "$@"