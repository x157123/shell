import os
import time
import random
import asyncio
import requests
import argparse
from loguru import logger
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import paho.mqtt.client as mqtt
import json
import traceback
from DrissionPage import ChromiumPage, ChromiumOptions


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


def decrypt_aes_ecb(secret_key, data_encrypted_base64, accountType):
    """
    解密 AES ECB 模式的 Base64 编码数据，
    去除 PKCS7 填充后返回所有 accountType 为 "hyper" 的记录。
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

        # 解析 JSON 字符串为 Python 对象（通常为列表）
        data_list = json.loads(decrypted_text)

        # 创建结果列表，收集所有 accountType 为 "hyper" 的记录
        result = [item for item in data_list if item.get('accountType') == accountType]

        # 返回结果列表，如果没有匹配项则返回空列表
        return result
    except Exception as e:
        # 记录错误日志
        logger.error(f"解密失败: {e}")
        return []


class Test(object):

    def __init__(self):
        self.__headers = {
            'authority': 'mainnet.base.org',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://ct.app',
            'referer': 'https://ct.app/',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        }
        if not os.path.isfile('./gaia_relay_swap.txt'):
            with open(file='./gaia_relay_swap.txt', mode='a+', encoding='utf-8') as file:
                file.close()
            time.sleep(0.1)
            del file
        self.__swap_log = open(file='./gaia_relay_swap.txt', mode='r+', encoding='utf-8')
        self.__swap_log_str = self.__swap_log.read()

    def __get_base_balance(self, evm_address):
        json_data = {
            'jsonrpc': '2.0',
            'id': random.randint(1, 1000),
            'method': 'eth_getBalance',
            'params': [
                evm_address.lower(),
                'latest',
            ],
        }
        url = 'https://mainnet.base.org/'
        response = requests.post(url=url, headers=self.__headers, json=json_data)
        result = response.json()
        base_balance = int(result.get('result'), 16) / (10 ** 18)
        return base_balance

    @staticmethod
    async def __get_page():
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_browser_path(path="/opt/google/chrome/google-chrome")
            .set_tmp_path(path="/home/" + args.user + "/task/" + args.chromePort + "/" + args.wallet)
            .set_local_port(args.chromePort)
            .add_extension(path="/home/" + args.user + "/extensions/chrome-cloud")
            .headless(on_off=False))
        page.wait.doc_loaded(timeout=30)
        page.set.window.max()
        await asyncio.sleep(5)
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

    # task 01 登陆钱包
    async def __login_wallet(self, page, evm_id):
        tab = page.get_tab(url='chrome-extension://')
        await asyncio.sleep(2)
        url = tab.url
        try:
            # 输入钱包编号
            tab.ele(locator='x://input').input(f'{int(evm_id)}')
        except:
            return False
        time.sleep(3)
        # 点击登录钱包
        await self.__click_ele(page=tab, xpath='x://*[@id="existingWallet"]')
        await asyncio.sleep(3)
        # tab = page.get_tab(url='https://ntp.msn.com/edge/ntp')
        page.get(url.replace('tab.html#/onboarding', 'popup.html'))
        await asyncio.sleep(5)
        if page.ele('x://button[@data-testid="toggle"]').attr('aria-checked') == 'false':
            await self.__click_ele(page=page, xpath='x://button[@data-testid="toggle"]')
            await asyncio.sleep(2)
        return evm_id

    # 处理弹窗
    async def __deal_window(self, page):
        # 如果窗口大于2才进行操作
        if page.tabs_count >= 2:
            await asyncio.sleep(3)
            tab = page.get_tab()
            if '/popup.html?page=%2Fdapp-permission' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    await self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    await asyncio.sleep(1)
                await self.__click_ele(page=tab, xpath='x://button[@id="grantPermission"]')
                await asyncio.sleep(2)

            elif '/notification.html#connect' in tab.url:
                await self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                await self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                await asyncio.sleep(2)

            elif '/notification.html#confirmation' in tab.url:
                await self.__click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                await asyncio.sleep(2)
                await self.__click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                await asyncio.sleep(2)

            elif '/notification.html#confirm-transaction' in tab.url:
                await self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                await asyncio.sleep(2)

            elif '/popup.html?page=%2Fsign-transaction' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    await self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    await asyncio.sleep(1)
                await self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                await asyncio.sleep(2)

            elif '/popup.html?page=%2Fsign-data' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    await self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    await asyncio.sleep(1)
                await self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                await asyncio.sleep(2)

            elif 'popup.html?page=%2Fpersonal-sign' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    await self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    await asyncio.sleep(1)
                await self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                await asyncio.sleep(2)

            elif ('&tab=%2Fadd-evm-chain' in tab.url) or ('/popup.html?requestId=' in tab.url):
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    await self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    await asyncio.sleep(1)
                await self.__click_ele(page=tab, xpath='x://button[@id="addNewChain"]')
                await asyncio.sleep(2)

            elif ('popout.html?windowId=backpack' in tab.url):
                await self.__click_ele(page=tab, xpath='x://div/span[text()="确认"]')
                await asyncio.sleep(2)
        return True

    # 添加网络
    async def __add_net_work(self, page, coin_name='base'):
        obj = {
            'arb': 42161,
            'base': 8453,
            'opt': 10,
        }
        number = obj[coin_name]
        url = f'https://chainlist.org/?search={number}&testnets=false'
        page.get(url=url)
        await asyncio.sleep(2)
        page.wait.ele_displayed(loc_or_ele='x://button[text()="Connect Wallet"]', timeout=10)
        await self.__click_ele(page=page,
                               xpath=f'x://td[contains(text(), "{number} ")]/../../../following-sibling::button[1]')
        await asyncio.sleep(3)
        await self.__deal_window(page=page)
        await asyncio.sleep(2)
        await self.__click_ele(page=page,
                               xpath=f'x://td[contains(text(), "{number} ")]/../../../following-sibling::button[1]')
        await asyncio.sleep(2)
        await self.__deal_window(page=page)
        if page.tabs_count >= 2:
            await self.__deal_window(page=page)
        return True

    async def __link_account(self, page):
        url = 'https://relay.link/bridge/base?fromChainId=8453&fromCurrency=0x0000000000000000000000000000000000000000&toCurrency=0x0000000000000000000000000000000000000000'
        page.new_tab(url=url)
        time.sleep(10)
        claim = page.ele('x://button/div/div[text()="Select wallet"]')
        if claim:
            await self.__click_ele(page=page, xpath='x://button/div/div[text()="Select wallet"]')
            await asyncio.sleep(3)
            page.ele(locator='x://div[@data-testid="dynamic-modal-shadow"]').shadow_root.ele(
                'x://button/div/span[text()="Signma"]').click()
            await asyncio.sleep(5)
            for _ in range(10):
                if page.tabs_count < 2:
                    break
                await self.__deal_window(page=page)
            else:
                return False
            await asyncio.sleep(3)
        return True

    async def __do_task(self, page, evm_id, evm_address):
        await self.__click_ele(page=page, xpath='x://button[@aria-label="Multi wallet dropdown"]', find_all=True,
                               index=-1)
        await self.__click_ele(page=page, xpath='x://div[text()="Paste wallet address"]')
        page.ele(locator='x://input[@placeholder="Address or ENS"]').input(evm_address)
        await self.__click_ele(page=page, xpath='x://button[text()="Save"]')
        await asyncio.sleep(2)
        amount = "{:.6f}".format(random.uniform(0.000094, 0.000235))  # 0.2$ - 0.5$
        page.wait.ele_displayed(loc_or_ele='x://input[@inputmode="decimal"]', timeout=10)
        page.ele(locator='x://input[@inputmode="decimal"]').input(amount)
        await asyncio.sleep(5)
        send_amount = page.ele(
            locator='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
            index=1, timeout=5).text.strip().replace('$', '')
        receive_amount = page.ele(
            locator='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
            index=2, timeout=5).text.strip().replace('$', '')
        gas_fee = round(float(send_amount) - float(receive_amount), 3)
        if float(gas_fee) > 0.05:
            logger.error(f'{gas_fee} gas too high {evm_id} {evm_address}')
            return False
        data = f'{evm_id} {evm_address} {amount} {gas_fee}'
        logger.error(data)
        page.wait.ele_displayed(loc_or_ele='x://button[text()="Review" or text()="Swap" or text()="Send"]', timeout=5)
        await self.__click_ele(page=page, xpath='x://button[text()="Review" or text()="Swap" or text()="Send"]')
        await asyncio.sleep(5)
        if page.tabs_count < 2:
            logger.error(f'transaction reject {evm_id} {evm_address}')
            return False
        for _ in range(10):
            if page.tabs_count < 2:
                break
            await self.__deal_window(page=page)
        else:
            return False
        await asyncio.sleep(10)
        for _ in range(30):
            base_balance = self.__get_base_balance(evm_address=evm_address)
            if 0.00009 < base_balance:
                data += f'钱包金额： {base_balance}'
                self.__swap_log.write(evm_address + '\r')
                self.__swap_log.flush()
                logger.success(data)
                return True
            else:
                logger.success(f"金额充值未成功{base_balance}")
            await asyncio.sleep(5)
        else:
            logger.error(data)
        return False

    async def __main(self, address, wallet) -> bool:
        page = await self.__get_page()
        try:
            logger.info("登录钱包")
            await asyncio.wait_for(fut=self.__login_wallet(page=page, evm_id=wallet), timeout=60)
            logger.info("开始添加网络")
            await asyncio.wait_for(fut=self.__add_net_work(page=page, coin_name='base'), timeout=60)
            logger.info("连接钱包")
            flag = await asyncio.wait_for(fut=self.__link_account(page=page), timeout=60)
            if not flag:
                logger.error(f'连接钱包错误 ==> {flag}')
                return False
            logger.info("开始充值")
            num = 1
            for key in address:
                base_balance = self.__get_base_balance(evm_address=key["publicKey"])
                logger.info(f'{num}/{len(address)}钱包信息：{key["secretKey"]} {key["publicKey"]} {base_balance}')
                num += 1
                if key["publicKey"] in self.__swap_log_str:
                    logger.success(f'已经跑过了 ==> {key["secretKey"]}')
                    continue
                if 0.00009 < base_balance:
                    logger.success('钱包金额充足，跳过当前账号')
                    self.__swap_log.write(key["publicKey"] + '\r')
                    self.__swap_log.flush()
                    time.sleep(1)
                    continue
                try:
                    bool = await asyncio.wait_for(fut=self.__do_task(page=page, evm_id=key["secretKey"], evm_address=key["publicKey"]), timeout=200)
                    if bool is False:
                        logger.error(f'充值失败 ==> {key["secretKey"]} {key["publicKey"]}')
                    time.sleep(2)
                    logger.info("重新打开页面")
                    url = 'https://relay.link/bridge/base?fromChainId=8453&fromCurrency=0x0000000000000000000000000000000000000000&toCurrency=0x0000000000000000000000000000000000000000'
                    page.get(url=url)
                    time.sleep(10)
                except Exception as error:
                    page.quit()
                    logger.error("异常: %s", error)
                    page = await self.__get_page()
                    time.sleep(2)
                    page.get("chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding")
                    time.sleep(2)
                    logger.info("登录钱包1")
                    await asyncio.wait_for(fut=self.__login_wallet(page=page, evm_id=wallet), timeout=60)
                    time.sleep(10)
                    if len(page.get_tabs(title="Signma")) > 0:
                        time.sleep(3)
                        pop_tab = page.get_tab(title="Signma")
                        if pop_tab.url == 'chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding':
                            pop_tab.close()
                    logger.info("连接钱包1")
                    flag = await asyncio.wait_for(fut=self.__link_account(page=page), timeout=60)
                    if not flag:
                        logger.error(f'连接钱包错误 ==> {flag}')
                        return False

        except Exception as error:
            logger.error(f'error ==> {error}')
        finally:
            page.quit()
        return True

    async def run(self, address, wallet):
        await self.__main(address=address, wallet=wallet)
        return True

if __name__ == '__main__':
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
    public_key_tmp = decrypt_aes_ecb(args.decryptKey, encrypted_data_base64, "wallet")
    if len(public_key_tmp) > 0:
        args.wallet = '88106'
        test = Test()
        asyncio.run(test.run(address=public_key_tmp, wallet=args.wallet))
