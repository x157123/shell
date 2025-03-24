import base58
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# 输入Base58编码的私钥（请替换为您的实际私钥）
private_key_b58 = "2222222222222222222"

# 解码Base58私钥为字节
private_key_bytes = base58.b58decode(private_key_b58)

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
