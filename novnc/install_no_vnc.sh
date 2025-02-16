#!/bin/bash
# 默认值
USER=""
PASSWORD=""
SERVER_ID=""
APP_ID=""
DECRYPT_KEY=""
# 默认 VNC 端口
VNC_PORT=5923   # 在此可自定义要使用的 VNC 端口

# 使用 getopt 解析命令行参数
TEMP=$(getopt -o u:p:k:s:a: --long user:,password:,decryptKey:,serverId:,appId: -n 'startChrome.sh' -- "$@")
if [ $? != 0 ]; then
    echo "Failed to parse options."
    exit 1
fi
eval set -- "$TEMP"

while true; do
    case "$1" in
        -u|--user)
            USER=$2
            shift 2
            ;;
        -p|--password)
            PASSWORD=$2
            shift 2
            ;;
        -k|--decryptKey)
            DECRYPT_KEY=$2
            shift 2
            ;;
        -s|--serverId)
            SERVER_ID=$2
            shift 2
            ;;
        -a|--appId)
            APP_ID=$2
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Internal error!"
            exit 1
            ;;
    esac
done

# 如果没有传递 serverId 或 appId，打印错误信息并退出
if [ -z "$SERVER_ID" ] || [ -z "$APP_ID" ]; then
  echo "Usage: $0 --serverId SERVER_ID --appId APP_ID [--user USER] [--password PASSWORD]"
  exit 1
fi

# 如果没有传递 user，则可以在此提醒（可选）
if [ -z "$USER" ]; then
  echo "Warning: --user 未指定，将默认以 admin 身份执行相关操作（如需特定用户，请使用 --user）"
fi


echo "安装剪切板"
# 尝试安装 xclip
echo "尝试安装 xclip..."
if sudo apt-get install -y xclip; then
    echo "xclip 安装成功。"
else
    echo "检测到安装异常，开始处理问题..."

    # 更换镜像源为阿里云
    echo "更换镜像源为阿里云..."
    sudo tee /etc/apt/sources.list > /dev/null <<EOL
deb https://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ focal-backports main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal-backports main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
EOL

    # 更新软件包列表
    echo "重新更新软件包列表..."
    sudo apt-get update

    # 尝试修复损坏的依赖
    echo "尝试修复损坏的依赖..."
    sudo apt --fix-broken install -y

    # 再次尝试安装 xclip
    echo "再次尝试安装 xclip..."
    if sudo apt-get install -y xclip; then
        echo "xclip 安装成功。"
    else
        echo "仍然存在安装问题，尝试安装缺失的依赖..."
        # 安装缺失的依赖（根据报错信息添加或修改）
        sudo apt-get install -y libayatana-appindicator3-1 libwebkit2gtk-4.0-37
        echo "最后再次尝试安装 xclip..."
        sudo apt-get install -y xclip
    fi
fi

echo "脚本执行完成。"

# 安装包的下载链接和文件名
CHROME_DEB="google-chrome-stable_current_amd64.deb"
CHROME_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"

# 检查是否已安装 Google Chrome
if ! dpkg-query -l | grep -q "google-chrome-stable"; then
    echo "=== Google Chrome 未安装，开始安装 ==="

    # 下载 Google Chrome 安装包
    if ! curl -sSL "$CHROME_URL" -o "$CHROME_DEB"; then
        echo "Google Chrome 下载失败"
        exit 1
    fi

    echo "Google Chrome 下载成功，开始安装..."

    # 安装下载的 .deb 包
    if ! sudo dpkg -i "$CHROME_DEB"; then
        echo "安装失败，正在修复依赖..."
        sudo apt-get install -f -y  # 修复缺失的依赖
    fi

    # 清理下载的安装包
    rm -f "$CHROME_DEB"

    echo "Google Chrome 安装完成"
else
    echo "Google Chrome 已安装，跳过安装过程"
fi

# 如果 /opt/chrome.py 存在，则先删除旧文件
if [ -f /opt/chrome.py ]; then
    echo "/opt/chrome.py 已存在，正在删除旧文件..."
    rm -f /opt/chrome.py
fi

# 下载并执行远程 Python 脚本
echo "开始下载脚本：https://www.15712345.xyz/shell/hyper/chrome.py ..."
wget -O /opt/chrome.py https://www.15712345.xyz/shell/hyper/chrome.py
if [ ! -f /opt/chrome.py ]; then
    echo "脚本下载失败，请检查网络连接或 URL 是否正确。"
    exit 1
fi

echo "为 /opt/chrome.py 设置可执行权限..."
chmod +x /opt/chrome.py

# 如果用户传了 --user，则将文件属主改为该用户，同时后续用该用户执行
if [ -n "$USER" ]; then
    chown "$USER":"$USER" /opt/chrome.py
fi

# 根据实际需求决定 drissionpage 的安装位置
# 如果你希望以系统方式安装，可保留在外部安装
# 如果想让指定用户安装，则放到 sudo -u $USER -i 环境中执行
echo "安装/升级 drissionpage ..."
pip3 install --upgrade drissionpage

window=1


if netstat -tulpn | grep -q 'Xtightvnc'; then

  # 获取所有 Xtightvnc 的进程 ID
  pids=$(ps aux | grep Xtightvnc | grep -v grep | awk '{print $2}')

  # 统计进程数量
  pid_count=$(echo "$pids" | wc -l)

  # 如果只有多个实例杀掉
  if [ "$pid_count" -gt 1 ]; then
    # 获取最后一个
    last_pid=$(echo "$pids" | tail -n 1)

    # 杀掉
    for pid in $pids; do
      if [ "$pid" != "$last_pid" ]; then
        kill -9 $pid
        echo "Killed process with PID: $pid"
      fi
    done
  else
    echo "Only one Xtightvnc process running, no action taken."
  fi

  sleep 4

  window=$(ps aux | grep Xtightvnc | grep -v grep | awk '{sub(/:/, "", $12); print $12}' | head -n 1)
  echo "Xtightvnc 已启动 $window"
else
  echo "Xtightvnc 未启动,重新安装vnc"
  ##############################################################################
  # 安装桌面环境、VNC、XRDP等
  ##############################################################################
  echo "Installing xfce4, xfce4-goodies, tightvncserver, xrdp, expect, sudo..."
  apt-get install -y \
      xfce4 \
      xfce4-goodies \
      tightvncserver \
      xrdp \
      expect \
      sudo

  ##############################################################################
  # 创建用户
  ##############################################################################
  if id "$USER" &>/dev/null; then
      echo "用户 $USER 已存在，跳过创建步骤"
  else
      echo "创建用户 $USER ..."
      useradd -m -s /bin/bash "$USER"
      echo "$USER:$PASSWORD" | chpasswd
      # 如果需要让此用户可使用 sudo，则取消下面行的注释
      # usermod -aG sudo "$USER"
  fi

  sleep 2

  ##############################################################################
  # 以新建用户身份执行 VNC 配置
  ##############################################################################
  echo "开始以新建用户($USER)的身份执行 VNC 配置..."
  # 将必要变量传递进 sudo 环境
  sudo -u "$USER" VNC_PASS="$PASSWORD" VNC_REAL_PORT="$VNC_PORT" bash <<'INNEREOF'
  # 在这里引用外层传来的 VNC_PASS 和 VNC_REAL_PORT

  # 确保 ~/.vnc 文件夹存在，并设置正确权限
  mkdir -p "$HOME/.vnc"
  chmod 700 "$HOME/.vnc"

  # 构造 expect 脚本，用于初始化 VNC 密码
  EXPECT_SCRIPT=$(cat <<EOL
spawn tightvncserver :23 -rfbport ${VNC_REAL_PORT}
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
  tightvncserver -kill :23 >/dev/null 2>&1 || true
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
  tightvncserver -kill :23 >/dev/null 2>&1 || true

  # 最终启动 VNC 服务器，指定显示号、端口、分辨率和颜色深度
  tightvncserver :23 -rfbport ${VNC_REAL_PORT} -geometry 1920x1080 -depth 24
INNEREOF

  ##############################################################################
  # 最后输出信息
  ##############################################################################
  echo "=== 安装和配置已完成 ==="
  echo -e "\n"

fi

echo "等待5s"
sleep 5

echo "再次判断是否安装启动vnc"
if netstat -tulpn | grep -q 'Xtightvnc'; then
  window=$(ps aux | grep Xtightvnc | grep -v grep | awk '{sub(/:/, "", $12); print $12}' | head -n 1)
  echo "Xtightvnc 已启动 $window"
else
  echo "Xtightvnc未正常启动,退出脚本"
  exit 1
fi


##############################################################################
# XRDP 配置：让 XRDP 使用 Xfce4
##############################################################################
echo "Configuring XRDP..."
echo "startxfce4" > /home/$USER/.xsession
chown $USER:$USER /home/$USER/.xsession

# 如 XRDP 未运行，则启动
if ! service xrdp status | grep -q "running"; then
    echo "XRDP未运行，正在启动..."
    service xrdp start
    sleep 10
else
    echo "XRDP已在运行。"
fi

##############################################################################
# 检查 VNC 是否在运行，如没有则启动
##############################################################################
echo "检查 VNC 是否正在运行..."
if ! pgrep -f "tightvncserver :${window}" > /dev/null; then
    echo "VNC 尚未运行，正在启动..."
    sudo -u "$USER" tightvncserver :${window} -rfbport $VNC_PORT -geometry 1920x1080 -depth 24 &
    sleep 10  # 等待 VNC 启动并绑定端口
else
    echo "VNC 已在运行，跳过启动。"
fi

##############################################################################
# 安装 & 启动 noVNC
##############################################################################
if [ -d "noVNC" ]; then
    echo "noVNC 目录已存在，跳过 git clone。"
else
    echo "Downloading noVNC repository..."
    git clone https://github.com/novnc/noVNC.git
fi

echo "检查 noVNC 是否正在运行..."
if pgrep -f "novnc_proxy" > /dev/null; then
    echo "noVNC proxy 已在运行。"
else
    echo "Starting noVNC proxy..."
    nohup ./noVNC/utils/novnc_proxy \
        --vnc localhost:$VNC_PORT \
        --listen 26380 \
        &> /dev/null &
    echo "noVNC proxy started in the background (listening on port 26380)."
fi