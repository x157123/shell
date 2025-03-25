#!/bin/bash
set -e

# 检查是否传入了参数
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <DATA> <ip_suffix>"
    exit 1
fi

# 传递的参数数据
DATA="$1"
ip_suffix="$2"
NETWORK_SEGMENT="$3"
PROXY="$4"

# 自定义镜像名称
IMAGE_NAME="unbutu:node"

IP_PREFIX="192.168"
SUBNET="${IP_PREFIX}.${NETWORK_SEGMENT}.0/24"
GATEWAY="${IP_PREFIX}.${NETWORK_SEGMENT}.20"
PARENT_IFACE="enp3s0"
NETWORK_NAME="mymacvlan${NETWORK_SEGMENT}"

# 远程脚本的URL
SCRIPT_URL="https://www.15712345.xyz/shell/hyper/hyperLocalCli.py"

container_ip="${IP_PREFIX}.${NETWORK_SEGMENT}.${ip_suffix}"
container_name="node${ip_suffix}"

echo ">>> 检查容器: ${container_name}"
echo "    - 容器IP: ${container_ip}"


# --------------------------------------------------------------
# 创建 Docker 网络（如果不存在才创建）
# --------------------------------------------------------------
if ! docker network inspect ${NETWORK_NAME} >/dev/null 2>&1; then
    echo ">>> 创建网络 ${NETWORK_NAME}..."
    docker network create -d macvlan --subnet=${SUBNET} --gateway=${GATEWAY} -o parent=${PARENT_IFACE} ${NETWORK_NAME}
else
    echo ">>> 网络 ${NETWORK_NAME} 已存在，跳过创建。"
fi


# 检查容器是否存在并已启动
if ! docker ps -a --format '{{.Names}}' | grep -q "${container_name}"; then
    echo "容器 ${container_name} 不存在，创建并启动容器..."
    # 启动 Docker 容器
    docker run -d \
        --name "${container_name}" \
        --p "${ip_suffix}:2222" \
        ${IMAGE_NAME}
else
    echo "容器 ${container_name} 已存在"
    # 检查容器是否已启动，如果已启动，跳过创建
    if ! docker ps --format '{{.Names}}' | grep -q "${container_name}"; then
        echo "容器 ${container_name} 已存在，但未启动，正在启动..."
        docker start "${container_name}"
    fi
fi

# 等待 5 秒钟
#sleep 5

# --------------------------------------------------------------
# 重设容器内全局代理（先删除之前设置的代理，再写入新的代理配置到 /etc/environment）
# --------------------------------------------------------------
#echo ">>> 重设容器内全局代理..."
#docker exec "${container_name}" bash -c "sed -i '/[Hh][Tt][Tt][Pp]_proxy=/d' /etc/environment && \
#sed -i '/[Hh][Tt][Tt][Pp][Ss]_proxy=/d' /etc/environment && \
#echo \"http_proxy=http://${PROXY}\" >> /etc/environment && \
#echo \"https_proxy=https://${PROXY}\" >> /etc/environment"

sleep 5 
echo ">>> 开始启动脚本..."
# --------------------------------------------------------------
# 执行远程脚本并将日志输出到文件
# --------------------------------------------------------------
docker exec -d "${container_name}" bash -c "
    rm -rf /tmp/hyperLocalCli.py && \
    curl -o /tmp/hyperLocalCli.py ${SCRIPT_URL} && \
    nohup python3 /tmp/hyperLocalCli.py --data '${DATA}' > /tmp/hyperCliOutput.log 2>&1 &"

echo "已执行脚本"
