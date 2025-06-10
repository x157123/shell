#!/usr/bin/env bash
set -euo pipefail
set -x

# =============================
# Xray SOCKS5 代理 (TOML 格式) 一键安装脚本
#
# 用法：$0 [LISTEN_PORT] [USERNAME] [PASSWORD]
# 示例：./install_socks_toml.sh 1080 myuser mypass
# 默认：1080 enCNHQqNML KU6L2u3T86
# =============================

# ---- 可选参数 ----
LISTEN_PORT=${1:-10800}
SOCKS_USER=${2:-enCNHQqNML}
SOCKS_PASS=${3:-KU6L2u3T86}

# ---- 固定变量 ----
XRAY_BIN="/usr/local/bin/xray"
SERVICE_NAME="xray-socks"
CONFIG_DIR="/etc/xray"
CONFIG_FILE="${CONFIG_DIR}/config.toml"

# ---- 更新或创建 systemd 服务 ----
update_service() {
    echo "[INFO] 更新 systemd 服务文件..."
    mkdir -p "$CERT_DIR"
    cat <<EOF >/etc/systemd/system/${SERVICE_NAME}.service
[Unit]
Description=XrayL Service
After=network.target

[Service]
ExecStart=${XRAY_BIN} -config ${CONFIG_FILE}
Restart=on-failure
User=root
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}
}

# ---- 安装 Xray Core ----
install_xray() {
  echo "[INFO] 安装 Xray Core..."
  if command -v apt-get &>/dev/null; then
    apt-get update && apt-get install -y unzip wget
  else
    yum install -y unzip wget
  fi

  wget -qO /tmp/xray.zip \
    https://github.com/XTLS/Xray-core/releases/download/v25.5.16/Xray-linux-64.zip
  unzip -o /tmp/xray.zip -d /usr/local/bin
  chmod +x "$XRAY_BIN"
}


# ---- 生成 TOML 配置 ----
generate_config() {
  echo "[INFO] 生成配置文件：${CONFIG_FILE}"
  mkdir -p "$CONFIG_DIR"
  cat > "$CONFIG_FILE" <<EOF
[log]
loglevel = "info"

# inbound: SOCKS5 代理
[[inbounds]]
port = ${LISTEN_PORT}
listen = "0.0.0.0"
protocol = "socks"

[inbounds.settings]
auth = "password"
udp = true
accounts = [
  { user = "${SOCKS_USER}", pass = "${SOCKS_PASS}" }
]

# outbound: 直接放行
[[outbounds]]
protocol = "freedom"
EOF
}

# ---- 主流程 ----
main() {
    if ! command -v "$XRAY_BIN" &>/dev/null; then
        install_xray
    else
        update_service
    fi
    generate_config
    systemctl restart ${SERVICE_NAME}
    echo "[INFO] Xray 服务已重启，配置已生效。"
}

main
