import time
from DrissionPage._base.chromium import Chromium
from DrissionPage._configs.chromium_options import ChromiumOptions
from loguru import logger
import random


def configure_browser():
    """配置并启动浏览器"""
    co = (ChromiumOptions().set_local_port(9515)
          .set_paths(r"/opt/google/chrome/google-chrome"))
    arguments = [
        "--accept-lang=en-US", "--no-first-run", "--force-color-profile=srgb",
        "--metrics-recording-only", "--password-store=basic", "--use-mock-keychain",
        "--export-tagged-pdf", "--disable-gpu", "--disable-web-security",
        "--disable-infobars", "--disable-popup-blocking", "--allow-outdated-plugins",
        "--deny-permission-prompts", "--disable-suggestions-ui", "--window-size=1920,1080",
        "--disable-mobile-emulation", "--user-data-dir=/tmp/nexus/userData/9516",
        "--disable-features=ServerSentEvents"
    ]

    for arg in arguments:
        co.set_argument(arg)

    co.set_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

    browser = Chromium(co)
    # tab = browser.new_tab(url="https://app.nexus.xyz")
    tab = browser.latest_tab
    return tab

def monitor_switch(tab):
    num = random.randint(10, 20)
    while True:
        try:
            time.sleep(num)

            # 定位 class 属性中包含 'bg-[#ffffff]' 的 div 元素
            div_ele = tab.ele('x://div[contains(@class, "bg-[#ffffff]")]')

            # 判断元素是否存在，存在则执行点击操作
            if div_ele:
                div_ele.click(by_js=True)
                logger.info("离线，已执行点击操作。")
            else:
                logger.info("在线。")

        except Exception as e:
            logger.info("错误。")


def main():

    # 启动浏览器
    logger.info(f"start")
    tab = configure_browser()
    time.sleep(3)
    tab = tab.browser.new_tab(url="https://app.nexus.xyz")

    # 定位 class 属性中包含 'bg-[#ffffff]' 的 div 元素
    div_ele = tab.ele('x://div[contains(@class, "bg-[#ffffff]")]')

    # 判断元素是否存在，存在则执行点击操作
    if div_ele:
        div_ele.click(by_js=True)
        logger.info("找到了包含 'bg-[#ffffff]' 的 div，已执行点击操作。")
    else:
        logger.info("未找到包含 'bg-[#ffffff]' 的 div。")

    # 点击 "Sign up to earn NEX" 元素
    signup_ele = tab.ele('x://div[text()="Sign up to earn NEX"]/ancestor::button')
    if signup_ele:
        signup_ele.click(by_js=True)
        # 根据实际情况调整等待时间，确保页面加载完成
        time.sleep(2)

        # 定位到包含 shadow DOM 的元素
        shadow_host = tab.ele('x://div[@data-testid="dynamic-modal-shadow"]')
        if shadow_host:
            # 进入 shadow DOM
            shadow_root = shadow_host.shadow_root
            if shadow_root:
                # 选择钱包
                continue_button = shadow_root.ele('x://p[contains(text(), "Continue with a wallet")]')
                if continue_button:
                    # 点击目标元素
                    continue_button.click(by_js=True)
                    time.sleep(2)
                    # 点击钱包
                    signma_ele = shadow_root.ele('x://span[text()="Signma"]')
                    if signma_ele:
                        signma_ele.click(by_js=True)
                        time.sleep(2)
                        # myriad_pop(tab)

        # 选择网络
        shadow_host = tab.ele('x://div[@data-testid="dynamic-modal-shadow"]')
        if shadow_host:
            # 进入 shadow DOM
            shadow_root = shadow_host.shadow_root
            if shadow_root:
                # 连接到网络
                newtwork = shadow_root.ele('x://@button[data-testid="SelectNetworkButton"]')
                if newtwork:
                    newtwork.click(by_js=True)

        # 连接网络
        shadow_host = tab.ele('x://div[@data-testid="dynamic-modal-shadow"]')
        if shadow_host:
            # 进入 shadow DOM
            logger.info("找到12233。")
            shadow_root = shadow_host.shadow_root
            if shadow_root:
                logger.info("找到123。")
                newtwork = shadow_root.ele('x://button[.//span[text()="Continue"]]')
                if newtwork:
                    logger.info("找到13。")
                    newtwork.click(by_js=True)
                    
    # 进入循环，持续监控切换按钮状态
    monitor_switch(tab)


if __name__ == '__main__':

    # 启动网络循环
    main()
