#!/bin/bash
set -e

# 检查是否传入了参数
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <DATA> <ip_suffix>"
    exit 1
fi

# 传递的参数数据
DATA="$1"
ip_suffix="$2"

# 自定义镜像名称
IMAGE_NAME="unbutu:node"

# 远程脚本的URL
SCRIPT_URL="https://www.15712345.xyz/shell/hyper/hyperLocalCli.py"

container_name="node${ip_suffix}"

echo ">>> 检查容器: ${container_name}"
echo "    - 容器端口: ${ip_suffix}"



# 检查容器是否存在并已启动
if ! docker ps -a --format '{{.Names}}' | grep -q "${container_name}"; then
    echo "容器 ${container_name} 不存在，创建并启动容器..."
    # 启动 Docker 容器
    docker run -d \
        --name "${container_name}" \
        -p "${ip_suffix}:2222" \
        ${IMAGE_NAME}
else
    echo "容器 ${container_name} 已存在"
    # 检查容器是否已启动，如果已启动，跳过创建
    if ! docker ps --format '{{.Names}}' | grep -q "${container_name}"; then
        echo "容器 ${container_name} 已存在，但未启动，正在启动..."
        docker start "${container_name}"
    fi
fi


sleep 5 
echo ">>> 开始启动脚本..."
# --------------------------------------------------------------
# 执行远程脚本并将日志输出到文件
# --------------------------------------------------------------
docker exec -d "${container_name}" bash -c "
    rm -rf /opt/hyperCloudCli.py && \
    curl -o /opt/hyperCloudCli.py ${SCRIPT_URL} && \
    nohup python3 /opt/hyperCloudCli.py --data '${DATA}' > /opt/hyperCloudCli.log 2>&1 &"

echo "已执行脚本"
