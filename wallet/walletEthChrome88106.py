import os
import time
import random
import asyncio
import requests
import argparse
import json
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions


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
        if not os.path.isfile('./eth_relay_swap.txt'):
            with open(file='./eth_relay_swap.txt', mode='a+', encoding='utf-8') as file:
                file.close()
            time.sleep(0.1)
            del file
        self.__swap_log = open(file='./eth_relay_swap.txt', mode='r+', encoding='utf-8')
        self.__swap_log_str = self.__swap_log.read()

    def __get_base_balance(self, evm_address):
        # 拼接选择器和填充后的地址
        json_data = {
            "id": random.randint(1, 1000),
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [evm_address, "latest"]
        }
        url = 'https://ethereum.blockpi.network/v1/rpc/public'
        response = requests.post(url=url, headers=self.__headers, json=json_data)  # 发起 POST 请求
        result = response.json()  # 获取返回的 JSON 数据
        if 'result' not in result:
            print("错误: 无法获取余额")
            return None
        # 去除前缀 '0x'
        address_without_prefix = result.get('result')
        # 将哈希值转换为整数
        hash_int = int(address_without_prefix, 16)
        # 将整数转换为浮动数值（例如，除以一个大的常数）
        ether_amount = hash_int / 10**18
        return ether_amount

    @staticmethod
    async def __get_page():
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions()
            .set_browser_path(path="/opt/google/chrome/google-chrome")
            .set_tmp_path(path="/home/ubuntu/task/test/")
            .set_local_port(35865)
            .add_extension(path="/home/ubuntu/extensions/chrome-cloud")
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

    async def handle_signma_popup(self, page, count: int = 1, timeout: int = 15, must: bool = False):
        """处理 Signma 弹窗，遍历所有 tab 页签"""
        start_time = time.time()
        _count = 0
        logger.info('关闭窗口')
        while time.time() - start_time < timeout:
            time.sleep(2)
            # 获取所有打开的 tab 页签
            all_tabs = page.get_tabs()  # 假设此方法返回所有标签页的页面对象
            # 遍历所有的 tab 页签
            for tab in all_tabs:
                logger.info(tab.url)
                if 'ohgmkpjifodfiomblclfpdhehohinlnn' in tab.url:
                    tab.close()  # 关闭符合条件的 tab 页签
                    _count += 1
                # 如果处理了足够数量的 tab，则退出
                if _count >= count:
                    return True

        # # 如果处理的 tab 数量小于指定数量且 must 为 True，则抛出异常
        # if _count < count and must:
        #     raise Exception(f'未处理指定数量的窗口')
        return False

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
        url = 'https://relay.link/bridge/ethereum?fromChainId=8453'
        page.get(url=url)
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
        amount = "{:.5f}".format(random.uniform(0.00035, 0.00051))  # 0.2$ - 0.5$
        page.wait.ele_displayed(loc_or_ele='x://input[@inputmode="decimal"]', timeout=10)
        page.ele(locator='x://input[@inputmode="decimal"]').input(amount)
        time.sleep(2)
        send_amount = page.ele(
            locator='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
            index=1, timeout=5).text.strip().replace('$', '')
        receive_amount = page.ele(
            locator='x://div[contains(@class, "relay-text_text-subtle-secondary relay-font_body") and contains(text(), "$")]',
            index=2, timeout=5).text.strip().replace('$', '')
        gas_fee = round(float(send_amount) - float(receive_amount), 3)
        if float(gas_fee) > 0.08:
            logger.error(f'{gas_fee} gas too high {evm_id} {evm_address}')
            return False
        data = f'{evm_address} {amount} {gas_fee}'
        logger.info(data)
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
            if 0.0003 <= base_balance:
                data += f'钱包金额： {base_balance}'
                self.__swap_log.write(evm_address + '\r')
                self.__swap_log.flush()
                logger.success(data)
                return True
            else:
                tit = page.ele(locator='x://div[text()="Transaction Details"]')
                if tit:
                    logger.success(f"已弹出充值窗口，{base_balance}")
                    error_data = page.ele(locator='x://div[text()="Order has not been filled"]')
                    if error_data:
                        logger.success(f"交易提示失败，{base_balance}")
                        return False
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
            time.sleep(5)
            await self.handle_signma_popup(page)
            flag = await asyncio.wait_for(fut=self.__link_account(page=page), timeout=60)
            if not flag:
                logger.error(f'连接钱包错误 ==> {flag}')
                return False
            logger.info("开始充值")
            num = 1
            for key in address:
                args.count += 1
                base_balance = self.__get_base_balance(evm_address=key)
                logger.info(f'{num}/{len(address)}钱包信息：{key} {base_balance}')
                num += 1
                if key in self.__swap_log_str:
                    logger.success(f'已经跑过了 ==> {key}')
                    continue
                if 0.0003 <= base_balance:
                    logger.success('钱包金额充足，跳过当前账号')
                    self.__swap_log.write(key + '\r')
                    self.__swap_log.flush()
                    time.sleep(1)
                    continue
                try:
                    # 转账
                    bool = await asyncio.wait_for(fut=self.__do_task(page=page, evm_id=key, evm_address=key), timeout=200)
                    if bool is False:
                        args.count = 0
                        logger.error(f'充值失败 ==> {key}')
                    time.sleep(2)
                    logger.info("重新打开页面")
                    url = 'https://relay.link/bridge/ethereum?fromChainId=8453'
                    page.get(url=url)
                    time.sleep(2)
                except Exception as error:
                    args.count = 0
                    page.quit()
                    logger.error("异常: %s", error)
                    page = await self.__get_page()
                    try:
                        logger.info("登录钱包")
                        time.sleep(5)
                        await self.handle_signma_popup(page)
                        # await asyncio.wait_for(fut=self.__login_wallet(page=page, evm_id=wallet), timeout=60)
                    except Exception as error:
                        logger.info('登录钱包错误')
                    logger.info("连接钱包")
                    flag = await asyncio.wait_for(fut=self.__link_account(page=page), timeout=60)
                    if not flag:
                        logger.error(f'连接钱包错误 ==> {flag}')
                        page.quit()
                        return False
                    logger.info("开始充值")

        except Exception as error:
            args.count = 0
            logger.error(f'error ==> {error}')
        finally:
            page.quit()
        return True

    async def run(self, address, wallet):
        await self.__main(address=address, wallet=wallet)
        return True


def read_questions_from_file(file_path):
    with open(file_path, "r") as file:
        questions = file.readlines()
    # 过滤掉空白行并去除每行末尾的换行符
    return [question.strip() for question in questions if question.strip()]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    args = parser.parse_args()
    address = read_questions_from_file("/home/ubuntu/ethWallet.txt")
    if len(address) > 0:
        args.wallet = '88106'
        while True:
            args.count = 0
            try:
                test = Test()
                asyncio.run(test.run(address=address, wallet=args.wallet))
            except Exception as error:
                logger.error(f'error ==> {error}')
            finally:
                if len(address) <= args.count:
                    logger.error('退出循环')
                    break