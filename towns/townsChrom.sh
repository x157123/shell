#!/bin/bash

# 脚本描述: 用于配置和管理 Chrome 浏览器的自动化环境，支持多实例 VNC 配置和动态端口

# 常量定义
readonly APT_PACKAGES=("net-tools" "fontconfig" "fonts-wqy-zenhei" "fonts-wqy-microhei" "lsof" "python3-tk" "python3-dev" "libu2f-udev" "expect")  # 添加 lsof
readonly PYTHON_PACKAGES=("psutil" "requests" "paho-mqtt" "selenium" "pycryptodome" "loguru" "pyperclip" "drissionpage" "pyautogui")
readonly DEPENDENCIES=("curl" "wget" "git" "pip3" "lsof" "expect")  # 依赖命令
readonly CHROME_DEB="google-chrome-stable_current_amd64.deb"
readonly CHROME_URL="https://dl.google.com/linux/direct/$CHROME_DEB"
readonly CHROME_BAK_URL="https://www.15712345.xyz/chrome/$CHROME_DEB"
readonly DOWN_IMG="https://img95.699pic.com/element/40204/2110.png_300.png"
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

# 解析命令行参数
parse_args() {
    TEMP=$(getopt -o u:p:k:s:a:d:f:py: --long user:,password:,decryptKey:,serverId:,appId:,vncDisplay:,fileName:,pythonUrl: -n "$0" -- "$@") || error_exit "选项解析失败"
    eval set -- "$TEMP"
    while true; do
        case "$1" in
            -u|--user) USER="$2"; shift 2 ;;
            -p|--password) PASSWORD="$2"; shift 2 ;;
            -k|--decryptKey) DECRYPT_KEY="$2"; shift 2 ;;
            -s|--serverId) SERVER_ID="$2"; shift 2 ;;
            -a|--appId) APP_ID="$2"; shift 2 ;;
            -d|--vncDisplay) VNC_DISPLAY="$2"; shift 2 ;;
            -f|--fileName) FILE_NAME="$2"; shift 2 ;;
            -py|--pythonUrl) PYTHON_SCRIPT_URL="$2"; shift 2 ;;
            --) shift; break ;;
            *) error_exit "内部错误: 未知选项 $1" ;;
        esac
    done

    # 参数验证
    [ -z "$SERVER_ID" ] || [ -z "$APP_ID" ] && error_exit "必须提供 --serverId 和 --appId 参数\n用法: $0 --serverId SERVER_ID --appId APP_ID [--user USER] [--password PASSWORD] [--vncDisplay DISPLAY]"
    [[ "$VNC_DISPLAY" =~ ^[0-9]+$ ]] || error_exit "VNC 显示号 (--vncDisplay) 必须为整数"

    # 计算动态端口
    VNC_PORT=$((VNC_BASE_PORT + VNC_DISPLAY))
    NOVNC_PORT=$((NOVNC_BASE_PORT + VNC_DISPLAY))
    CHROME_DEBUG_PORT=$((CHROME_DEBUG_BASE_PORT + VNC_DISPLAY))
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

# 安装 Google Chrome
install_chrome() {
    if ! dpkg-query -W google-chrome-stable >/dev/null 2>&1; then
        log_info "安装 Google Chrome..."
        if ! curl -sSL "$CHROME_URL" -o "$CHROME_DEB"; then
            log_info "主 URL 下载失败，尝试备用 URL..."
            curl -sSL "$CHROME_BAK_URL" -o "$CHROME_DEB" || error_exit "Google Chrome 下载失败，主 URL 和备用 URL 均不可用"
        fi
        sudo dpkg -i "$CHROME_DEB" || sudo apt-get install -f -y || error_exit "Google Chrome 安装失败"
        rm -f "$CHROME_DEB"
        log_info "Google Chrome 安装完成"
    else
        log_info "Google Chrome 已安装，跳过"
    fi
}

install_chrome_120(){
#    if dpkg-query -W google-chrome-stable >/dev/null 2>&1; then
#      log_info "卸载最新版本版本"
#      sudo dpkg --remove google-chrome-stable
#    fi
#    if ! curl -sSL "$CHROME_URL_OLD" -o "$CHROME_DEB"; then
#        log_info "URL 下载失败..."
#    fi
#    sudo dpkg -i "$CHROME_DEB" || sudo apt-get install -f -y || error_exit "Google Chrome 安装失败"
#    rm -f "$CHROME_DEB"
#    sudo apt-mark hold google-chrome-stable
#    log_info "Google Chrome 安装完成"
    if ! dpkg-query -W google-chrome-stable >/dev/null 2>&1; then
        log_info "安装 Google Chrome..."
        if ! curl -sSL "$CHROME_URL_OLD" -o "$CHROME_DEB"; then
            log_info "URL 下载失败..."
        fi
        sudo dpkg -i "$CHROME_DEB" || sudo apt-get install -f -y || error_exit "Google Chrome 安装失败"
        rm -f "$CHROME_DEB"
        sudo apt-mark hold google-chrome-stable
        log_info "Google Chrome 安装完成"
    else
        log_info "Google Chrome 已安装，跳过"
    fi
}

install_edge() {
    # 定义变量
    EDGE_DEB="microsoft-edge-stable.deb"
    # 检查是否已安装 Microsoft Edge
    if ! dpkg-query -W microsoft-edge-stable >/dev/null 2>&1; then
        log_info "安装 Microsoft Edge..."
        # 尝试从主 URL 下载
        if ! curl -sSL "$EDGE_URL" -o "$EDGE_DEB"; then
            log_info "URL 下载失败..."
        fi
        # 安装 .deb 文件，若失败则尝试修复依赖
        sudo dpkg -i "$EDGE_DEB" || sudo apt-get install -f -y || error_exit "Microsoft Edge 安装失败"
        # 清理临时文件
        rm -f "$EDGE_DEB"
        log_info "Microsoft Edge 安装完成"
    else
        log_info "Microsoft Edge 已安装，跳过"
    fi
}

install_wallet() {
  # 目录路径
  DIR="/home/$USER/extensions/chrome-cloud"
  DIRT="/home/$USER/extensions/chrome_cloud"
  # 文件下载地址
  TARGET_DIR="/home/$USER/extensions/"

  if [ -d "$DIR" ]; then
    log_info "钱包目录 $DIR 已存在，准备删除。"
    rm -rf "$DIR"
  fi

  # 判断目录是否存在
  if [ ! -d "$DIR" ]; then
    # 目录不存在，创建目录
    mkdir -p "$TARGET_DIR"
    log_info "钱包目录 $TARGET_DIR 已创建。"

    wget -q -O /tmp/chrome-cloud.tar "$WALLET_URL" || error_exit "钱包下载失败"

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
# 下载image
setup_img() {
    if [ ! -d "/home/ubuntu/img/" ]; then
        log_info "目录 /home/ubuntu/img/ 不存在，正在创建..."
        mkdir -p "/home/ubuntu/img/" || error_exit "无法创建目录 /home/ubuntu/img/"
        chown "$USER:$USER" "/home/ubuntu/img/"
    fi
    if [ -f "/home/ubuntu/img/img.png" ]; then
        log_info "/home/ubuntu/img/img.png 已存在，删除旧文件..."
        rm -f "/home/ubuntu/img/img.png"
    fi
    log_info "下载 Python 脚本..."
    wget -q -O "/home/ubuntu/img/img.png" "$DOWN_IMG" || error_exit "脚本下载失败"
    chown "$USER:$USER" "/home/ubuntu/img/img.png"
}

# 下载并配置 Python 脚本
setup_python_script() {
    if [ ! -d "$PYTHON_SCRIPT_DIR" ]; then
        log_info "目录 $PYTHON_SCRIPT_DIR 不存在，正在创建..."
        mkdir -p "$PYTHON_SCRIPT_DIR" || error_exit "无法创建目录 $PYTHON_SCRIPT_DIR"
        chown "$USER:$USER" "$PYTHON_SCRIPT_DIR"
    fi
    if [ -f "$PYTHON_SCRIPT_DIR$FILE_NAME" ]; then
        log_info "$PYTHON_SCRIPT_DIR$FILE_NAME 已存在，删除旧文件..."
        rm -f "$PYTHON_SCRIPT_DIR$FILE_NAME"
    fi
    log_info "下载 Python 脚本..."
    wget -q -O "$PYTHON_SCRIPT_DIR$FILE_NAME" "$PYTHON_SCRIPT_URL" || error_exit "脚本下载失败"
    chmod +x "$PYTHON_SCRIPT_DIR$FILE_NAME"
    chown "$USER:$USER" "$PYTHON_SCRIPT_DIR$FILE_NAME"
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

# 配置 noVNC
setup_novnc() {
    if [ ! -d "noVNC" ]; then
        log_info "安装 noVNC..."
        git clone https://github.com/novnc/noVNC.git || error_exit "noVNC 下载失败"
    fi

    NOVNC_PID_FILE="novnc_$VNC_DISPLAY.pid"
    # 检查 noVNC 是否运行且端口已监听
    if [ -f "$NOVNC_PID_FILE" ] && kill -0 "$(cat "$NOVNC_PID_FILE")" 2>/dev/null && check_port "$NOVNC_PORT"; then
        log_info "noVNC 已运行且端口 $NOVNC_PORT 在监听，跳过启动"
    else
        # 清理旧进程
        if [ -f "$NOVNC_PID_FILE" ]; then
            log_info "终止旧 noVNC 进程..."
            kill "$(cat "$NOVNC_PID_FILE")" 2>/dev/null || true
            rm -f "$NOVNC_PID_FILE"
        fi

        # 启动 noVNC
        log_info "启动 noVNC，监听端口 $NOVNC_PORT..."
        nohup ./noVNC/utils/novnc_proxy \
            --vnc localhost:$VNC_PORT \
            --listen "$NOVNC_PORT" &>> "novnc_$VNC_DISPLAY.log" & echo $! > "$NOVNC_PID_FILE"
        sleep 2  # 等待启动完成
        check_port "$NOVNC_PORT" || error_exit "noVNC 启动失败，端口 $NOVNC_PORT 未监听"
        log_info "noVNC 已启动，监听端口 $NOVNC_PORT，日志追加到 novnc_$VNC_DISPLAY.log"
    fi
}

stop_services(){
    # 检查并清理特定 Chrome 调试端口
    PIDS=$(lsof -t -i:$CHROME_DEBUG_PORT -sTCP:LISTEN)
    if [ -n "$PIDS" ]; then
        log_info "$CHROME_DEBUG_PORT 端口已被占用，终止占用该端口的进程：$PIDS"
        kill -9 "$PIDS"
        sleep 1
    fi


    # 查找运行中的 关闭 nexus
    pids=$(pgrep -f "/opt/nexus_chrom")
    if [ -n "$pids" ]; then
        echo "检测到正在运行的实例: $pids，准备终止..."
        for pid in $pids; do
            kill -9 "$pid"
            echo "已终止 PID: $pid"
        done
    fi

    # 查找运行中的 去除python进程
    pids=$(pgrep -f "$PYTHON_SCRIPT_DIR$FILE_NAME")
    if [ -n "$pids" ]; then
        echo "检测到正在运行的实例: $pids，准备终止..."
        for pid in $pids; do
            kill -9 "$pid"
            echo "已终止 PID: $pid"
        done
    fi
}

# 启动 Chrome 和 Python 脚本
start_services() {

    SUDO_USER="$USER"

    # 启动 Python 脚本
    log_info "启动 $PYTHON_SCRIPT_DIR ..."
    export DISPLAY=:${VNC_DISPLAY}
    sudo -u "$SUDO_USER" -i nohup python3 "$PYTHON_SCRIPT_DIR$FILE_NAME" --serverId "$SERVER_ID" --appId "$APP_ID" --decryptKey "$DECRYPT_KEY" --user "$SUDO_USER" --chromePort "$CHROME_DEBUG_PORT" --display "$VNC_DISPLAY"> "$FILE_NAME"Out.log 2>&1 &
    log_info "脚本执行完成，已在后台运行，VNC 显示号 :$VNC_DISPLAY，端口 $VNC_PORT，noVNC 端口 $NOVNC_PORT，Chrome 调试端口 $CHROME_DEBUG_PORT"
}

# 主执行流程
main() {
    if [ "$(id -u)" -ne 0 ]; then
        error_exit "此脚本需要 root 权限运行，请使用 sudo 或以 root 用户执行"
    fi

    parse_args "$@"

    stop_services

    sudo apt-get install python3-tk python3-dev -y
#    update_system
    install_system_deps
    check_dependencies
    setup_vnc
#    install_chrome
    install_chrome_120
#    install_edge
#    install_wallet
    setup_img
    setup_python_script
    setup_xrdp
    setup_novnc
    install_python_packages
    start_services
}

main "$@"