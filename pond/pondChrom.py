import random
import asyncio
import os
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
from datetime import datetime, timedelta

print(time.strftime('%Y-%m-%d %H:%M:%S'))
start_time = int(time.time() * 1000)


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
            if item.get('accountType') == 'pond':
                value = item.get(key)
                if value is not None:  # 确保只添加存在的 key 值
                    result.append(value)
                    data_map[key] = item.get('password')

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

    def __get_page(self):
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions().set_browser_path(path=r"/usr/bin/microsoft-edge")
            .add_extension(r"/home/" + args.user + "/extensions/chrome-cloud")
            .set_user_data_path("/home/" + args.user + "/task/" + args.chromePort + "/" + args.index)
            .auto_port()
            .headless(on_off=False))
        page.wait.doc_loaded(timeout=30)
        page.set.window.max()
        return page

    # 点击元素
    def __click_ele(self, page, xpath: str = '', find_all: bool = False, index: int = -1) -> int:
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
            time.sleep(2)
        return 1


    def setup_wallet(self, args):
        tab = self.browser.new_tab(url="chrome://extensions/")
        time.sleep(12)
        tab.wait.ele_displayed("x://html/body/extensions-manager", 30)
        toggle_ele = (
            tab.ele(
                "x://html/body/extensions-manager"
            )  # /html/body/extensions-manager
            .shadow_root.ele('x://*[@id="viewManager"]')
            .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
            .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
            .shadow_root.ele("tag:cr-toggle@@id=enableToggle")
        )

        refresh_ele = (
            tab.ele(
                "x://html/body/extensions-manager"
            )  # /html/body/extensions-manager
            .shadow_root.ele('x://*[@id="viewManager"]')
            .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
            .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
            .shadow_root.ele("tag:cr-icon-button@@id=dev-reload-button")
        )

        if toggle_ele.attr("aria-pressed") == "false":
            toggle_ele.click()
        refresh_ele.click()
        time.sleep(6)
        if len(self.browser.get_tabs(
                url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding")) > 0:
            wallet_tab = self.browser.get_tab(
                url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
            )
        else:
            wallet_tab = self.browser.new_tab(
                url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
            )

        time.sleep(3)
        index_input_path = (
            "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
        )
        wallet_tab.ele(index_input_path).input(args.index, clear=True)
        index_button_path = "tag:button@@id=existingWallet"
        index_set_button = wallet_tab.ele(index_button_path)
        time.sleep(1)
        index_set_button.click()

        time.sleep(3)
        result = True
        return result


    async def __do_task(self, page, evm_id, evm_address):
        self.browser = page
        logger.info("开始打开钱包")
        res = self.setup_wallet(args)

        # email_url = 'https://mail.dmail.ai/inbox'
        # pond_page = page.new_tab(url=email_url)
        # await self.__click_ele(page=pond_page, xpath='x://div[@data-title="Setting"]')
        # email_span = pond_page.ele('x://p[contains(., "Default Address: ")]/span')
        # email = email_span.text
        # print(email)
        #
        # pond_url = 'https://cryptopond.xyz/points?tab=idea'
        # pond_page = page.new_tab(url=pond_url)
        # if args.passwd == '000000':
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()="Sign in"]')
        #     await self.__click_ele(page=pond_page, xpath='x://p[text()="Forgot?"]')
        #     await asyncio.sleep(5)
        #     pond_page.ele('x://input[@placeholder="Enter email"]').input(args.address, clear=True)
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()="Send email"]')
        # else:
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()="Sign up"]')
        #     pond_page.ele('x://input[@placeholder="Enter email"]').input(args.address, clear=True)
        #     await asyncio.sleep(5)
        #     await self.__click_ele(page=pond_page, xpath='x://span[contains(@class, "chakra-checkbox__control")]')
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()="Sign up"]')
        #
        # code = None
        # loop_count = 0
        # while True:
        #     email_page = page.new_tab(url='https://mail.dmail.ai/inbox')
        #     try:
        #         time.sleep(5)
        #         await self.__click_ele(page=email_page, xpath='x://span[text()="Starred"]')
        #         time.sleep(3)
        #         await self.__click_ele(page=email_page, xpath='x://span[text()="Inbox"]')
        #         time.sleep(3)
        #         await self.__click_ele(page=email_page, xpath='x://div[contains(@class, "icon-refresh")]')
        #         time.sleep(3)
        #         await self.__click_ele(page=email_page, xpath='x://div[contains(@class,"sc-eDPEul")]//ul/li[1]')
        #         time.sleep(3)
        #         # 读取验证码
        #         ele = email_page.ele(locator='x://p[contains(text(),"Your verification code is: ")]')
        #         code = ele.text.split(':')[-1].strip()
        #         print(code)
        #     except Exception as e:
        #         logger.error(f'error ==> {e}')
        #     finally:
        #         email_page.close()
        #         time.sleep(3)
        #
        #     if loop_count >= 5:
        #         page.close()
        #         return
        #     if code is None:
        #         loop_count += 1
        #         continue  # 跳到下一次循环
        #     else:
        #         pond_page.ele('x://input[@placeholder="Enter code"]').input(code, clear=True)
        #         time.sleep(2)
        #         pond_page.ele('x://input[@placeholder="Enter password"]').input("xujiaxujia123", clear=True)
        #         time.sleep(4)
        #         if args.passwd == '000000':
        #             print("重置密码")
        #             await self.__click_ele(page=pond_page, xpath='x://button[text()="Reset password"]')
        #         else:
        #             print("提交")
        #             await self.__click_ele(page=pond_page, xpath='x://button[text()="Join Pond"]')
        #         break
        #
        # time.sleep(2)
        # pond_page.ele('x://input[@placeholder="Enter email"]').input(args.address, clear=True)
        # time.sleep(2)
        # pond_page.ele('x://input[@placeholder="Enter password"]').input("xujiaxujia123", clear=True)
        # time.sleep(2)
        # await self.__click_ele(page=pond_page, xpath='x://button[text()="Sign in"]')
        # if pond_page.ele('x://button[text()=" Continue"]'):
        #     time.sleep(2)
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()=" Continue"]')
        #     time.sleep(2)
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()=" Continue"]')
        #     time.sleep(2)
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()="Got It"]')
        #     time.sleep(2)
        #
        #
        # # # Common
        # await self.__click_ele(page=pond_page, xpath='x://p[text()="Common"]')
        # go_in = pond_page.ele('x://span[text()="Complete Profile Information"]/ancestor::div[2]/following-sibling::div//button')
        # if go_in:
        #     time.sleep(2)
        #     await self.__click_ele(page=pond_page, xpath='x://span[text()="Complete Profile Information"]/ancestor::div[2]/following-sibling::div//button')
        #     time.sleep(2)
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()="Save"]')
        #     time.sleep(2)
        #     pond_page.get(url=pond_url)
        #     time.sleep(2)
        #
        #
        # # idea Propose an Idea
        # await self.__click_ele(page=pond_page, xpath='x://p[text()="Idea"]')
        # go_in = pond_page.ele('x://span[text()="Propose an Idea"]/ancestor::div[2]/following-sibling::div//button')
        # if go_in:
        #     await self.__click_ele(page=pond_page, xpath='x://span[text()="Propose an Idea"]/ancestor::div[2]/following-sibling::div//button')
        #     pond_page.ele('x://input[@placeholder="Enter the title of your model idea"]').input("SmartFormAI: AI-Powered Intelligent Form Autofill and Data Extraction", clear=True)
        #     pond_page.ele('x://textarea[@placeholder="Enter a brief summary of your model idea"]').input("SmartFormAI is an AI model designed to automate form-filling processes and extract structured data from various document types. Leveraging natural language processing (NLP) and computer vision, this model can understand and interpret input fields, extract relevant user information, and accurately populate forms across web and desktop applications. The model is particularly useful for automating repetitive form submissions, enhancing data entry efficiency, and integrating with enterprise-level workflows.", clear=True)
        #     await self.__click_ele(page=pond_page, xpath='x://div[@class="ProseMirror bn-editor bn-default-styles"]')
        #     pond_page.actions.type("SmartFormAI is an AI model that combines OCR (Optical Character Recognition), NLP, and deep learning-based entity recognition to automatically fill out forms and extract structured information. The model follows these key steps:")
        #     pond_page.actions.type("Document and Form Detection:")
        #     pond_page.actions.type("Uses computer vision to identify form structures in images, PDFs, or digital forms.")
        #     pond_page.actions.type("Recognizes input fields, labels, and section titles using OCR and layout analysis.")
        #     pond_page.actions.type("Data Extraction and Interpretation:")
        #     pond_page.actions.type("Analyzes provided text (e.g., user profile, ID cards, invoices) to extract relevant details.")
        #     pond_page.actions.type("Uses NLP-based Named Entity Recognition (NER) to classify fields (e.g., name, address, email, etc.).")
        #     pond_page.actions.type("Intelligent Form-Filling:")
        #     pond_page.actions.type("Maps extracted data to corresponding fields using contextual understanding.")
        #     pond_page.actions.type("Auto-fills fields dynamically, ensuring accuracy and format compliance.")
        #     pond_page.actions.type("Supports learning from user interactions to improve accuracy over time.")
        #     pond_page.actions.type("Integration & Automation:")
        #     time.sleep(2)
        #     await self.__click_ele(page=pond_page, xpath='x://button[text()="Save"]')
        #     time.sleep(2)
        #     pond_page.get(url=pond_url)
        #     time.sleep(2)
        #
        # # idea Propose an Idea
        # await self.__click_ele(page=pond_page, xpath='x://p[text()="Idea"]')
        # go_in = pond_page.ele('x://span[text()="Vote on an Idea"]/ancestor::div[2]/following-sibling::div//button')
        # if go_in:
        #     time.sleep(3)
        #     await self.__click_ele(page=pond_page, xpath='x://span[text()="Vote on an Idea"]/ancestor::div[2]/following-sibling::div//button')
        #     time.sleep(3)
        #     await self.__click_ele(page=pond_page, xpath='x://div[contains(@class, "css-1mfyor6")]')
        #     time.sleep(3)


    def __main(self, evm_id, evm_address) -> bool:
        page = self.__get_page()
        self.__do_task(page=page, evm_id=evm_id, evm_address=evm_address)
        return True

    def run(self, evm_id, evm_address):
        self.__main(evm_id=evm_id, evm_address=evm_address)
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
    data_map = {}

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()


    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + args.appId + '_user.json')
    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(args.decryptKey, encrypted_data_base64, 'secretKey')

    if len(public_key_tmp) > 0:
        logger.info(f"发现账号{public_key_tmp}")
        while True:
            current_date = datetime.now().strftime('%Y%m%d')  # 当前日期
            args.day_count = 0
            if current_date in data_map and data_map[current_date] is not None:
                args.day_count = data_map[current_date]
                logger.info(f"已标记被执行")
            if args.day_count <= 1:
                num = 0
                for key in public_key_tmp:
                    num = 1
                    args.index = key
                    logger.info(f"执行: {key}")

                    test = Test()
                    args.address = "0"
                    args.passwd = "yhy000@001yhy"
                    logger.info("开始执行")
                    test.run(evm_id=args.index, evm_address=args.address)

                    #
                    # try:
                    #     test = Test()
                    #     args.address = "0"
                    #     args.passwd = "yhy000@001yhy"
                    #     logger.info("开始执行")
                    #     asyncio.run(test.run(evm_id=args.index, evm_address=args.address))
                    # except Exception as e:
                    #     logger.info(f"发生错误: {e}")
                    time.sleep(random.randint(23, 50))
                    break
                logger.info(f"执行完毕")
                data_map[current_date] = 2
            else:
                logger.info(f"执行完毕等待一小时")
                time.sleep(3600)
    else:
        logger.info("未绑定需要执行的账号")
