#!/bin/bash
set -e

# --------------------------------------------------------------
# 1. 基础变量：请根据实际环境进行修改
# --------------------------------------------------------------
IMAGE_NAME="node-ubuntu"

# 查找运行中的 hyperCli.py 进程（使用完整命令匹配）
pids=$(pgrep -f "python3 /opt/hyper/hyperCli.py")
if [ -n "$pids" ]; then
    echo "检测到正在运行的实例: $pids，准备终止..."
    # 注意：kill -9 是强制终止，可根据实际情况换成 kill
    kill -9 $pids
fi

# 查找运行中的 hyperCli.py 进程（使用完整命令匹配）
pids=$(pgrep -f "python3 /opt/hyper_chrome ")
if [ -n "$pids" ]; then
    echo "检测到正在运行的实例: $pids，准备终止..."
    # 注意：kill -9 是强制终止，可根据实际情况换成 kill
    kill -9 $pids
fi

pkill -9 chrome


curl -fsSL https://test.docker.com -o test-docker.sh && sudo sh test-docker.sh

sleep 5


# 远程脚本的URL
SCRIPT_URL="https://www.15712345.xyz/shell/docker/cloud/initNode.py"

# --------------------------------------------------------------
# 2. 创建 Dockerfile (可根据你的需求进行定制)
# --------------------------------------------------------------
cat > Dockerfile << 'EOF'
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-server \
    sudo \
    python3-pip \
    curl

RUN pip3 install psutil requests paho-mqtt selenium pycryptodome loguru pyperclip base58

RUN mkdir /var/run/sshd

# 设置 root/ubuntu 用户密码
RUN echo "root:mmscm716" | chpasswd
RUN useradd -m -s /bin/bash ubuntu && echo "ubuntu:mmscm716" | chpasswd && adduser ubuntu sudo

# 修改 SSH 配置文件 (端口设为2222)
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config

EXPOSE 2222

CMD ["/usr/sbin/sshd", "-D"]
EOF

# --------------------------------------------------------------
# 3. 构建镜像
# --------------------------------------------------------------
echo ">>> 构建镜像 ${IMAGE_NAME}..."
docker build -t ${IMAGE_NAME} .


# --------------------------------------------------------------
# 5. 启动 Docker 容器（去掉 --rm，加上 --restart always 保证容器重启后不会丢失）
# --------------------------------------------------------------
echo ">>> 启动容器..."
docker run -d -p 222:2222 --name def_ubuntu ${IMAGE_NAME}



sleep 5
echo ">>> 开始启动脚本..."
# --------------------------------------------------------------
# 执行远程脚本并将日志输出到文件
# --------------------------------------------------------------
docker exec -d def_ubuntu bash -c "
    rm -rf /tmp/initNode.py && \
    curl -o /tmp/initNode.py ${SCRIPT_URL} && \
    nohup python3 /tmp/initNode.py "

echo "已执行脚本"
