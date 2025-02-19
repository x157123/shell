#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

VERSION="0.4.7"

NEXUS_HOME="$HOME/.nexus"
PROVER_ID_FILE="$NEXUS_HOME/prover-id"
SESSION_NAME="nexus-prover"
PROGRAM_DIR="$NEXUS_HOME/src/generated"
ARCH=$(uname -m)
OS=$(uname -s)
REPO_BASE="https://github.com/nexus-xyz/network-api/raw/refs/tags/$VERSION/clients/cli"

check_openssl_version() {
    if [ "$OS" = "Linux" ]; then
        if ! command -v openssl &> /dev/null; then
            echo -e "${RED}未安装 OpenSSL${NC}"
            return 1
        fi

        local version=$(openssl version | cut -d' ' -f2)
        local major_version=$(echo $version | cut -d'.' -f1)

        if [ "$major_version" -lt "3" ]; then
            if command -v apt &> /dev/null; then
                echo -e "${YELLOW}当前 OpenSSL 版本过低，正在升级...${NC}"
                sudo apt update
                sudo apt install -y openssl
                if [ $? -ne 0 ]; then
                    echo -e "${RED}OpenSSL 升级失败，请手动升级至 3.0 或更高版本${NC}"
                    return 1
                fi
            elif command -v yum &> /dev/null; then
                echo -e "${YELLOW}当前 OpenSSL 版本过低，正在升级...${NC}"
                sudo yum update -y openssl
                if [ $? -ne 0 ]; then
                    echo -e "${RED}OpenSSL 升级失败，请手动升级至 3.0 或更高版本${NC}"
                    return 1
                fi
            else
                echo -e "${RED}请手动升级 OpenSSL 至 3.0 或更高版本${NC}"
                return 1
            fi
        fi
        echo -e "${GREEN}OpenSSL 版本检查通过${NC}"
    fi
    return 0
}

setup_directories() {
    mkdir -p "$PROGRAM_DIR"
    ln -sf "$PROGRAM_DIR" "$NEXUS_HOME/src/generated"
}

check_dependencies() {
    check_openssl_version || exit 1

    if ! command -v tmux &> /dev/null; then
        echo -e "${YELLOW}tmux 未安装, 正在安装...${NC}"
        if [ "$OS" = "Darwin" ]; then
            if ! command -v brew &> /dev/null; then
                echo -e "${RED}请先安装 Homebrew: https://brew.sh${NC}"
                exit 1
            fi
            brew install tmux
        elif [ "$OS" = "Linux" ]; then
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install -y tmux
            elif command -v yum &> /dev/null; then
                sudo yum install -y tmux
            else
                echo -e "${RED}未能识别的包管理器，请手动安装 tmux${NC}"
                exit 1
            fi
        fi
    fi
}

download_program_files() {
    local files="cancer-diagnostic fast-fib"

    for file in $files; do
        local target_path="$PROGRAM_DIR/$file"
        if [ ! -f "$target_path" ]; then
            echo -e "${YELLOW}下载 $file...${NC}"
            curl -L "$REPO_BASE/src/generated/$file" -o "$target_path"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}$file 下载完成${NC}"
                chmod +x "$target_path"
            else
                echo -e "${RED}$file 下载失败${NC}"
            fi
        fi
    done
}

download_prover() {
    local prover_path="$NEXUS_HOME/prover"
    if [ ! -f "$prover_path" ]; then
        if [ "$OS" = "Darwin" ]; then
            if [ "$ARCH" = "x86_64" ]; then
                echo -e "${YELLOW}下载 macOS Intel 架构 Prover...${NC}"
                curl -L "https://github.com/qzz0518/nexus-run/releases/download/v$VERSION/prover-macos-amd64" -o "$prover_path"
            elif [ "$ARCH" = "arm64" ]; then
                echo -e "${YELLOW}下载 macOS ARM64 架构 Prover...${NC}"
                curl -L "https://github.com/qzz0518/nexus-run/releases/download/v$VERSION/prover-arm64" -o "$prover_path"
            else
                echo -e "${RED}不支持的 macOS 架构: $ARCH${NC}"
                exit 1
            fi
        elif [ "$OS" = "Linux" ]; then
            if [ "$ARCH" = "x86_64" ]; then
                echo -e "${YELLOW}下载 Linux AMD64 架构 Prover...${NC}"
                curl -L "https://github.com/qzz0518/nexus-run/releases/download/v$VERSION/prover-amd64" -o "$prover_path"
            elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
                echo -e "${YELLOW}下载 Linux ARM64 架构 Prover...${NC}"
                curl -L "https://github.com/qzz0518/nexus-run/releases/download/v$VERSION/prover-linux-arm64" -o "$prover_path"
            else
                echo -e "${RED}不支持的 Linux 架构: $ARCH${NC}"
                exit 1
            fi
        else
            echo -e "${RED}不支持的操作系统: $OS${NC}"
            exit 1
        fi
        chmod +x "$prover_path"
        echo -e "${GREEN}Prover 下载完成${NC}"
    fi
}

download_files() {
    download_prover
    download_program_files
}

generate_prover_id() {
    local temp_output=$(mktemp)
    tail -f "$temp_output" &
    local tail_pid=$!

    "./prover" beta.orchestrator.nexus.xyz > "$temp_output" 2>&1 &
    local prover_pid=$!

    while ! grep -q "Success! Connection complete!" "$temp_output" 2>/dev/null; do
        if ! kill -0 $prover_pid 2>/dev/null; then
            break
        fi
        sleep 1
    done

    kill $prover_pid 2>/dev/null
    kill $tail_pid 2>/dev/null

    local prover_id=$(grep -o 'Your current prover identifier is [^ ]*' "$temp_output" | cut -d' ' -f6)
    if [ -n "$prover_id" ]; then
        echo "$prover_id" > "$PROVER_ID_FILE"
        echo -e "${GREEN}已生成并保存新的 Prover ID: $prover_id${NC}"
    else
        echo -e "${RED}生成 Prover ID 失败${NC}"
    fi
    rm "$temp_output"
}

start_prover() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${YELLOW}Prover 已在运行中，请选择2查看运行日志${NC}"
        return
    fi

    cd "$NEXUS_HOME" || exit

    if [ ! -f "$PROVER_ID_FILE" ]; then
        echo -e "${YELLOW}Please enter your Prover ID${NC}"
        echo -e "${YELLOW}If you don't have a Prover ID, press Enter to automatically generate one${NC}"
        read -p "Prover ID > " input_id

        if [ -n "$input_id" ]; then
            echo "$input_id" > "$PROVER_ID_FILE"
            echo -e "${GREEN}Saved Prover ID: $input_id${NC}"
        else
            echo -e "${YELLOW}A new Prover ID will be automatically generated...${NC}"
        fi
    fi

    tmux new-session -d -s "$SESSION_NAME" "cd '$NEXUS_HOME' && ./prover rpc.nexus.xyz/ws"
    echo -e "${GREEN}Prover 已启动，选择2可查看运行日志${NC}"
}

check_status() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${GREEN}Prover 正在运行中. 正在打开日志窗口...${NC}"
        echo -e "${YELLOW}提示: 查看完成后直接关闭终端即可，不要使用 Ctrl+C${NC}"
        sleep 2
        tmux attach-session -t "$SESSION_NAME"
    else
        echo -e "${RED}Prover 未运行${NC}"
    fi
}

show_prover_id() {
    if [ -f "$PROVER_ID_FILE" ]; then
        local id=$(cat "$PROVER_ID_FILE")
        echo -e "${GREEN}当前 Prover ID: $id${NC}"
    else
        echo -e "${RED}未找到 Prover ID${NC}"
    fi
}

set_prover_id() {
    if [ -n "$1" ]; then
        echo "$1" > "$PROVER_ID_FILE"
        echo -e "${GREEN}Prover ID 已更新${NC}"
    else
        echo -e "${RED}Prover ID 不能为空${NC}"
    fi
}

stop_prover() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        tmux kill-session -t "$SESSION_NAME"
        echo -e "${GREEN}Prover 已停止${NC}"
    else
        echo -e "${RED}Prover 未运行${NC}"
    fi
}

update_nexus() {
    echo -e "${YELLOW}开始更新 Nexus...${NC}"

    stop_prover
    echo -e "${YELLOW}删除现有文件...${NC}"
    rm -f "$NEXUS_HOME/prover"
    rm -rf "$PROGRAM_DIR"/*

    echo -e "${YELLOW}重新安装 Nexus...${NC}"
    setup_directories
    check_dependencies
    download_files

    echo -e "${GREEN}更新完成！正在启动 Nexus...${NC}"

    start_prover
}

cleanup() {
    echo -e "\n${YELLOW}正在清理...${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 解析命令行参数
while getopts "1-7s:" opt; do
    case $opt in
        1)
            setup_directories
            check_dependencies
            download_files
            start_prover
            ;;
        2)
            check_status
            ;;
        3)
            show_prover_id
            ;;
        4)
            set_prover_id "$OPTARG"
            ;;
        5)
            stop_prover
            ;;
        6)
            update_nexus
            ;;
        7)
            echo -e "\n${GREEN}感谢使用！${NC}"
            echo -e "${YELLOW}更多工具请关注 Twitter: ${NC}https://x.com/zerah_eth"
            echo -e "${YELLOW}SOL 代币回收工具: ${NC}https://solback.app/\n"
            cleanup
            ;;
        *)
            echo -e "${RED}无效的选择${NC}"
            ;;
    esac
done
