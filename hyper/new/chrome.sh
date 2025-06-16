#!/bin/bash

# 脚本描述: 用于配置和管理 Chrome 浏览器的自动化环境，支持多实例 VNC 配置和动态端口

# 常量定义
readonly APT_PACKAGES=("net-tools" "fontconfig" "fonts-wqy-zenhei" "fonts-wqy-microhei" "lsof" "python3-tk" "python3-dev" "libu2f-udev" "expect")  # 添加 lsof
readonly PYTHON_PACKAGES=("psutil" "requests" "paho-mqtt" "selenium" "pycryptodome" "loguru" "pyperclip" "drissionpage" "pyautogui")
readonly DEPENDENCIES=("curl" "wget" "git" "pip3" "lsof" "expect")  # 依赖命令
readonly DEFAULT_VNC_DISPLAY=26       # 默认显示号

# 默认值
USER="${USER:-admin}"
PASSWORD="${PASSWORD:-Mmscm716+}"
VNC_DISPLAY="${VNC_DISPLAY:-$DEFAULT_VNC_DISPLAY}"

# 错误处理函数
error_exit() {
    echo "ERROR: $1" >&2
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

# 检查依赖命令
check_dependencies() {
    for dep in "${DEPENDENCIES[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            error_exit "缺少依赖命令: $dep，请先安装"
        fi
    done
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

# 检查 Python 包是否已安装
check_python_package() {
    local package=$1
    if pip3 show "$package" >/dev/null 2>&1; then
        log_info "Python 包 $package 已安装，跳过"
        return 0
    else
        return 1
    fi
}

# 安装 Python 包
install_python_packages() {
    local to_install=()
    for pkg in "${PYTHON_PACKAGES[@]}"; do
        if ! check_python_package "$pkg"; then
            to_install+=("$pkg")
        fi
    done
    if [ ${#to_install[@]} -gt 0 ]; then
        log_info "安装未检测到的 Python 包: ${to_install[*]}"
        pip3 install -q "${to_install[@]}" || error_exit "Python 包安装失败"
        log_info "Python 包安装完成"
    else
        log_info "所有 Python 包已安装，跳过安装"
    fi
}

# 检查系统包是否已安装
check_apt_package() {
    local package=$1
    if dpkg-query -W "$package" >/dev/null 2>&1; then
        log_info "系统包 $package 已安装，跳过"
        return 0
    else
        return 1
    fi
}

# 安装系统包
install_apt_packages() {
    local to_install=()
    for pkg in "${APT_PACKAGES[@]}"; do
        if ! check_apt_package "$pkg"; then
            to_install+=("$pkg")
        fi
    done
    if [ ${#to_install[@]} -gt 0 ]; then
        log_info "安装未检测到的系统包: ${to_install[*]}"
        sudo apt-get install -y "${to_install[@]}" || error_exit "系统包安装失败"
        log_info "系统包安装完成"
    else
        log_info "所有系统包已安装，跳过安装"
    fi
}

# 更新系统包列表
update_system() {
    log_info "更新系统软件包列表..."
    # 屏蔽掉google浏览器
    sudo mv /etc/apt/sources.list.d/google-chrome.list /etc/apt/sources.list.d/google-chrome.list.bak
    sudo apt update -y || error_exit "软件包列表更新失败"
}

# 安装系统依赖
install_system_deps() {
    log_info "安装 xclip..."
    if ! command -v xclip >/dev/null 2>&1; then
        sudo apt-get install -y xclip || {
            log_info "xclip 安装失败，尝试更换镜像源..."
            sudo tee /etc/apt/sources.list > /dev/null <<'EOL'
deb https://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-backports main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal-backports main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
EOL
            sudo apt-get update -y && sudo apt-get install -y xclip || error_exit "xclip 安装失败，即使更换源后仍未成功"
        }
        log_info "xclip 安装成功"
    else
        log_info "xclip 已安装，跳过"
    fi

    export DEBIAN_FRONTEND=noninteractive
    install_apt_packages

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
        mkdir -p "/home/ubuntu/vnc/.vnc"
        chmod 700 "/home/ubuntu/vnc/.vnc"

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
  cat > "/home/ubuntu/vnc/.vnc/xstartup" <<'XSTARTUP'
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
XSTARTUP

  chmod +x "/home/ubuntu/vnc/.vnc/xstartup"

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

    update_system
    install_system_deps
    check_dependencies
    setup_vnc
    setup_xrdp
    install_python_packages
}

main "$@"