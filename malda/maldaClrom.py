import os
import time
import uuid
import asyncio
import argparse
import requests
import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
from datetime import datetime


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
        logger.info('monad_faucet')

    @staticmethod
    async def __get_page():
        page = ChromiumPage(addr_or_opts=ChromiumOptions()
                            .set_local_port(args.chromePort)
                            .set_paths(r"/opt/google/chrome/google-chrome")
                            .add_extension(r"/home/" + args.user + "/extensions/chrome-cloud")
                            .headless(on_off=False))
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

    async def __do_task(self, page):
        time.sleep(15)
        if len(page.get_tabs(title="Signma")) > 0:
            time.sleep(3)
            pop_tab = page.get_tab(title="Signma")
            if pop_tab.url == 'chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding':
                pop_tab.close()
        url = 'https://testnet.malda.xyz/faucet/'
        page.get(url=url)
        num = 1
        for key in public_key_tmp:
            logger.info(f"执行第{len(public_key_tmp)}/{num}个账号: {key['secretKey']}：{key['publicKey']}")
            try:
                page.refresh()
                time.sleep(5)
                page.ele(locator='x://input[@placeholder="Enter your wallet address"]').input(key["publicKey"], clear=True)
                time.sleep(3)
                await self.__click_ele(page=page, xpath='x://p[text()="Optimism"]')
                time.sleep(10)
                claim = page.ele('x://button[text()="Claim "]')
                if claim:
                    await self.__click_ele(page=page, xpath='x://button[text()="Claim "]')
                    logger.info(f"点击第一个按钮")
                    time.sleep(15)
                    await self.__click_ele(page=page, xpath='x://p[text()="Linea"]')
                    time.sleep(10)
                    claim = page.ele('x://button[text()="Claim "]')
                    if claim:
                        await self.__click_ele(page=page, xpath='x://button[text()="Claim "]')
                        time.sleep(30)
                        logger.info(f"点击第二个按钮")
                        await self.__click_ele(page=page, xpath='x://p[text()="Ethereum"]')
                        time.sleep(3)
                        claim = page.ele('x://button[text()="Claim "]')
                        if claim:
                            await self.__click_ele(page=page, xpath='x://button[text()="Claim "]')
                            logger.info(f"点击第三个按钮")
                            time.sleep(150)
            except Exception as error:
                logger.error(f'error ==> {error}')
            finally:
                num += 1
    async def __main(self) -> bool:
        page = await self.__get_page()
        try:
            await asyncio.wait_for(fut=self.__do_task(page=page), timeout=60)
        except Exception as error:
            logger.error(f'error ==> {error}')
        finally:
            page.quit()
        return True

    async def run(self):
        await self.__main()
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

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + args.appId + '_user.json')
    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(args.decryptKey, encrypted_data_base64, "pond")

    if len(public_key_tmp) > 0:
        for key in public_key_tmp:
            logger.info(f"发现账号{key['secretKey']}")
        while True:
            current_date = datetime.now().strftime('%Y%m%d')  # 当前日期
            args.day_count = 0
            if current_date in data_map and data_map[current_date] is not None:
                args.day_count = data_map[current_date]
                logger.info(f"已标记被执行")
            # 早上6点后才执行
            now = datetime.now()
            if now.hour >= 7 and args.day_count <= 1:
                now = datetime.now()
                test = Test()
                asyncio.run(test.run())
                data_map[current_date] = 2
            else:
                logger.info(f"执行完毕等待一小时")
                time.sleep(3600)
    else:
        logger.info("未绑定需要执行的账号")