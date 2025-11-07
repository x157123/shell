#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
IFS=$'\n\t'

# ================== 可配参数 ==================
TARGET_USER="ubuntu"
PASSWORD="Mmscm716+"

EDGE_VERSION="133.0.3065.82"  # 固定 Edge 版本
EDGE_DEB="microsoft-edge-stable_${EDGE_VERSION}-1_amd64.deb"
EDGE_URL="https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/${EDGE_DEB}"

START_DISPLAY=24
END_DISPLAY=24
GEOMETRY="1920x1080"
DEPTH=24
# =============================================

error_exit() { echo "ERROR: $1" >&2; exit 1; }
log_info()   { echo "[INFO] $1"; }

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    error_exit "此脚本需要以 root 权限运行（请使用 sudo 或 root）"
  fi
}

apt_prepare() {
  log_info "更新软件源并安装基础组件..."
  apt-get update -y
  apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    xfce4 xfce4-goodies tightvncserver xrdp \
    dbus-x11 x11-xserver-utils \
    fonts-noto-cjk fonts-noto-color-emoji fonts-wqy-zenhei fonts-wqy-microhei
  fc-cache -f -v >/dev/null 2>&1 || true
}

check_port() {
  local port="$1"
  ss -lnt | grep -q ":${port}" && return 0 || return 1
}

ensure_user() {
  if ! id "$TARGET_USER" >/dev/null 2>&1; then
    log_info "创建用户 ${TARGET_USER}..."
    useradd -m -s /bin/bash "$TARGET_USER"
    echo "${TARGET_USER}:${PASSWORD}" | chpasswd
  else
    log_info "用户 ${TARGET_USER} 已存在，跳过创建"
  fi
}

install_edge() {
  if dpkg-query -W microsoft-edge-stable >/dev/null 2>&1; then
    log_info "Microsoft Edge 已安装，跳过"
    return 0
  fi

  log_info "下载 Microsoft Edge ${EDGE_VERSION} ..."
  curl -fSLo "$EDGE_DEB" "$EDGE_URL" || error_exit "Edge 安装包下载失败：$EDGE_URL"

  log_info "安装 Edge（自动解决依赖）..."
  apt-get install -y "./${EDGE_DEB}" || error_exit "Edge 安装失败"
  rm -f "$EDGE_DEB"

  apt-mark hold microsoft-edge-stable || true
  log_info "Microsoft Edge 安装完成并已 hold"
}

write_user_file() {
  local path="$1"
  local content="$2"
  install -o "$TARGET_USER" -g "$TARGET_USER" -m 700 -d "$(dirname "$path")"
  printf "%s\n" "$content" > "$path"
  chown "$TARGET_USER:$TARGET_USER" "$path"
}

setup_vnc_for_display() {
  local dpy="$1"
  local port=$((5900 + dpy))

  log_info "配置 VNC 会话 :$dpy (端口 $port) ..."

  # 准备 ~/.vnc 目录
  install -o "$TARGET_USER" -g "$TARGET_USER" -m 700 -d "/home/${TARGET_USER}/.vnc"

  # 以目标用户身份：杀旧会话、删旧密码、非交互创建新密码、写 xstartup、启动
  su - "$TARGET_USER" -c "VNC_PASS='${PASSWORD}' VNC_DP='${dpy}' VNC_PORT='${port}' GEOMETRY='${GEOMETRY}' DEPTH='${DEPTH}' bash -s" <<'EOF'
set -Eeuo pipefail

# 停旧会话（忽略失败）
tightvncserver -kill ":${VNC_DP}" >/dev/null 2>&1 || true

# 删除旧密码文件
rm -f "$HOME/.vnc/passwd" "$HOME/.vnc/passwd.view" "$HOME/.vnc/passwd.ro" 2>/dev/null || true

# 非交互写入新密码（与系统密码可相同或不同）
umask 077
printf "%s\n" "$VNC_PASS" | vncpasswd -f > "$HOME/.vnc/passwd"
chmod 600 "$HOME/.vnc/passwd"

# 写 xstartup（每次覆盖，确保一致）
cat > "$HOME/.vnc/xstartup" <<'XSTARTUP'
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
XSTARTUP
chmod +x "$HOME/.vnc/xstartup"

# 再保险地停一次，确保应用最新配置
tightvncserver -kill ":${VNC_DP}" >/dev/null 2>&1 || true

# 启动 VNC
tightvncserver ":${VNC_DP}" -rfbport "${VNC_PORT}" -geometry "${GEOMETRY}" -depth "${DEPTH}"
EOF

  # 双重校验：进程 + 端口
  if pgrep -u "$TARGET_USER" -f "Xtightvnc :${dpy}" >/dev/null 2>&1 && check_port "$port"; then
    log_info "VNC :$dpy 启动成功（端口 $port 正在监听）"
  else
    error_exit "VNC :$dpy 启动失败，请检查 /home/${TARGET_USER}/.vnc/*.log"
  fi
}

setup_xrdp() {
  log_info "配置并启动 XRDP ..."
  write_user_file "/home/${TARGET_USER}/.xsession" "startxfce4"
  chmod 644 "/home/${TARGET_USER}/.xsession"
  systemctl enable --now xrdp
  systemctl is-active --quiet xrdp && log_info "XRDP 已运行" || error_exit "XRDP 启动失败"
}

main() {
  require_root
  apt_prepare
  ensure_user
  install_edge

  for dpy in $(seq "$START_DISPLAY" "$END_DISPLAY"); do
    setup_vnc_for_display "$dpy"
  done

  setup_xrdp
  log_info "全部完成 ✅"
}

main "$@"
