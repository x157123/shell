#!/bin/bash

# 脚本描述: 用于配置和管理 Chrome 浏览器的自动化环境，支持多实例 VNC 配置和动态端口

# 常量定义
readonly APT_PACKAGES=("net-tools" "fontconfig" "fonts-wqy-zenhei" "fonts-wqy-microhei" "lsof" "python3-tk" "python3-dev" "libu2f-udev")  # 添加 lsof
readonly PYTHON_PACKAGES=("psutil" "requests" "paho-mqtt" "selenium" "pycryptodome" "loguru" "pyperclip" "drissionpage" "pyautogui")
readonly DEPENDENCIES=("curl" "wget" "git" "pip3" "lsof" "expect")  # 依赖命令
readonly PYTHON_SCRIPT_DIR="/opt/"  # 目录
readonly DEFAULT_VNC_DISPLAY=23       # 默认显示号
readonly VNC_BASE_PORT=5900           # VNC 基础端口
readonly NOVNC_BASE_PORT=26300        # noVNC 基础端口
readonly CHROME_DEBUG_BASE_PORT=9518  # Chrome 调试基础端口

# 默认值
USER="${USER:-admin}"
PASSWORD="${PASSWORD:-default_password}"
SERVER_ID=""
APP_ID=""
DECRYPT_KEY="${DECRYPT_KEY:-default_password}"
VNC_DISPLAY="${VNC_DISPLAY:-$DEFAULT_VNC_DISPLAY}"
FILE_NAME=""
PYTHON_SCRIPT_URL=""
CONTAINER_NAME="def_ubuntu"
RUN_NODE_PYTHON_SCRIPT_URL="https://www.15712345.xyz/shell/docker/cloud/runNode.py"
RUN_NODE_SH_PYTHON_SCRIPT_URL="https://www.15712345.xyz/shell/docker/cloud/runNodePort.sh"

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
    CHROME_DEBUG_PORT=$((CHROME_DEBUG_BASE_PORT + 0))
}

# 更新系统包列表
update_system() {
    log_info "更新系统软件包列表..."
    sudo apt update -y || error_exit "软件包列表更新失败"
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

    if [ -f "$PYTHON_SCRIPT_DIR/runNode.py" ]; then
        log_info "$PYTHON_SCRIPT_DIR/runNode.py 已存在，删除旧文件..."
        rm -f "$PYTHON_SCRIPT_DIR/runNode.py"
    fi

    if [ -f "$PYTHON_SCRIPT_DIR/runNode.sh" ]; then
        log_info "$PYTHON_SCRIPT_DIR/runNode.sh 已存在，删除旧文件..."
        rm -f "$PYTHON_SCRIPT_DIR/runNode.sh"
    fi


    log_info "下载 Python 脚本..."
    wget -q -O "$PYTHON_SCRIPT_DIR$FILE_NAME" "$PYTHON_SCRIPT_URL" || error_exit "脚本下载失败"
    chmod +x "$PYTHON_SCRIPT_DIR$FILE_NAME"
    chown "$USER:$USER" "$PYTHON_SCRIPT_DIR$FILE_NAME"


    log_info "下载 Python 脚本..."
    wget -q -O "$PYTHON_SCRIPT_DIR/runNode.py" "$RUN_NODE_PYTHON_SCRIPT_URL" || error_exit "脚本下载失败"
    chmod +x "$PYTHON_SCRIPT_DIR/runNode.py"
    chown "$USER:$USER" "$PYTHON_SCRIPT_DIR/runNode.py"


    log_info "下载 Python 脚本..."
    wget -q -O "$PYTHON_SCRIPT_DIR/runNodePort.sh" "$RUN_NODE_SH_PYTHON_SCRIPT_URL" || error_exit "脚本下载失败"
    chmod +x "$PYTHON_SCRIPT_DIR/runNodePort.sh"
    chown "$USER:$USER" "$PYTHON_SCRIPT_DIR/runNodePort.sh"
}


# 启动 Chrome 和 Python 脚本
start_services() {

    SUDO_USER="$USER"

    # 启动 Python 脚本
    log_info "启动 $PYTHON_SCRIPT_DIR ..."
    export DISPLAY=:${VNC_DISPLAY}
    nohup python3 "$PYTHON_SCRIPT_DIR$FILE_NAME" --serverId "$SERVER_ID" --appId "$APP_ID" --decryptKey "$DECRYPT_KEY" --user "$SUDO_USER" --chromePort "$CHROME_DEBUG_PORT" --display "$VNC_DISPLAY"> "$FILE_NAME"Out.log 2>&1 &
    log_info "脚本执行完成，已在后台运行，VNC 显示号 :$VNC_DISPLAY，端口 $VNC_PORT，noVNC 端口 $NOVNC_PORT，Chrome 调试端口 $CHROME_DEBUG_PORT"
}

# 主执行流程
main() {
    if [ "$(id -u)" -ne 0 ]; then
        error_exit "此脚本需要 root 权限运行，请使用 sudo 或以 root 用户执行"
    fi

    if ! docker ps -a --format '{{.Names}}' | grep -q "${CONTAINER_NAME}"; then
        echo "容器 ${CONTAINER_NAME} 不存在，需要创建并启动容器..."
        exit 0
    else
        echo "容器 ${CONTAINER_NAME} 已存在"
        # 检查容器是否已启动，如果已启动，跳过创建
        if ! docker ps --format '{{.Names}}' | grep -q "${CONTAINER_NAME}"; then
            echo "容器 ${CONTAINER_NAME} 已存在，但未启动..."
        else
            echo "容器 ${CONTAINER_NAME} 已存在，但未启动，正在启动..."
            docker stop "${CONTAINER_NAME}"
            sleep 10
        fi

        docker commit def_ubuntu unbutu:node
    fi

    check_dependencies
    parse_args "$@"
    update_system
    setup_python_script
    install_python_packages
    start_services
}

main "$@"