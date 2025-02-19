import json
import os
import platform
import random
import time
import uuid

import requests
from DrissionPage._base.chromium import Chromium
from DrissionPage._configs.chromium_options import ChromiumOptions
import argparse
from DrissionPage._functions.keys import Keys
from loguru import logger


class TaskSet:
    def __init__(self, args):
        self.co = ChromiumOptions()
        self.meta_id = 'dholkoaddiccbagimjcfjaldcacogjgc'
        self.arguments = [
            "--accept-lang=en-US",
            "--no-first-run",
            "--force-color-profile=srgb",
            "--disable-extensions-file-access-check",
            "--metrics-recording-only",
            "--password-store=basic",
            "--use-mock-keychain",
            "--export-tagged-pdf",
            "--no-default-self.browser-check",
            "--disable-background-tab-loading",
            "--enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=OverlayScrollbar",
            "--disable-infobars",
            "--disable-popup-blocking",
            "--allow-outdated-plugins",
            "--always-authorize-plugins",
            "--disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage,PrivacySandboxSettings4",
            "--deny-permission-prompts",
            "--disable-suggestions-ui",
            "--hide-crash-restore-bubble",
            "--window-size=1920,1080",
            "--disable-mobile-emulation",
        ]
        if platform.system().lower() == 'windows':
            self.co.set_paths(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
            self.ex_path = r"D:\web3\signma_extension\dist\chrome-cloud"
            self.co.set_user_data_path(r"E:\chrome_data")
            self.meta_id = 'ohgmkpjifodfiomblclfpdhehohinlnn'
        else:
            self.co.set_paths(r"/opt/google/chrome/google-chrome")
            self.ex_path = r"/home/ubuntu/extensions/chrome-cloud"
            self.co.set_user_data_path(os.path.join("/home/ubuntu/task/chrome_data", uuid.uuid4().hex.lower()))
        self.co.add_extension(self.ex_path)

        self.co.set_user_agent(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        self.co.set_local_port(int(args.index[-4:]) + random.randint(1000, 2000))
        self.browser = Chromium(self.co)
        self.tab = self.browser.latest_tab
        self.res_info = None

    def signma_log(self, message: str, task_name: str, index: str, server_url: str):
        url = "{}/service_route?service_name=signma_log&&task={}&&chain_id={}&&index={}&&msg={}"
        if server_url is None:
            server_url = "https://signma.bll06.xyz"

        print(url.format(server_url, task_name, "9004", index, message))
        response = requests.get(
            url.format(server_url, task_name, "9004", index, message), verify=False
        )

    def get_private_key(self, args):
        private_key = None
        url = '{}/service_route?service_name=get_private_key&&index={}&&pass_key={}'

        if args.server_url is None:
            server_url = 'https://signma.bll06.xyz'
        else:
            server_url = args.server_url

        try:
            response = requests.get(url.format(server_url, args.index, args.pass_key), verify=False)
            if response.status_code == 200:
                private_key = response.json()['data']['privateAddress']
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")

        return private_key

    def navigate_and_click(self, url, element_selector, wait_time=1):
        """通用方法：导航到URL并点击指定元素xxx"""
        self.tab.get(url=url)
        if self.tab.wait.ele_displayed(element_selector, timeout=10):
            self.tab.ele(element_selector).click()
            time.sleep(wait_time)

    def setup_wallet(self, args):
        self.tab = self.browser.new_tab(url="chrome://extensions/")
        time.sleep(3)

        toggle_ele = (
            self.tab.ele(
                "x://html/body/extensions-manager"
            )  # /html/body/extensions-manager
            .shadow_root.ele('x://*[@id="viewManager"]')
            .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
            .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
            .shadow_root.ele("tag:cr-toggle@@id=enableToggle")
        )

        refresh_ele = (
            self.tab.ele(
                "x://html/body/extensions-manager"
            )  # /html/body/extensions-manager
            .shadow_root.ele('x://*[@id="viewManager"]')
            .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
            .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
            .shadow_root.ele("tag:cr-icon-button@@id=dev-reload-button")
        )

        toggle_ele.attr("aria-pressed")
        if toggle_ele.attr("aria-pressed") == "false":
            toggle_ele.click()

        refresh_ele.click()

        time.sleep(2)
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

        index_set_button.click()

    def close_browser(self):
        """关闭浏览器并清理资源"""
        self.browser.reconnect()
        self.browser.close_tabs(tabs_or_ids=self.tab, others=True)
        self.browser.quit(timeout=60, force=True, del_data=True)

    def myriad_pop(self):
        if len(self.browser.get_tabs(title="Signma")) > 0:
            pop_tab = self.browser.get_tab(title="Signma")

            back_path = 'x://*[@id="sign-root"]/div/div/section/main/div[1]/section[1]/div/button'
            conn_path = "tag:div@@class=jsx-3858486283 button_content@@text()=连接"
            sign_enable_path = (
                "tag:button@@class=jsx-3858486283 button large primaryGreen"
            )

            sign_blank_path = (
                "tag:div@@class=jsx-1443409666 subtext@@text()^希望您使用您的登录"
            )

            if pop_tab.url == 'chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/popup.html?page=%2Fdapp-permission':
                if pop_tab.ele(back_path) is not None:
                    pop_tab.ele(back_path).click()
                time.sleep(2)

                if pop_tab.ele(conn_path) is not None:
                    pop_tab.ele(conn_path).click()
                    time.sleep(3)
            elif "chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/popup.html?page=%2Fpersonal-sign":
                while pop_tab.wait.ele_displayed(sign_enable_path, timeout=3) is False:
                    if pop_tab.wait.ele_displayed(sign_blank_path, timeout=3):
                        pop_tab.actions.move_to(sign_blank_path)
                        pop_tab.ele(sign_blank_path).click()
                        time.sleep(2)

                if pop_tab.ele(sign_enable_path) is not None:
                    pop_tab.ele(sign_enable_path).click()

    def myriad(self, args):
        try:
            if len(self.browser.get_tabs(title="Signma")) > 0:
                self.browser.get_tab(title="Signma").close()

            self.tab.get("https://myriad.markets", timeout=60)

            time.sleep(5)
            # 接受cookie
            accept_path = (
                "tag:button@@id=CybotCookiebotDialogBodyButtonAccept@@text()=Allow all"
            )

            if self.tab.wait.ele_displayed(accept_path, timeout=5):
                self.tab.ele(accept_path).click()
            # 连接钱包
            connect_path = "tag:button@@data-id=connect-wallet-button"
            img_path = 'tag:img@src=https://myriad.markets/ui/myriad-icon-avatar-placeholder.svg'
            claim_button_path = "tag:div@@class^text-text-sub-600@@text()^Limbo"

            avali_button_path = "tag:div@@class=relative@@text()^Available in "

            if self.tab.wait.ele_displayed(img_path, timeout=5):
                i = 0
            elif self.tab.wait.ele_displayed(connect_path, timeout=5):
                self.tab.ele(connect_path).click()
                time.sleep(5)
                for i in range(10):
                    # logger.info(f'第{i}次循环')
                    self.myriad_pop()
                    time.sleep(5)

                time.sleep(5)
                i = 1
                while (
                        self.tab.wait.ele_displayed(claim_button_path, timeout=2) is False
                        and self.tab.wait.ele_displayed(avali_button_path, timeout=1) is False
                ) and self.tab.wait.ele_displayed(
                    "tag:div@@class=relative@@text()=Sign in to Claim", timeout=1
                ) is not False:
                    self.tab.ele("tag:div@@class=relative@@text()=Sign in to Claim").click()
                    time.sleep(5)

                    if len(self.browser.get_tabs(title="Myriad | DASTAN")) > 0:
                        sign_in_tab = self.browser.get_tab(title="Myriad | DASTAN")

                        sign_in_path = "tag:span@@class=text-sm font-medium px-1@@text()=Sign in with Abstract"

                        if sign_in_tab.wait.ele_displayed(sign_in_path, timeout=3):
                            sign_in_tab.actions.move_to(sign_in_path)
                            sign_in_tab.ele(sign_in_path).click()
                            time.sleep(10)

            for i in range(2):
                # logger.info(f'第{i}次补充循环')
                self.myriad_pop()
                time.sleep(2)


            time.sleep(3)

            self.tab.get("https://myriad.markets", timeout=5)
            self.tab.wait.load_start()
            time.sleep(10)
            if self.tab.wait.ele_displayed(claim_button_path, timeout=10) is not False:
                self.tab.ele(claim_button_path).click()
                time.sleep(2)
                # if self.tab.wait.ele_displayed(avali_button_path, timeout=1) is False:
                save_wallet_path = "tag:div@@text()=Save to Wallet"
                close_path = "tag:div@@text()=Close"
                if self.tab.wait.ele_displayed(close_path, timeout=3) is not False:
                    self.tab.ele(close_path).click()
                    self.tab.ele(claim_button_path).click()
                    time.sleep(2)

                if self.tab.wait.ele_displayed(close_path, timeout=3) is False:
                    conf_count = 0
                    while (
                            self.tab.wait.ele_displayed(save_wallet_path, timeout=3)
                            is False
                            and conf_count < 2
                    ):
                        time.sleep(3)
                        conf_count = conf_count + 1

                    if self.tab.wait.ele_displayed(save_wallet_path, timeout=3):
                        self.tab.actions.move_to(save_wallet_path)
                        self.tab.ele(save_wallet_path).click()
                        time.sleep(2)
                else:
                    self.tab.ele(close_path).click()

            self.myriad_pop()

            self.tab.get("https://myriad.markets/markets", timeout=30)
            time.sleep(5)
            market_list = self.tab.eles(
                "tag:div@@class=relative group/gcontainer@@style=padding: 1px;"
            )

            market_item = random.choice(market_list)

            market_url = market_item.s_ele(
                "tag:a@@class=gap-2 flex items-center min-h-[44px] mt-3 px-4 linkbox__overlay"
            ).attr("href")

            self.tab.get(market_url, timeout=5)

            time.sleep(5)

            buy_path = "tag:div@@class=relative truncate@@text()=Buy"

            while self.tab.wait.ele_displayed(buy_path) is False:
                time.sleep(5)

            if self.tab.wait.ele_displayed(buy_path, timeout=30):
                self.tab.actions.move_to(buy_path)
                time.sleep(1)
                self.tab.ele(buy_path).click()
                time.sleep(5)

            confirm_path = "tag:div@@class=relative@@text()=Confirm"

            while self.tab.wait.ele_displayed(confirm_path) is False:
                time.sleep(2)

            if self.tab.wait.ele_displayed(confirm_path, timeout=20):
                self.tab.actions.move_to(confirm_path)
                self.tab.ele(confirm_path).click()
                time.sleep(5)

            time.sleep(15)

            approve_path = "tag:button@@text()=Approve"

            not_now_path = "tag:button@@text()=Not now"

            buy_count = 0
            while len(self.browser.get_tabs(title="Auth · Privy")) == 0 and buy_count < 15:
                time.sleep(2)
                buy_count = buy_count + 1

            if len(self.browser.get_tabs(title="Auth · Privy")) > 0:
                approve_tab = self.browser.get_tab(title="Auth · Privy")

                if (
                        approve_tab.wait.ele_displayed(approve_path, timeout=30)
                        and approve_tab.wait.ele_displayed("tag:span@@text()^\$0", timeout=3)
                        and approve_tab.wait.ele_displayed(
                    "tag:span@@text()=Sponsored", timeout=1
                )
                ):
                    # time.sleep(5)
                    approve_tab.actions.move_to(approve_path)
                    approve_tab.ele(approve_path).click()
                    time.sleep(20)
                    # approve_tab = self.browser.get_tab(title="Auth · Privy")
                    done_count = 0
                    retry_path = "tag:button@@text()=Retry transaction"
                    all_path = "tag:button@@text()=All Done"
                    while (
                            approve_tab.wait.ele_displayed(all_path, timeout=3) is False
                            and done_count < 6
                    ):
                        time.sleep(2)
                        approve_tab = self.browser.get_tab(title="Auth · Privy")
                        done_count = done_count + 1

                    if approve_tab.wait.ele_displayed(retry_path, timeout=1) is not False:
                        self.res_info = "approve参数错误,跳过"
                    elif approve_tab.wait.ele_displayed(all_path, timeout=10) is not False:
                        approve_tab.ele(all_path).click()

                        time.sleep(8)
                        self.res_info = "成功处理"
                    else:
                        self.res_info = "未获取到all done按钮"
                else:
                    if len(self.browser.get_tabs(title="Auth · Privy")) > 0:
                        approve_tab.ele(not_now_path).click()
                    self.res_info = "交易数据错误,跳过"
            else:
                # No markets found. Try changing the filters.
                if len(self.browser.get_tabs(title="Auth · Privy")) > 0:
                    self.tab(not_now_path).click()
            time.sleep(10)
            self.tab.get("https://myriad.markets/profile", timeout=5)

            time.sleep(3)
            if self.tab.wait.ele_displayed("tag:div@@text()=No markets found. Try changing the filters.", timeout=10):
                self.res_info = "无交易记录"
            else:
                self.res_info = "有交易记录,交易成功"



        except Exception as e:
            logger.info(f"---------发生异常：{str(e)}-----------------")
            self.res_info = f"发生异常：{str(e)}"
        finally:
            self.signma_log(self.res_info, all_args.task, all_args.index,"https://signma.bll06.xyz")

            # res = requests.request("POST", self.log_url, headers=headers, data=payload)
            logger.info(f"---------完成情况：no-----------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This script accepts args.")
    parser.add_argument('--type', type=str, help='operation type')
    parser.add_argument('--task', type=str, help='task name')
    parser.add_argument('--index', type=str, help='index')
    all_args = parser.parse_args()
    task_set = TaskSet(all_args)

    try:

        if all_args.type == 'myriad':
            task_set.setup_wallet(all_args)
            task_set.myriad(all_args)
    finally:
        task_set.close_browser()
