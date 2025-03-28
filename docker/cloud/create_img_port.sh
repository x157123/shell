#!/bin/bash
set -e

# --------------------------------------------------------------
# 1. 基础变量：请根据实际环境进行修改
# --------------------------------------------------------------
IMAGE_NAME="node-ubuntu"
CONTAINER_NAME="def_ubuntu"


echo "开始安装 Docker..."

# --------------------------------------------------------------
# 2. 检查 Docker 是否安装
# --------------------------------------------------------------
if ! command -v docker &> /dev/null
then
    echo "Docker 未安装，开始安装 Docker..."

    # 检查锁定状态并尝试解决
    while fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
        echo "检测到 apt 锁定，等待 10 秒后重试..."
        sleep 10
    done

    curl -fsSL https://test.docker.com -o test-docker.sh && sudo sh test-docker.sh
    sleep 5
else
    echo "Docker 已安装"
fi

# --------------------------------------------------------------
# 3. 判断 Docker 容器是否已启动
# --------------------------------------------------------------
docker ps --filter "name=${CONTAINER_NAME}" --filter "status=running" | grep -q "${CONTAINER_NAME}"
if [ $? -eq 0 ]; then
    echo "容器 ${CONTAINER_NAME} 已经在运行，退出脚本"
    exit 0
fi



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
docker run -d -p 222:2222 --name ${CONTAINER_NAME} ${IMAGE_NAME}



sleep 5
echo ">>> 开始启动脚本..."
# --------------------------------------------------------------
# 执行远程脚本并将日志输出到文件
# --------------------------------------------------------------
docker exec -d ${CONTAINER_NAME} bash -c "
    rm -rf /tmp/initNode.py && \
    curl -o /tmp/initNode.py ${SCRIPT_URL} && \
    nohup python3 /tmp/initNode.py "

echo "已执行脚本"
