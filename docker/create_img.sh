#!/bin/bash
set -e

# --------------------------------------------------------------
# 1. 基础变量：请根据实际环境进行修改
# --------------------------------------------------------------
IP_PREFIX="192.168."
NETWORK_SEGMENT="2"
SUBNET="${IP_PREFIX}${NETWORK_SEGMENT}.0/24"
GATEWAY="${IP_PREFIX}${NETWORK_SEGMENT}.20"
PARENT_IFACE="enp3s0"
NETWORK_NAME="mymacvlan${NETWORK_SEGMENT}"

IMAGE_NAME="node-ubuntu"

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

RUN pip3 install psutil requests paho-mqtt selenium pycryptodome loguru pyperclip

RUN mkdir /var/run/sshd

# 设置 root/ubuntu 用户密码
RUN echo "root:xujiaxujia" | chpasswd
RUN useradd -m -s /bin/bash ubuntu && echo "ubuntu:xujiaxujia" | chpasswd && adduser ubuntu sudo

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
# 4. 创建 Docker 网络
# --------------------------------------------------------------
echo ">>> 创建网络 ${NETWORK_NAME}..."
docker network create -d macvlan --subnet=${SUBNET} --gateway=${GATEWAY} -o parent=${PARENT_IFACE} ${NETWORK_NAME}

# --------------------------------------------------------------
# 5. 启动 Docker 容器
# --------------------------------------------------------------
echo ">>> 启动容器..."
docker run -it --rm --network ${NETWORK_NAME} --ip ${IP_PREFIX}.${NETWORK_SEGMENT}.100 --name myubuntu ${IMAGE_NAME}