import csv
import json
import zlib
import base64
import subprocess
import base58
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


# 文件路径
# csv_file_path = '/root/hyperClis.csv'
csv_file_path = 'C://Users/liulei/Desktop/data/hyperCli.csv'

def compress_data(data):
    # 校验字符串是否正常
    set_pem_data(data)
    # 将字典转换为 JSON 字符串
    json_str = json.dumps(data)
    # 压缩 JSON 字符串（生成 bytes）
    compressed = zlib.compress(json_str.encode('utf-8'))
    # 将压缩后的 bytes 编码成 base64 字符串，便于传输和保存
    compressed_b64 = base64.b64encode(compressed).decode('utf-8')
    return compressed_b64


def set_pem_data(data):
    # 首先判断 data 是否有 remarks 属性，并且 remarks 是字符串类型
    if 'remarks' in data and isinstance(data['remarks'], str) and data['remarks'].strip():
        # 如果存在且去除空白后非空字符串，就执行相应逻辑
        print("remarks 属性存在且有效:", data['remarks'])
        # 这里可以加入其他的处理逻辑
    else:
        print(f"remarks 属性不存在或者为空/仅含空格{data['remarks']}")

        # 解码Base58私钥为字节
        private_key_bytes = base58.b58decode(data['private_key'])

        # 从私钥字节创建Ed25519私钥对象
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)

        # 从私钥生成公钥
        public_key = private_key.public_key()

        # 序列化为PKCS8格式的PEM文件（包含私钥信息）
        pem_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # 序列化为X.509格式的PEM文件（包含公钥信息）
        pem_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # 去掉PEM头尾并提取Base64编码的内容
        private_key_base64 = pem_private_key.decode('ascii').strip().split('\n')[1:-1]  # Remove BEGIN and END lines
        public_key_base64 = pem_public_key.decode('ascii').strip().split('\n')[1:-1]  # Remove BEGIN and END lines


        # 输出合并后的Base64结果
        private_str = ''.join(private_key_base64)
        public_str = ''.join(public_key_base64)


        output_private_str = "MFECAQEw" + private_str[8:]
        output_public_str = "gS" + public_str[14:]
        begin_str = "-----BEGIN PRIVATE KEY-----"
        end_str = "-----END PRIVATE KEY-----"

        public_key_pem = begin_str + "\n" + output_private_str + "\n" + output_public_str + "\n" + end_str

        print(public_key_pem)
        data['remarks'] = public_key_pem




# 函数：启动容器应用
def run_shell_script(data, ip_suffix, network_segment, proxy):
    # 定义脚本路径
    script_path = '/root/runNode.sh'

    # 调用 shell 脚本并传递参数
    try:
        result = subprocess.run([script_path, data, str(ip_suffix), str(network_segment), str(proxy)], check=True, capture_output=True, text=True)

        # 获取脚本的输出
        print("Shell script output:")
        print(result.stdout)

        # 获取脚本的错误输出（如果有）
        if result.stderr:
            print("Shell script error output:")
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running the script: {e}")
        print(f"Return code: {e.returncode}")
        print(f"Error output: {e.stderr}")


data_list = []
with open(csv_file_path, mode='r', encoding='utf-8-sig') as f:
    # 使用 DictReader 可以按表头读出字段名对应的值
    reader = csv.DictReader(f)
    for row in reader:
        # 排除空行（检查字典中是否存在有效数据）
        if any(row.values()):  # 如果有任何字段的值非空
            # row 是一个字典，例如 {"id": "1", "public_key": "public_key_1", "private_key": "...", "remarks": "..."}
            data_list.append(row)

# 主程序
for item in data_list:
    data = compress_data(item)
    run_shell_script(data, item['id'], item['network_segment'], item['proxy'])
