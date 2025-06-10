#!/usr/bin/env bash
set -euo pipefail
set -x

# ============================
# Xray 安装与多出口配置脚本
# 修正版：支持通过脚本参数指定远程 SOCKS 服务器
# Usage: $0 [REMOTE_SOCKS_SERVER1 REMOTE_SOCKS_SERVER2 ...]
# ============================

usage() {
    echo "Usage: $0 [REMOTE_SOCKS_SERVER ...]"
    exit 1
}

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
    usage
fi

# ---- 默认参数 ----
BASE_PORT_DIRECT=22291
BASE_PORT_FWD=22292
DEFAULT_REMOTE_SOCKS_SERVERS=()
DEFAULT_SOCKS_PORT=10800
DEFAULT_SOCKS_USER="enCNHQqNML"
DEFAULT_SOCKS_PASS="KU6L2u3T86"
DEFAULT_UUID="8d653735-cd42-4e35-b5e7-9d3724009ef0"
DEFAULT_WS_PATH="/8d653735-cd42-4e35-b5e7-9d3724009ef0"
CERT_DIR="/etc/xray"
CERT_FILE="$CERT_DIR/cert.crt"
KEY_FILE="$CERT_DIR/private.key"
CONFIG_FILE="$CERT_DIR/config.toml"
XRAY_BIN="/usr/local/bin/xray"
SERVICE_NAME="xrayL"

# ---- 解析传入的 SOCKS 服务器 ----
if [ "$#" -ge 1 ]; then
    REMOTE_SOCKS_SERVERS=("$@")
else
    REMOTE_SOCKS_SERVERS=("${DEFAULT_REMOTE_SOCKS_SERVERS[@]}")
fi

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
    wget -qO /tmp/xray_core.zip \
        https://github.com/XTLS/Xray-core/releases/download/v25.5.16/Xray-linux-64.zip
    unzip -o /tmp/xray_core.zip -d /usr/local/bin
    chmod +x "$XRAY_BIN"
    update_service
    echo "[INFO] Xray Core 安装完成。"
}

# ---- 生成 Xray 配置文件 (TOML) ----
generate_config() {
    echo "[INFO] 生成 Xray 配置文件 ${CONFIG_FILE}..."
    mkdir -p "$CERT_DIR"
    cat > "$CONFIG_FILE" <<EOF
[log]
loglevel = "info"

# 直连节点
[[inbounds]]
port = ${BASE_PORT_DIRECT}
listen = "0.0.0.0"
protocol = "vmess"
tag = "direct_in"
[inbounds.settings]
  clients = [ { id = "${DEFAULT_UUID}", alterId = 0 } ]
[inbounds.streamSettings]
  network = "ws"
  security = "tls"
[inbounds.streamSettings.wsSettings]
  path = "${DEFAULT_WS_PATH}"
[inbounds.streamSettings.tlsSettings]
  certificates = [ { certificateFile = "${CERT_FILE}", keyFile = "${KEY_FILE}" } ]

EOF

    # 转发节点
    for i in "${!REMOTE_SOCKS_SERVERS[@]}"; do
        port=$((BASE_PORT_FWD + i))
        idx=$((i + 1))
        cat >> "$CONFIG_FILE" <<EOF
[[inbounds]]
port = ${port}
listen = "0.0.0.0"
protocol = "vmess"
tag = "fwd_${idx}"
[inbounds.settings]
  clients = [ { id = "${DEFAULT_UUID}", alterId = 0 } ]
[inbounds.streamSettings]
  network = "ws"
  security = "tls"
[inbounds.streamSettings.wsSettings]
  path = "${DEFAULT_WS_PATH}"
[inbounds.streamSettings.tlsSettings]
  certificates = [ { certificateFile = "${CERT_FILE}", keyFile = "${KEY_FILE}" } ]

EOF
    done

    # 出站配置
    cat >> "$CONFIG_FILE" <<EOF
# 出站配置

[[outbounds]]
tag = "direct"
protocol = "freedom"

EOF

    for i in "${!REMOTE_SOCKS_SERVERS[@]}"; do
        idx=$((i + 1))
        remote_ip="${REMOTE_SOCKS_SERVERS[i]}"
        cat >> "$CONFIG_FILE" <<EOF
[[outbounds]]
tag = "socks_${idx}"
protocol = "socks"
[outbounds.settings]
  servers = [ { address = "${remote_ip}", port = ${DEFAULT_SOCKS_PORT}, users = [ { user = "${DEFAULT_SOCKS_USER}", pass = "${DEFAULT_SOCKS_PASS}" } ] } ]

EOF
    done

    # 路由规则
    cat >> "$CONFIG_FILE" <<EOF
# 路由规则
[routing]
domainStrategy = "AsIs"

EOF

    for i in "${!REMOTE_SOCKS_SERVERS[@]}"; do
        idx=$((i + 1))
        cat >> "$CONFIG_FILE" <<EOF
[[routing.rules]]
type = "field"
inboundTag = [ "fwd_${idx}" ]
outboundTag = "socks_${idx}"

EOF
    done

    # 直连路由
    cat >> "$CONFIG_FILE" <<EOF
# 直连路由
[[routing.rules]]
type = "field"
inboundTag = [ "direct_in" ]
outboundTag = "direct"
EOF

    echo "[INFO] 配置文件生成完成。"
}

# ---- 主流程 ----
main() {
    if ! command -v "$XRAY_BIN" &>/dev/null; then
        install_xray
    else
        update_service
    fi
    generate_config
    chown -R root:root "$CERT_DIR"
    chmod 644 "$CERT_FILE"
    chmod 600 "$KEY_FILE"
    systemctl restart ${SERVICE_NAME}
    echo "[INFO] Xray 服务已重启，配置已生效。"
}

main
