import requests
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import pyperclip
import random
from loguru import logger
import argparse
import os


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
        # logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                _page.ele(locator=xpath).click()
            else:
                _page.eles(locator=xpath)[index].click()
            # logger.info(f'点击按钮{xpath}:{loop_count}')
            return True
        except Exception as e:
            error = e
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return False
        loop_count += 1


# 获取元素
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
              find_all: bool = False,
              index: int = -1):
    loop_count = 1
    while True:
        # logger.info(f'查找元素{xpath}:{loop_count}')
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


def signma_log(message: str, task_name: str, index: str, node_name: str, total: str = "N", keywords: str = "") -> bool:
    try:
        url = "{}/service_route?service_name=signma_log&&task={}&&chain_id={}&&index={}&&msg={}&&total={}&&keywords={}"
        server_url = 'https://signma.bll06.xyz'
        full_url = url.format(server_url, task_name, node_name, index, message, total, keywords)
        try:
            response = requests.get(full_url, verify=False)
            if response.status_code == 200:
                logger.info("积分提交成功,")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return False
    except requests.exceptions.RequestException as e:
        raise logger.error(f"网络请求失败: {str(e)}")
    except Exception as e:
        raise logger.error(f"发送日志失败: {str(e)}")


def monitor_switch(pages):
    total = 70
    while True:
        try:
            time.sleep(random.randint(60, 80))
            for idx, tab in enumerate(pages, start=1):
                if __get_ele(page=tab, xpath='x://button[@role="switch"]', loop=2):
                    if __click_ele(_page=tab, xpath='x://button[@role="switch" and @aria-checked="false"]', loop=2):
                        logger.info(f"未链接网络")
                    else:
                        logger.info(f"已链接网络:{total}")
                        if __get_ele(page=tab, xpath='x://span[text()="Connected"]', loop=1):
                            if total > 60:
                                # 获取积分 每循环60次检测 获取一次积分
                                points = get_points(tab)
                                # 关闭积分弹窗（如果存在）
                                __click_ele(tab, 'x://button[.//span[text()="Close"]]')
                                if points is not None and points != "":
                                    logger.info("appInfo", args.ip + ',采集积分,' + str(points))
                                    signma_log(message=str(points), task_name="hyper", index=tab.page_id, node_name=args.ip)
                                    logger.info(f"推送积分:{points}")
                else:
                    logger.info("刷新页面")
                    tab.refresh()
            if total > 60:
                total = 0
            total += 1
        except Exception as e:
            logger.info("appInfo", args.ip + ',检查过程中出现异常: ' + str(e))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--param", type=str, help="参数")
    parser.add_argument("--ip", type=str, help="参数")
    args = parser.parse_args()
    pages = []
    idx = 0
    for part in args.param.split("||"):
        os.environ['DISPLAY'] = ':23'
        port = 9515 + idx
        idx += 1
        arg = part.split(",")
        im_public_key = arg[0]
        im_private_Key = arg[1]
        logger.info(f"启动:{im_public_key}")
        options = ChromiumOptions()
        options.set_browser_path('/opt/google/chrome')
        options.set_user_data_path(f"/home/ubuntu/task/hyper/chrome_data/{im_public_key}")
        options.set_local_port(port)

        # ...............
        page = ChromiumPage(options)
        page.get('https://node.hyper.space/')
        page.page_id = im_public_key
        time.sleep(10)
        # if __click_ele(page, "x://p[text()='Public Key:']/following-sibling::div//button"):
            # public_key = pyperclip.paste().strip()
            # print(public_key)
            # if public_key is not None and public_key != im_public_key:
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
        __click_ele(_page=page, xpath='x://button[.//span[text()="Close"]]', loop=2)
        pages.append(page)
        time.sleep(60 + (15 * idx))

    # 进入循环，持续监控切换按钮状态
    monitor_switch(pages=pages)
