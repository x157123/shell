import time
import asyncio

import argparse
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions


class Test(object):

    @staticmethod
    async def __get_page(index, port, user):
        page = ChromiumPage(
            addr_or_opts=ChromiumOptions().set_browser_path(path=r"/usr/bin/microsoft-edge")
            .add_extension(r"/home/" + user + "/extensions/chrome-cloud")
            .add_extension(r"/home/" + user + "/extensions/keplr")
            .set_user_data_path("/home/" + user + "/edge/" + index)
            .auto_port()
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
                return 0
            loop_count += 1
            await asyncio.sleep(2)
        return 1

    # 设置钱包
    async def open_wallet(self, page, union_address, text):
        try:
            url = 'chrome-extension://dmkamcknogkgcdfhhbddcghachkejeap/register.html#'
            wallet_page = page.new_tab(url=url)

            import_button = wallet_page.ele('x://button[contains(@class, "sc-kLLXSd fnozug")]')
            if import_button:
                import_button.click()
            time.sleep(5)

            key_button = wallet_page.ele('x://button[contains(., "使用助记词或私钥") or contains(., "Use recovery phrase or private key")]')
            if key_button:
                key_button.click()

            words = text.split()

            # 定位所有符合条件的 <input> 元素（注意根据实际页面结构调整 XPath）
            inputs = wallet_page.eles("x://input[@type='password' and contains(@class, 'sc-efBctP cSWuvD')]")

            # 将每个 input 元素依次填入对应的单词
            for input_ele, word in zip(inputs, words):
                # 模拟键入操作，填入 word
                input_ele.input(word)
                time.sleep(1)

            time.sleep(2)
            import_key_button = wallet_page.ele('x://button[normalize-space(.)="导入" or normalize-space(.)="Import"]')
            if import_key_button:
                import_key_button.click()

            input_name = wallet_page.ele('x://input[@name="name"]')
            input_name.input('key')
            password = wallet_page.ele('x://input[@name="password"]')
            if password:
                password.input('xujiaxujia')
            confirmPassword = wallet_page.ele('x://input[@name="confirmPassword"]')
            if confirmPassword:
                confirmPassword.input('xujiaxujia')


            time.sleep(2)
            step_button = wallet_page.ele('x://button[normalize-space(.)="下一步" or normalize-space(.)="Next"]')
            if step_button:
                step_button.click()

            time.sleep(2)
            save_button = wallet_page.ele('x://button[normalize-space(.)="保存" or normalize-space(.)="Save"]')
            if save_button:
                save_button.click()

            time.sleep(2)
            imp_button = wallet_page.ele('x://button[normalize-space(.)="导入" or normalize-space(.)="Import"]')
            if imp_button:
                imp_button.click()

            time.sleep(2)
            end_button = wallet_page.ele('x://button[normalize-space(.)="完成" or normalize-space(.)="Finish"]')
            if end_button:
                end_button.click()
            wallet_page.close()
        except Exception as error:
            logger.error(f'error ==> {error}')
        finally:
            await self.__deal_window(page)

    # 登陆钱包
    async def get_wallet(self, page, union_address, text):
        wallet_page = None
        try:
            url = 'chrome-extension://dmkamcknogkgcdfhhbddcghachkejeap/popup.html'
            wallet_page = page.new_tab(url=url)
            input_password = wallet_page.ele("x://input[@type='password' and contains(@class, 'sc-ikZpkk pEVcx')]")
            if input_password:
                time.sleep(3)
                input_password.input('xujiaxujia')
                time.sleep(3)
                log_in_button = wallet_page.ele('x://button[normalize-space(.)="解锁"]')
                if log_in_button:
                    log_in_button.click()
                    time.sleep(5)
            money = wallet_page.ele('x://div[contains(@class, "sc-hKMtZM sc-jSMfEi eHObTT iuhvyf")]')
            if money:
                # 获取元素的文本内容，例如 "$0"
                money_text = money.text
                # 去除 "$" 符号，并去除可能的空白字符
                money_clean = money_text.replace("$", "").strip()
                print(money_clean)

        except Exception as error:
            if wallet_page:
                wallet_page.close()
            # 异常 重新导入钱包
            await asyncio.wait_for(fut=self.open_wallet(page=page, union_address=union_address, text=text), timeout=100)
        finally:
            await self.__deal_window(page)

    async def activate_wallet(self, page, union_address):
        url = 'chrome-extension://dmkamcknogkgcdfhhbddcghachkejeap/popup.html'
        wallet_page = page.new_tab(url=url)
        input = wallet_page.ele("x://input[@autocomplete='off' and contains(@class, 'sc-ikZpkk pEVcx')]")
        if input:
            time.sleep(3)
            input.input('UNO')
            time.sleep(2)
            target_div = wallet_page.ele('x://div[normalize-space(text())="UNO"]/parent::div/parent::div/parent::div/parent::div')
            if target_div:
                print("找到目标元素:", target_div.html)
                wallet_page.actions.move_to(target_div).click()
            else:
                enable_button = wallet_page.ele('x://button[normalize-space(.)="Enable"]')
                logger.info('没找到元素1')
                if enable_button:
                    enable_button.click()
                    time.sleep(3)
                    await self.__deal_window(page)
                    wallet_page.refresh()
                    time.sleep(5)
                    target_div = wallet_page.ele('x://div[normalize-space(text())="UNO"]/parent::div/parent::div/parent::div/parent::div')
                    if target_div:
                        print("激活钱包:")
                        wallet_page.actions.move_to(target_div).click()

            time.sleep(2)
            await self.__click_ele(page=wallet_page, xpath='x://div[@cursor="pointer" and .//div[contains(text(), "Send")]]')
            send_inputs = wallet_page.eles("x://input[@autocomplete='off' and contains(@class, 'sc-ikZpkk pEVcx')]")
            values = [union_address, '0.0001', 'send']

            # 遍历输入框与对应的值，依次填入
            for input_ele, value in zip(send_inputs, values):
                input_ele.input(value)
                time.sleep(2)
            time.sleep(2)
            # 提交
            await self.__click_ele(page=wallet_page, xpath="x://button[@color='primary' and contains(@class, 'sc-iTONeN jEEuKd')]")
            time.sleep(1)
            # 确定转账
            await self.__click_ele(page=wallet_page, xpath="x://button[@type='button' and contains(@class, 'sc-cOFTSb iuHbmd')]")


    async def __do_task(self, page, union_id, union_address):
        data = f'{union_id} {union_address}'
        url = 'https://app.union.build/faucet'
        main_page = page.new_tab(url=url)
        await asyncio.sleep(5)
        main_page.wait.ele_displayed(loc_or_ele='x://input[@name="wallet-address"]', timeout=10)
        main_page.ele(locator='x://input[@name="wallet-address"]').input(union_address)
        await asyncio.sleep(2)
        await self.__click_ele(page=main_page, xpath='x://button[contains(text(), "Verify")]')
        await asyncio.sleep(5)
        ele = main_page.ele(locator='x://div[@class=" svelte-d2x57e"]/div').shadow_root.child().ele('x://body').shadow_root.ele('x:./div/div/div')
        if ele.html.count('<input type="checkbox">'):
            ele.ele('x://label/input').click()
            await asyncio.sleep(5)
        await self.__click_ele(page=main_page, xpath='x://button[contains(text(), "Submit")]')
        while True:
            if not main_page.wait.ele_displayed(loc_or_ele='x://button[contains(text(), "Submit")]', timeout=2):
                break
        if main_page.wait.ele_displayed(loc_or_ele='x://a[contains(@href, "/union/tx/")]', timeout=2):
            logger.success(f'领水成功 ==> {data}')
        else:
            logger.error(f'领水失败 ==> {data}')

        # 关联keplr钱包
        await self.__click_ele(page=main_page, xpath='x://button[.//span[contains(text(), "Connect Wallet")]]')
        await self.__click_ele(page=main_page, xpath='x://button[normalize-space(.)="keplr"]')
        time.sleep(4)
        await self.__deal_window(page)
        await self.__click_ele(page=main_page, xpath='x://button[@data-melt-dialog-close]')

        # 验证第二个
        await self.__click_ele(page=main_page, xpath='x://button[contains(text(), "Verify")]')
        time.sleep(5)
        ele = main_page.ele(locator='x://div[@class=" svelte-d2x57e"]/div').shadow_root.child().ele('x://body').shadow_root.ele('x:./div/div/div')
        if ele.html.count('<input type="checkbox">'):
            ele.ele('x://label/input').click()
            time.sleep(5)
        await self.__click_ele(page=main_page, xpath='x://button[contains(text(), "Submit")]')
        while True:
            if not main_page.wait.ele_displayed(loc_or_ele='x://button[contains(text(), "Submit")]', timeout=2):
                break
        if main_page.wait.ele_displayed(loc_or_ele='x://a[contains(@href, "/union/tx/")]', timeout=2):
            logger.success(f'领水成功 ==> {data}')
        else:
            logger.error(f'领水失败 ==> {data}')

        return data

    # 处理弹窗
    async def __deal_window(self, page):
        try:
            # 如果窗口大于2才进行操作
            if page.tabs_count >= 2:
                time.sleep(3)
                for index in range(page.tabs_count):
                    tab = page.get_tab(index)
                    time.sleep(3)
                    # keplr 钱包
                    if 'chrome-extension://dmkamcknogkgcdfhhbddcghachkejeap/popup.html' in tab.url:
                        if tab.wait.ele_displayed(loc_or_ele="x://button[normalize-space(.)='Approve']", timeout=3):
                            await self.__click_ele(page=tab, xpath="x://button[normalize-space(.)='Approve']")
                            time.sleep(1)
                    elif '/register.html#?route=enable-chains' in tab.url:
                        buttons = tab.ele("x://input[@type='checkbox' and contains(@class, 'sc-kIKDeO jbWSkg')]")
                        if buttons:
                            buttons.click()
                            time.sleep(2)
                            await self.__click_ele(page=tab, xpath="x://button[normalize-space(.)='Save']")
                    elif '/register.html' in tab.url:
                        tab.close()

                    #  evm 钱包
                    elif '/popup.html?page=%2Fdapp-permission' in tab.url:
                        if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=3):
                            close_but = tab.ele('x://*[@id="close"]')
                            if close_but:
                                tab.actions.move_to(close_but).click()
                            time.sleep(1)
                        com_but = tab.ele('x://button[@id="grantPermission"]')
                        if com_but:
                            tab.actions.move_to(com_but).click()
                        time.sleep(2)

                    elif '/notification.html#connect' in tab.url:
                        self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                        self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                        time.sleep(2)

                    elif '/notification.html#confirmation' in tab.url:
                        self.__click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                        time.sleep(2)
                        self.__click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                        time.sleep(2)

                    elif '/notification.html#confirm-transaction' in tab.url:
                        self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                        time.sleep(2)

                    elif '/popup.html?page=%2Fsign-transaction' in tab.url:
                        if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                            self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                            time.sleep(1)
                        logger.info('准备点击1')
                        self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                        logger.info('点击结束1')
                        time.sleep(2)

                    elif '/popup.html?page=%2Fsign-data' in tab.url:
                        if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                            self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                            time.sleep(1)
                        self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                        time.sleep(2)

                    elif 'popup.html?page=%2Fpersonal-sign' in tab.url:
                        if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                            self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                            time.sleep(1)
                        self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                        time.sleep(2)

                    elif '/popup.html?requestId=0&page=%2Fadd-evm-chain' in tab.url:
                        self.__click_ele(page=tab, xpath='x://button[@type="submit"]')

                    elif ('&tab=%2Fadd-evm-chain' in tab.url) or ('/popup.html?requestId=' in tab.url):
                        if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                            self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                            time.sleep(1)
                        self.__click_ele(page=tab, xpath='x://button[@id="addNewChain"]')
                        time.sleep(2)

                    # elif 'edge://newtab/' in tab.url:
                        # tab.close()
                        # time.sleep(2)

                    elif 'popout.html?windowId=backpack' in tab.url:
                        self.__click_ele(page=tab, xpath='x://div/span[text()="确认"]')
                        time.sleep(2)
        except Exception as error:
            logger.error(f'error ==> {error}')
        return True

    async def __do_faucet_task(self, page, evm_id, evm_address):
        data = f'{evm_id} {evm_address}'
        url = 'https://faucet.circle.com/'
        faucet_page = page.new_tab(url=url)
        await asyncio.sleep(5)
        faucet_page.wait.ele_displayed(loc_or_ele='x://input[@placeholder="Wallet address"]', timeout=10)

        # 领取 Ethereum Sepolia usdc
        await self.__click_ele(page=faucet_page, xpath='x://button[@aria-haspopup="listbox"]')
        await asyncio.sleep(2)
        await self.__click_ele(page=faucet_page, xpath='x://span/span[text()="Ethereum Sepolia"]')
        await asyncio.sleep(2)
        faucet_page.ele(locator='x://input[@placeholder="Wallet address"]', timeout=3).input(evm_address)
        await asyncio.sleep(2)
        await self.__click_ele(page=faucet_page, xpath='x://button/span[text()="Send 10 USDC"]')
        await asyncio.sleep(5)
        if faucet_page.wait.ele_displayed(loc_or_ele='x://a[contains(@href, "/tx/0x")]', timeout=5):
            logger.success(f'sepolia usdc {data} 领取成功')
        else:
            logger.error(f'sepolia usdc {data} 领取失败')
        await self.__click_ele(page=faucet_page, xpath='x://button/span[text()="Get more tokens" or text()="Go Back"]')
        await asyncio.sleep(2)

        # 领取 Arbitrum Sepolia usdc
        await self.__click_ele(page=faucet_page, xpath='x://button[@aria-haspopup="listbox"]')
        await asyncio.sleep(2)
        await self.__click_ele(page=faucet_page, xpath='x://span[text()="Arbitrum Sepolia"]')
        await asyncio.sleep(2)
        faucet_page.ele(locator='x://input[@placeholder="Wallet address"]', timeout=3).input(evm_address)
        await asyncio.sleep(2)
        await self.__click_ele(page=faucet_page, xpath='x://button/span[text()="Send 10 USDC"]')
        await asyncio.sleep(5)
        if faucet_page.wait.ele_displayed(loc_or_ele='x://a[contains(@href, "/tx/0x")]', timeout=5):
            logger.success(f'arb usdc {data} 领取成功')
        else:
            logger.error(f'arb usdc {data} 领取失败')
        await self.__click_ele(page=faucet_page, xpath='x://button/span[text()="Get more tokens" or text()="Go Back"]')
        await asyncio.sleep(2)

        # 领取 Base Sepolia usdc
        await self.__click_ele(page=faucet_page, xpath='x://button[@aria-haspopup="listbox"]')
        await asyncio.sleep(2)
        await self.__click_ele(page=faucet_page, xpath='x://span[text()="Base Sepolia"]')
        await asyncio.sleep(2)
        faucet_page.ele(locator='x://input[@placeholder="Wallet address"]', timeout=3).input(evm_address)
        await asyncio.sleep(2)
        await self.__click_ele(page=faucet_page, xpath='x://button/span[text()="Send 10 USDC"]')
        await asyncio.sleep(5)
        if faucet_page.wait.ele_displayed(loc_or_ele='x://a[contains(@href, "/tx/0x")]', timeout=5):
            logger.success(f'base usdc {data} 领取成功')
        else:
            logger.error(f'base usdc {data} 领取失败')
        await self.__click_ele(page=faucet_page, xpath='x://button/span[text()="Get more tokens" or text()="Go Back"]')
        faucet_page.close()
        return data
        
        
    async def test(self, page, net):
        url = 'https://app.union.build/transfer'
        wallet_page = page.new_tab(url=url)
        time.sleep(4)                                                                            
        # 关联evm钱包
        await self.__click_ele(page=wallet_page, xpath='x://button[.//span[contains(text(), "Connect Wallet") or contains(text(), "Connected")]]')
        signma_but = wallet_page.ele('x://button[normalize-space(.)="Signma"]')
        if signma_but:
            await self.__click_ele(page=wallet_page, xpath='x://button[normalize-space(.)="Signma" or text()="Signma"]')
            time.sleep(4)
            await self.__deal_window(page)
            await self.__click_ele(page=wallet_page, xpath='x://button[@data-melt-dialog-close]')

        time.sleep(4)
        # 关联钱包
        await self.__click_ele(page=wallet_page, xpath='x://button[.//span[contains(text(), "Connect Wallet") or contains(text(), "Connected")]]')
        keplr_but = wallet_page.ele('x://button[normalize-space(.)="keplr"]')
        if keplr_but:
            await self.__click_ele(page=wallet_page, xpath='x://button[normalize-space(.)="keplr"]')
            time.sleep(4)
            await self.__deal_window(page)
            await self.__click_ele(page=wallet_page, xpath='x://button[@data-melt-dialog-close]')

        time.sleep(4)
        buttons = wallet_page.eles('x://div[contains(@class, "overflow-y-scroll")]//button[contains(@class, "inline-flex items-center")]')
        # 检查是否找到了至少三个按钮
        if len(buttons) >= 3:
            second_button = buttons[1]  # 列表索引从0开始，索引1为第二个按钮
            wallet_page.actions.move_to(second_button).click()
            await self.__click_ele(page=wallet_page, xpath=f'x://div[contains(text(), "{net}")]')

            # await self.__click_ele(page=wallet_page, xpath='x://div[contains(text(), "Stargaze Testnet")]')
            # await self.__click_ele(page=wallet_page, xpath='x://div[contains(text(), "Stride Testnet")]')
        # time.sleep(4)
        # uno_button = wallet_page.eles('x://div[contains(@class, "overflow-y-scroll")]//button[contains(@class, "inline-flex items-center")]')
        # # 检查是否找到了至少三个按钮
        # if len(uno_button) >= 3:
        #     third_button = uno_button[2]   # 索引2为第三个按钮
        #     logger.info(third_button.html)
        #     wallet_page.actions.move_to(third_button).click()
        #     time.sleep(5)
        #     uno_div = wallet_page.ele('x://b[normalize-space(text())="UNO"]/parent::span/parent::div/parent::div/parent::div')
        #     if uno_div:
        #         print("找到目标元素:", uno_div.html)
        #         wallet_page.actions.move_to(uno_div).click()
        input_balance = wallet_page.ele('x://input[contains(@inputmode, "decimal")]')
        if input_balance:
            input_balance.input('0.0001')
            time.sleep(2)
            select_balance = wallet_page.ele('x://button[text()="Use connected wallet"]')
            if select_balance:
                select_balance.click()
                # wallet_page.actions.move_to(select_balance).click()
            # 定位包含 "Transfer" 文本的按钮

            # 等待网络加载结束
            svg_xpath = 'x://svg[contains(@class, "absolute") and contains(@class, "-top-4") and contains(@class, "size-12") and contains(@class, "h-12") and contains(@class, "w-12") and contains(@class, "svelte-148xh0m")]'
            # 记录开始时间
            start_time = time.time()
            timeout = 30  # 最长等待30秒
            while True:
                # 尝试查找目标元素
                svg_ele = wallet_page.ele(svg_xpath)
                # 如果找不到元素，或者元素不可见，则认为已消失
                if not svg_ele:
                    print("SVG 元素已消失")
                    break
                # 判断是否超过超时时间
                if time.time() - start_time > timeout:
                    print("等待超时，SVG 元素仍然存在")
                    break
                # 每次等待 0.5 秒
                time.sleep(0.5)

            button = wallet_page.ele('x://button[contains(text(), "Transfer")]')
            # 判断按钮是否被禁用
            if button:
                button.click()
                conf_button = wallet_page.ele('x://button[contains(text(), "Confirm Transfer")]')
                if conf_button:
                    wallet_page.actions.move_to(conf_button).click()
                    time.sleep(5)
                    await self.__deal_window(page)
                time.sleep(5)
                conf_button = wallet_page.ele('x://button[contains(text(), "Confirm Transfer")]')
                if conf_button:
                    wallet_page.actions.move_to(conf_button).click()
                    time.sleep(5)
                    await self.__deal_window(page)
                    time.sleep(60)
                    retry_but = wallet_page.ele('x://button[contains(text(), "RETRY")]')
                    if retry_but:
                        wallet_page.actions.move_to(retry_but).click()
                        time.sleep(10)
                        await self.__deal_window(page)
                        time.sleep(100)
        wallet_page.close()

    async def setup_evm_wallet(self, page, index):
        logger.info(f"开始打开设置钱包：{index}")
        wallet_tab = page.new_tab(
            url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
        )
        time.sleep(3)
        logger.info(f"开始设置钱包：{index}")
        index_input_path = (
            "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
        )
        wallet_tab.ele(index_input_path).input(index, clear=True)
        time.sleep(3)
        index_button_path = "tag:button@@id=existingWallet"
        index_set_button = wallet_tab.ele(index_button_path)
        time.sleep(1)
        index_set_button.click()
        time.sleep(10)
        if len(page.get_tabs(title="Signma")) > 0:
            time.sleep(8)
            pop_tab = page.get_tab(title="Signma")
            if pop_tab.url == 'chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding':
                pop_tab.ele(index_input_path).input(index, clear=True)
                index_set_button = pop_tab.ele(index_button_path)
                time.sleep(1)
                index_set_button.click()
                pop_tab.close()
        time.sleep(3)
        result = True
        return result

    # 开始
    async def run(self, union_id, user, port, key, union_address, text) -> bool:
        page = await self.__get_page(index=union_id, port=port, user=user)
        # try:
        await asyncio.wait_for(fut=self.__do_faucet_task(page=page, evm_id=union_id, evm_address=key), timeout=100)
        await asyncio.wait_for(fut=self.setup_evm_wallet(page=page, index=union_id), timeout=100)
        await asyncio.wait_for(fut=self.open_wallet(page=page, union_address=union_address, text=text), timeout=100)
        # 激活钱包                                    
        await asyncio.wait_for(fut=self.activate_wallet(page=page, union_address=union_address), timeout=100)
        # await asyncio.wait_for(fut=self.get_wallet(page=page, union_address=union_address, text=text), timeout=100)
        # await asyncio.wait_for(fut=self.__do_task(page=page, union_id=union_id, union_address=union_address), timeout=100)
        await self.test(page, net="Babylon Testnet")
        await self.test(page, net="Stargaze Testnet")
        await self.test(page, net="Stride Testnet")
        # except Exception as error:
        #     logger.error(f'error ==> {error}')
        #     ...
        # finally:
        #     page.quit()
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
    test = Test()
    asyncio.run(test.run(union_id='78546', port='5934', key='0xa3f9c3f2e9e7d48d94e80415bdd33316570ef4e0', user='ubuntu',
                         union_address='union18pld2dxq9uxrzjrvffkd5ntql6aekmdnv892ec',
                         text='zoo horse way supreme narrow crunch ritual tonight party report story thought'))
