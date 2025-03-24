#!/bin/bash
set -e

# --------------------------------------------------------------
# 1. 基础变量：请根据实际环境进行修改
# --------------------------------------------------------------
IP_PREFIX="192.168"
NETWORK_SEGMENT="2"
SUBNET="${IP_PREFIX}.${NETWORK_SEGMENT}.0/24"
GATEWAY="${IP_PREFIX}.${NETWORK_SEGMENT}.20"
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
# 4. 创建 Docker 网络（如果不存在才创建）
# --------------------------------------------------------------
if ! docker network inspect ${NETWORK_NAME} >/dev/null 2>&1; then
    echo ">>> 创建网络 ${NETWORK_NAME}..."
    docker network create -d macvlan --subnet=${SUBNET} --gateway=${GATEWAY} -o parent=${PARENT_IFACE} ${NETWORK_NAME}
else
    echo ">>> 网络 ${NETWORK_NAME} 已存在，跳过创建。"
fi

# --------------------------------------------------------------
# 5. 启动 Docker 容器（去掉 --rm，加上 --restart always 保证容器重启后不会丢失）
# --------------------------------------------------------------
echo ">>> 启动容器..."
docker run -it --restart always --network ${NETWORK_NAME} --ip ${IP_PREFIX}.${NETWORK_SEGMENT}.100 --name myubuntu ${IMAGE_NAME}

# --------------------------------------------------------------
# 6. 重设容器内全局代理（先删除之前设置的代理，再写入新的代理配置到 /etc/environment）
# --------------------------------------------------------------
echo ">>> 重设容器内全局代理..."
docker exec myubuntu bash -c 'sed -i "/[Hh][Tt][Tt][Pp]_proxy=/d" /etc/environment && \
sed -i "/[Hh][Tt][Tt][Pp][Ss]_proxy=/d" /etc/environment && \
echo "http_proxy=http://192.168.1.30:7890" >> /etc/environment && \
echo "https_proxy=http://192.168.1.30:7890" >> /etc/environment'
