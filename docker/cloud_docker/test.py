from DrissionPage import ChromiumPage, ChromiumOptions
import time
import pyperclip
import random
from loguru import logger
import argparse


def get_points(tab):
    # 获取积分：点击按钮后从剪贴板读取
    if __click_ele(tab, "x://button[.//span[text()='Points']]"):
        time.sleep(15)  # 确保剪贴板内容更新
        # 定位到指定的 div 元素并获取其文本内容
        target_div = tab.ele("x://div[text()='Accumlated points']/following-sibling::div")
        # 获取该 div 中的文本
        text = target_div.text
        # logger.info(f"Text from the div: {text}")
        return text


def __click_ele(_page, xpath: str = '', loop: int = 5, must: bool = False,
                find_all: bool = False,
                index: int = -1) -> bool:
    loop_count = 1
    while True:
        logger.info(f'get {xpath}:{loop_count}')
        try:
            if not find_all:
                _page.ele(locator=xpath).click()
            else:
                _page.eles(locator=xpath)[index].click()
            logger.info(f'click {xpath}:{loop_count}')
            return True
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'not ele:{xpath}')
            return False
        loop_count += 1
        time.sleep(1)


def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


def get_app_info_integral(serverId, appId, public_key, integral, operationType, integralE, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "publicKey": f"{public_key}",
        "integral": f"{integral}",
        "operationType": f"{operationType}",
        "integralE": f"{integralE}",
        "description": f"{description}",
    }

# 获取元素
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
              find_all: bool = False,
              index: int = -1):
    loop_count = 1
    while True:
        logger.info(f'get ele {xpath}:{loop_count}')
        try:
            if not find_all:
                # logger.info(f'查找元素{xpath}:{loop_count}')
                txt = page.ele(locator=xpath)
                if txt:
                    return txt
            else:
                # logger.info(f'查找元素{xpath}:{loop_count}:{find_all}:{index}')
                txt = page.eles(locator=xpath)[index]
                if txt:
                    return txt
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return None
        loop_count += 1
        time.sleep(1)


def monitor_switch(tab):
    total = 70
    error = 5
    num = random.randint(6, 8)
    while True:
        try:
            time.sleep(num)
            logger.info("sw")
            if __get_ele(page=tab, xpath='x://button[@role="switch"]', loop=2):
                logger.info("check net")
                if __click_ele(_page=tab, xpath='x://button[@role="switch" and @aria-checked="false"]', loop=2):
                    logger.info("not net")
                    error += 1
                else:
                    logger.info("up net")
                    if __get_ele(page=tab, xpath='x://span[text()="Connected"]', loop=1):
                        logger.info("net")
                        if error > 0:
                            logger.info('Connect to the Internet')
                        error = 0

                        if total > 60:
                            # 获取积分 每循环60次检测 获取一次积分
                            points = get_points(tab)
                            # 关闭积分弹窗（如果存在）
                            __click_ele(tab, 'x://button[.//span[text()="Close"]]')
                            if points is not None and points != "":
                                logger.info(f"get points:{points}")
                                total = 0
                            elif total > 70:
                                logger.info(f"error refresh:{total}")
                                total = 30
                                tab.refresh()
                if error == 9:
                    tab.refresh()
                    time.sleep(3)
                    logger.info("refresh page:")    # 关闭弹窗（如果存在）
                    __click_ele(tab, 'x://button[.//span[text()="Close"]]')

                if error == 10:
                    logger.info(f"error :{total}")
                    error = 0
            else:
                logger.info("refresh")
                tab.refresh()

            total += 1
        except Exception as e:
            logger.info(f"error :{str(e)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    args = parser.parse_args()
    data_map = {}

    options = ChromiumOptions()
    # options.set_browser_path(r'C:\Users\liulei\Desktop\chrome-win\chrome.exe')
    options.set_browser_path('/usr/bin/chromium-browser')
    options.set_argument('--no-sandbox')

    page = ChromiumPage(options)
    page.get('https://node.hyper.space/')

    args.serverId = '1'
    args.appId = '1'
    args.display = '5903'
    args.publicKey = 'J4BRHjFRNd438DcigpiooJd17FXdFuuXvYYzMhUpFyCN'
    args.privateKey = 'G9afgDMmmSnjNWAENgvyMK2dAEZmsFZCxDzy5Q6LcV3z'
    im_public_key = args.publicKey
    im_private_Key = args.privateKey

    time.sleep(100)
    if __click_ele(page, "x://p[text()='Public Key:']/following-sibling::div//button"):
        public_key = pyperclip.paste().strip()
        print(public_key)
        if public_key is not None and public_key != im_public_key:
            if __click_ele(page, "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
                if __click_ele(page, "x://div[contains(@class, 'cursor-text')]"):
                    print(f"write key")
                    page.actions.type(im_private_Key)
                    time.sleep(1)
                    # 确认导入
                    __click_ele(page, "x://button[normalize-space()='IMPORT KEY']")
                    time.sleep(5)
                    page.refresh()
                    time.sleep(3)
            # 关闭私钥弹窗（如果存在）
            __click_ele(_page=page, xpath='x://button[.//span[text()="Close"]]',loop=2)

    # 进入循环，持续监控切换按钮状态
    monitor_switch(page)
