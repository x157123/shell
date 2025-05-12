#!/bin/bash

# 脚本描述: 用于配置和管理 Chrome 浏览器的自动化环境，支持多实例 VNC 配置和动态端口

# 常量定义
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
}

# 启动 Chrome 和 Python 脚本
start_services() {
    # 启动 Python 脚本
    log_info "启动 $PYTHON_SCRIPT_DIR ..."
    python3 -m venv ~/drission_venv
    source ~/drission_venv/bin/activate
    pak add loguru
    nohup python3 "$PYTHON_SCRIPT_DIR$FILE_NAME" --serverId "$SERVER_ID" --appId "$APP_ID" --decryptKey "$DECRYPT_KEY" --user "$SUDO_USER" --chromePort "$CHROME_DEBUG_PORT" --display "$VNC_DISPLAY"> "$FILE_NAME"Out.log 2>&1 &
    log_info "脚本执行完成，已在后台运行，VNC 显示号 :$VNC_DISPLAY，端口 $VNC_PORT，noVNC 端口 $NOVNC_PORT，Chrome 调试端口 $CHROME_DEBUG_PORT"
}

# 主执行流程
main() {
    if [ "$(id -u)" -ne 0 ]; then
        error_exit "此脚本需要 root 权限运行，请使用 sudo 或以 root 用户执行"
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

    parse_args "$@"
    setup_python_script
    start_services
}

main "$@"