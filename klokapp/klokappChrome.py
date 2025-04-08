import os
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import random
import asyncio
import argparse
import json
import pyperclip
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
from datetime import datetime, timedelta

print(time.strftime('%Y-%m-%d %H:%M:%S'))
start_time = int(time.time() * 1000)


class Test(object):

    @staticmethod
    async def __get_page(index):
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_browser_path(path="/opt/google/chrome/google-chrome")
            .add_extension(r"/home/" + args.user + "/extensions/chrome-cloud")
            .set_user_data_path("/home/" + args.user + "/task/chrome/" + index)
            .set_local_port(args.chromePort)
            .headless(on_off=False))
        page.wait.doc_loaded(timeout=30)
        page.set.window.max()
        return page

    # task 01 登陆钱包
    async def __login_wallet(self, page, evm_id):
        wallet_tab = page.new_tab(
            url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
        )
        time.sleep(3)
        index_input_path = (
            "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
        )
        wallet_tab.ele(index_input_path).input(evm_id, clear=True)
        time.sleep(3)
        index_button_path = "tag:button@@id=existingWallet"
        index_set_button = wallet_tab.ele(index_button_path)
        time.sleep(1)
        index_set_button.click()
        time.sleep(10)
        if len(page.get_tabs(title="Signma")) > 0 and page.tabs_count >= 2:
            time.sleep(8)
            pop_tab = page.get_tab(title="Signma")
            if pop_tab.url == 'chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding':
                pop_tab.ele(index_input_path).input(evm_id, clear=True)
                index_set_button = pop_tab.ele(index_button_path)
                time.sleep(1)
                index_set_button.click()
                pop_tab.close()
        time.sleep(3)

    # 点击元素
    async def __click_ele(self, page, xpath: str = '', loop: int = 5, must: bool = False, by_jd: bool = True,
                          find_all: bool = False,
                          index: int = -1) -> int:
        loop_count = 1
        while True:
            logger.info(f'查找元素{xpath}:{loop_count}')
            try:
                if not find_all:
                    logger.info(f'点击按钮{xpath}:{loop_count}')
                    page.ele(locator=xpath).click(by_js=None)
                else:
                    page.eles(locator=xpath)[index].click(by_js=None)
                break
            except Exception as e:
                error = e
                pass
            if loop_count >= loop:
                # logger.info(f'---> {xpath} 无法找到元素。。。', str(error)[:100])
                if must:
                    # page.quit()
                    raise Exception(f'未找到元素:{xpath}')
                return 0
            loop_count += 1
            # time.sleep(1)
        return 1

    # 点击元素
    async def __get_ele_value(self, page, xpath: str = '', loop: int = 5, must: bool = False):
        loop_count = 1
        while True:
            logger.info(f'查找元素{xpath}:{loop_count}')
            try:
                logger.info(f'点击按钮{xpath}:{loop_count}')
                txt = page.ele(locator=xpath)
                if txt:
                    logger.info(page.ele(locator=xpath).text)
                    return
            except Exception as e:
                error = e
                pass
            if loop_count >= loop:
                if must:
                    raise Exception(f'未找到元素:{xpath}')
                return
            loop_count += 1

    async def __input_ele(self, page, xpath: str = '', value: str = '', loop: int = 5, must: bool = False,
                          find_all: bool = False,
                          index: int = -1) -> int:
        loop_count = 0
        while True:
            try:
                if not find_all:
                    ele = page.ele(locator=xpath).input(value, clear=True)
                else:
                    page.eles(locator=xpath)[index].input(value, clear=True)
                break
            except Exception as e:
                error = e
                pass
            if loop_count >= loop:
                # logger.info(f'---> {xpath} 无法找到元素。。。', str(error)[:100])
                if must:
                    # page.quit()
                    raise Exception(f'未找到元素:{xpath}')
                return 0
            loop_count += 1
        return 1

    # 处理弹窗
    async def __deal_window(self, page):
        # 如果窗口大于2才进行操作
        if page.tabs_count >= 2:
            time.sleep(8)
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

    async def __do_task(self, page, evm_id, questions):
        logger.info("登录钱包")
        await asyncio.wait_for(fut=self.__login_wallet(page=page, evm_id=evm_id), timeout=60)
        url = 'https://klokapp.ai/'
        hyperbolic_page = page.new_tab(url=url)
        await self.__click_ele(page=hyperbolic_page, xpath='x://button[text()="Connect Wallet"]', loop=1)
        await self.__click_ele(page=hyperbolic_page, xpath='x://button//span[contains(text(), "Signma")]', loop=1)
        await self.__deal_window(page=page)
        await self.__click_ele(page=hyperbolic_page, xpath='x://button[text()="Sign in"]', loop=1)
        await self.__deal_window(page=page)
        await self.__click_ele(page=hyperbolic_page, xpath='x://button[@aria-label="Close modal"]', loop=1)
        pyperclip.copy('')
        await self.__click_ele(page=hyperbolic_page, xpath='x://button[text()="Copy Referral Link"]', loop=2)
        clipboard_text = pyperclip.paste().strip()
        print(clipboard_text)
        for i in range(15):
            # 提问
            await self.__send(page=hyperbolic_page, xpath='x://div[@class="style_loadingDots__NNnij"]',
                              value=random.choice(questions))
        # 获取积分
        await self.__get_ele_value(page=hyperbolic_page,
                                   xpath='x://div[contains(text(), "Total Mira Points")]/following-sibling::div')

    async def __send(self, page, xpath, value):
        loop_count = 0
        while True:
            try:
                ele = page.ele(locator=xpath)
                if ele:
                    time.sleep(2)
                else:
                    # 已满
                    _input = page.ele('x://textarea[@name="message" and @disabled]')
                    if _input:
                        return
                    await self.__input_ele(page=page, xpath='x://textarea[@name="message"]', value=value)
                    await self.__click_ele(page=page, xpath='x://button//img[@alt="Send message"]', loop=1)
                    return
            except Exception as e:
                error = e
                pass
            if loop_count >= 15:
                return 0
            loop_count += 1

    # div
    async def run(self, evm_id, questions):
        page = await self.__get_page(evm_id)
        await asyncio.wait_for(fut=self.__do_task(page=page, evm_id=evm_id, questions=questions), timeout=60)


def read_questions_from_file(file_path):
    with open(file_path, "r") as file:
        questions = file.readlines()
    # 过滤掉空白行并去除每行末尾的换行符
    return [question.strip() for question in questions if question.strip()]


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
        questions = read_questions_from_file("/opt/data/questions.txt")
        while True:
            current_date = datetime.now().strftime('%Y%m%d')  # 当前日期
            args.day_count = 0
            if current_date in data_map and data_map[current_date] is not None:
                args.day_count = data_map[current_date]
                logger.info(f"已标记被执行")

            now = datetime.now()
            # 早上1点后才执行
            if now.hour >= 0 and args.day_count <= 1:
                for key in public_key_tmp:
                    try:
                        args.id = key["id"]
                        args.index = key["secretKey"]
                        logger.info(f"执行: {args.index}")
                        test = Test()
                        logger.info("开始执行")
                        test.run(evm_id=args.index, questions=questions)
                    except Exception as e:
                        logger.info(f"发生错误: {e}")
                    time.sleep(random.randint(23, 50))
                logger.info(f"执行完毕")
                data_map[current_date] = args.day_count + 1
            else:
                logger.info(f"执行完毕等待一小时")
                time.sleep(3600)
    else:
        logger.info("未绑定需要执行的账号")

