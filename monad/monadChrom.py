import uuid
import asyncio
import requests
import subprocess
import os
import signal
from DrissionPage._pages.chromium_page import ChromiumPage
import time
from DrissionPage._configs.chromium_options import ChromiumOptions
import paho.mqtt.client as mqtt
import json
import argparse
from loguru import logger
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


# =================================================   MQTT   ======================================
def create_mqtt_client(broker, port, username, password, topic):
    """
    创建并配置MQTT客户端，使用 MQTTv5 回调方式
    protocol=mqtt.MQTTv5 来避免旧版回调弃用警告
    """
    client = mqtt.Client(
        protocol=mqtt.MQTTv5,  # 指定使用 MQTTv5
        userdata={"topic": topic}  # 传递自定义数据
    )
    client.username_pw_set(username, password)

    # 注册回调函数（使用 v5 风格签名）
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        raise ConnectionError(f"Error connecting to broker: {e}")

    return client


# ========== MQTT 事件回调函数（MQTTv5） ==========
def on_connect(client, userdata, flags, reason_code, properties=None):
    """
    当客户端与 Broker 建立连接后触发
    reason_code = 0 表示连接成功，否则为失败码
    """
    if reason_code == 0:
        print("Connected to broker successfully.")
        # 仅发布消息，去除订阅
        pass
    else:
        print(f"Connection failed with reason code: {reason_code}")


def on_disconnect(client, userdata, reason_code, properties=None):
    """
    当客户端与 Broker 断开连接后触发
    可以在此处进行自动重连逻辑
    """
    print(f"Disconnected from broker, reason_code: {reason_code}")
    # 如果 reason_code != 0，则表示非正常断开
    while True:
        try:
            print("Attempting to reconnect...")
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # 等待 5 秒后重试


def on_message(client, userdata, msg):
    """
    当收到订阅主题的新消息时触发
    v5 中的 on_message 参数与 v3.x 相同： (client, userdata, message)
    """
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")


# =================================================   MQTT   ======================================


def read_file(file_path):
    """从文件中读取内容并去除多余空白"""
    try:
        # logger.info(f"读取文件: {file_path}")
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError(f"文件未找到: {file_path}")


def decrypt_aes_ecb(secret_key, data_encrypted_base64, key):
    """
    解密 AES ECB 模式的 Base64 编码数据，
    去除 PKCS7 填充后返回所有 accountType 为 "hyper" 的记录中的指定 key 值列表。
    """
    try:
        # Base64 解码
        encrypted_bytes = base64.b64decode(data_encrypted_base64)
        # 创建 AES 解密器
        cipher = AES.new(secret_key.encode('utf-8'), AES.MODE_ECB)
        # 解密数据
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        # 去除 PKCS7 填充（AES.block_size 默认为 16）
        decrypted_bytes = unpad(decrypted_bytes, AES.block_size)
        # 将字节转换为字符串
        decrypted_text = decrypted_bytes.decode('utf-8')

        # logger.info(f"获取数据中的 {key}: {decrypted_text}")

        # 解析 JSON 字符串为 Python 对象（通常为列表）
        data_list = json.loads(decrypted_text)

        # 创建结果列表，收集所有匹配的 key 值
        result = []
        for item in data_list:
            if item.get('accountType') == 'monad':
                value = item.get(key)
                if value is not None:  # 确保只添加存在的 key 值
                    result.append(value)

        # 返回结果列表，如果没有匹配项则返回空列表
        return result

    except Exception as e:
        raise ValueError(f"解密失败: {e}")

class Test(object):

    def __init__(self):
        if not os.path.isfile('./monad_faucet.txt'):
            with open(file='./monad_faucet.txt', mode='a+', encoding='utf-8') as file:
                file.close()
            time.sleep(0.1)
            del file
        self.__monad_faucet = open(file='./monad_faucet.txt', mode='r+', encoding='utf-8')
        self.__monad_faucet_str = self.__monad_faucet.read()

    @staticmethod
    async def __get_page():
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions().set_tmp_path(
                path='/home/ubuntu/task/TempFile').auto_port().headless(on_off=False))
        page.wait.doc_loaded(timeout=30)
        page.set.window.max()
        return page

    # 点击元素
    @staticmethod
    async def __click_ele(page, xpath: str = '', find_all: bool = False, index: int = -1) -> int:
        loop_count = 0
        while True:
            try:
                if not find_all:
                    page.ele(locator=xpath).click()
                else:
                    page.eles(locator=xpath)[index].click()
                break
            except Exception as e:
                error = e
                pass
            if loop_count >= 5:
                # print(f'---> {xpath} 无法找到元素。。。', str(error)[:100])
                page.quit()
                return 0
            loop_count += 1
            await asyncio.sleep(2)
        return 1

    @staticmethod
    def __get_monad_balance(evm_address):
        headers = {
            'authority': 'monad-testnet.g.alchemy.com',
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/json',
            'origin': 'chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'none',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        }

        json_data = {
            'id': str(uuid.uuid4()),
            'jsonrpc': '2.0',
            'method': 'eth_getBalance',
            'params': [
                evm_address,
                'latest',
            ],
        }
        url = 'https://monad-testnet.g.alchemy.com/v2/nR72bxK2nIiUl42EDVpqbNDDTo0yyGDX'
        response = requests.post(url=url, headers=headers, json=json_data)
        balance = int(response.json()['result'], 16) / (10 ** 18)
        return balance

    async def __do_task(self, page, evm_id, evm_address):
        url = 'https://testnet.monad.xyz/?chain=monad-testnet&inputCurrency=native&outputCurrency=DAK'
        page.get(url=url)
        await asyncio.sleep(5)
        page.wait.ele_displayed(loc_or_ele='x://button[@aria-label="Accept terms and conditions"]', timeout=10)
        await self.__click_ele(page=page, xpath='x://button[@aria-label="Accept terms and conditions"]')
        await asyncio.sleep(2)
        await self.__click_ele(page=page, xpath='x://button[text()="Continue"]')
        page.run_js('window.scroll(0, 1000)')
        page.ele(locator='x://input[@type="text"]').input(evm_address)
        await asyncio.sleep(3)
        ele = page.ele(locator='x://div[contains(@class, "wallet-address-container")]/div[last()]/div').shadow_root.child().ele(locator='x://body').shadow_root.ele('x:./div/div/div')
        if ele.html.count('<input type="checkbox">'):
            ele.ele('x://label/input').click()
            await asyncio.sleep(3)
        await self.__click_ele(page=page, xpath='x://button[text()="Get Testnet MON"]')
        await asyncio.sleep(10)
        monad_balance = self.__get_monad_balance(evm_address=evm_address)
        data = f'{evm_id} {evm_address} {monad_balance}'
        if monad_balance:
            self.__monad_faucet.write(data + '\r')
            self.__monad_faucet.flush()
            logger.success(f'领水成功 ==> {data}')
            client.publish("appInfo", json.dumps(get_app_info_integral(monad_balance)))
        else:
            logger.error(f'领水失败 ==> {data}')
            client.publish("appInfo", json.dumps(get_app_info()))
        return data

    async def __main(self, evm_id, evm_address) -> bool:
        page = await self.__get_page()
        try:
            await asyncio.wait_for(fut=self.__do_task(page=page, evm_id=evm_id, evm_address=evm_address), timeout=60)
        except Exception as error:
            logger.error(f'error ==> {error}')
            ...
        finally:
            page.quit()
        return True

    async def run(self, evm_id, evm_address):
        await self.__main(evm_id=evm_id, evm_address=evm_address)
        return True


def get_app_info_integral(integral):
    return {
        "serverId": f"{args.serverId}",
        "applicationId": f"{args.appId}",
        "publicKey": f"{args.address}",
        "integral": f"{integral}",
        "operationType": "2",
        "description": f"领水成功,积分：{integral}",
    }

def get_app_info():
    return {
        "serverId": f"{args.serverId}",
        "applicationId": f"{args.appId}",
        "publicKey": f"{args.address}",
        "operationType": "3",
        "description": f"领水失败",
    }

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    parser.add_argument("--chromePort", type=str, help="浏览器端口", required=True)
    args = parser.parse_args()

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + args.appId + '_user.json')
    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(args.decryptKey, encrypted_data_base64, 'publicKey')

    index = 0

    if len(public_key_tmp) > 0:
        logger.info(f"发现账号{public_key_tmp}")
        while True:
            try:
                if index >= len(public_key_tmp):
                    index = 0
                logger.info(f"开始执行{public_key_tmp[index]}")
                args.index = index
                args.address = public_key_tmp[index]
                test = Test()
                asyncio.run(test.run(evm_id=args.index, evm_address=args.address))
                logger.info(f"执行完毕等待12小时10分")
                time.sleep(43800)
            except Exception as e:
                logger.info(f"发生错误,使用kill杀掉浏览器: {e}")
                try:
                    # 获取占用 9518 端口的 PID
                    pids = subprocess.getoutput("lsof -t -i:"+args.chromePort+" -sTCP:LISTEN")
                    if pids:
                        pid_list = pids.splitlines()  # 按行分割 PID
                        print(f"找到占用 {args.chromePort} 端口的进程: {pid_list}")
                        for pid_str in pid_list:
                            try:
                                pid = int(pid_str.strip())  # 转换为整数并移除多余空格
                                os.kill(pid, signal.SIGKILL)
                                logger.info(f"成功终止进程 {pid}")
                                time.sleep(1)  # 每次杀死后等待 1 秒
                            except PermissionError:
                                logger.info(f"无权限终止进程，请检查进程所有者和 admin 用户权限")
                            except ValueError:
                                logger.info(f"无效 PID: {pid_str}")
                            except Exception as e:
                                logger.info(f"发生错误: {e}")
                    else:
                        logger.info(f"{args.chromePort} 端口未被占用")
                except Exception as e:
                    print(f"错误关闭: {e}")
    else:
        logger.info("未绑定需要执行的账号")
