import requests
from DrissionPage import ChromiumPage, ChromiumOptions
import time
from datetime import datetime
import random
from loguru import logger
import argparse
import os
import subprocess

# ========= 可调参数 =========
RESTART_INTERVAL_SEC = 60 * 60 * 24 * 2    # 每隔两天(48小时)重启
BASE_PORT = 9515                            # 起始远程调试端口
DISPLAY_VAL = ':23'                         # 你的 X 显示
CHROME_BIN = '/opt/google/chrome'           # Chrome 路径
USER_DATA_ROOT = '/home/ubuntu/task/hyper/chrome_data'  # 用户数据根目录
TARGET_URL = 'https://node.hyper.space/'
# ==========================

def get_points(tab):
    # 获取积分：点击按钮后从剪贴板读取
    if __click_ele(tab, "x://button[.//span[text()='Points']]"):
        time.sleep(15)  # 确保剪贴板内容更新
        # “Accumlated points” 可能有拼写差异，这里用 contains 提高容错
        target_div = tab.ele("x://div[contains(normalize-space(.),'Accum') and contains(normalize-space(.),'points')]/following-sibling::div")
        return target_div.text if target_div else None

def __click_ele(_page, xpath: str = '', loop: int = 5, must: bool = False,
                find_all: bool = False,
                index: int = -1) -> bool:
    loop_count = 1
    while True:
        try:
            if not find_all:
                _page.ele(locator=xpath).click()
            else:
                _page.eles(locator=xpath)[index].click()
            return True
        except Exception:
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return False
        loop_count += 1

def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
              find_all: bool = False,
              index: int = -1):
    loop_count = 1
    while True:
        try:
            if not find_all:
                txt = page.ele(locator=xpath)
                if txt:
                    return txt
            else:
                txt = page.eles(locator=xpath)[index]
                if txt:
                    return txt
        except Exception:
            pass
        if loop_count >= loop:
            if must:
                raise Exception(f'未找到元素:{xpath}')
            return None
        loop_count += 1

def signma_log(message: str, task_name: str, index: str) -> bool:
    try:
        url = "{}?ip={}&&type={}&&id={}&&data={}"
        server_url = 'http://150.109.5.143:9900'
        full_url = url.format(server_url, args.ip, task_name, index, message)
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

def get_date_as_string():
    return datetime.now().strftime("%Y-%m-%d")

# ============== 新增：进程与页面管理 ==============

def build_profiles(param: str):
    """把 --param 解析为 profile 列表，含公钥、私钥、端口、user-data 路径。"""
    profiles = []
    for idx, part in enumerate(param.split("||")):
        im_public_key, im_private_Key = part.split(",", 1)
        profiles.append({
            "public": im_public_key.strip(),
            "private": im_private_Key.strip(),
            "port": BASE_PORT + idx,
            "user_data": f"{USER_DATA_ROOT}/{im_public_key.strip()}",
        })
    return profiles

def launch_page(profile: dict) -> ChromiumPage:
    """启动或连接到指定 profile 的 Chrome，并打开页面，必要时导入私钥。"""
    os.environ['DISPLAY'] = DISPLAY_VAL
    options = ChromiumOptions()
    options.set_browser_path(CHROME_BIN)
    options.set_user_data_path(profile["user_data"])
    options.set_local_port(profile["port"])

    page = ChromiumPage(options)
    page.page_id = profile["public"]
    # 自定义记录端口/路径，便于重启时兜底关闭
    page._dp_port = profile["port"]
    page._user_data = profile["user_data"]

    page.get(TARGET_URL)
    time.sleep(10)

    # 如首次使用该 profile，导入私钥（存在则按钮一般可点击到输入框）
    if __click_ele(page, "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
        if __click_ele(page, "x://div[contains(@class, 'cursor-text')]"):
            logger.info("write key")
            page.actions.type(profile["private"])
            time.sleep(1)
            __click_ele(page, "x://button[normalize-space()='IMPORT KEY']")
            time.sleep(5)
            page.refresh()
            time.sleep(3)

    # 关闭私钥弹窗（如果存在）
    __click_ele(_page=page, xpath='x://button[.//span[text()="Close"]]', loop=2)
    return page

def launch_all_profiles(profiles):
    pages = []
    for i, pf in enumerate(profiles, start=1):
        logger.info(f"启动:{pf['public']}")
        page = launch_page(pf)
        pages.append(page)
        time.sleep(60)  # 你原来的节流
    return pages

def graceful_close(page: ChromiumPage):
    """尽量优雅关闭；不行再按端口 kill 兜底。"""
    port = getattr(page, '_dp_port', None)
    # 1) 优雅关闭
    for closer in ('quit', 'close'):
        try:
            fn = getattr(page, closer, None)
            if callable(fn):
                fn()
                return
        except Exception:
            pass
    # 2) 尝试关闭 browser 对象
    try:
        if hasattr(page, 'browser') and hasattr(page.browser, 'quit'):
            page.browser.quit()
            return
    except Exception:
        pass
    # 3) 兜底：按端口杀掉该实例
    if port:
        try:
            subprocess.run(['pkill', '-f', f'--remote-debugging-port={port}'], check=False)
        except Exception:
            pass

def restart_browsers(pages: list, profiles: list) -> list:
    logger.warning("开始重启 Chrome 实例（两天周期）...")
    # 先关
    for p in pages:
        graceful_close(p)
    time.sleep(3)
    # 再拉起
    new_pages = launch_all_profiles(profiles)
    logger.warning("Chrome 实例已全部重启。")
    return new_pages

# ============== 你的监控循环 + 重启触发 ==============

def monitor_switch(pages, profiles):
    total = 70
    last_restart = time.monotonic()  # 用单调时钟计时更稳
    while True:
        try:
            time.sleep(random.randint(60, 80))
            for idx, tab in enumerate(pages, start=1):
                if __get_ele(page=tab, xpath='x://button[@role="switch"]', loop=2):
                    if __click_ele(_page=tab, xpath='x://button[@role="switch" and @aria-checked="false"]', loop=2):
                        logger.info("未链接网络")
                    else:
                        logger.info(f"已链接网络:{total}")
                        if __get_ele(page=tab, xpath='x://span[text()="Connected"]', loop=1):
                            if total > 60:
                                # 每 60 次检测一次积分
                                points = get_points(tab)
                                __click_ele(tab, 'x://button[.//span[text()="Close"]]')
                                if points:
                                    logger.info("appInfo", args.ip + ',采集积分,' + str(points))
                                    logger.info(f"推送积分:{points}")
                                    signma_log(message=f"{points}",
                                               task_name=f'hyper_point_{get_date_as_string()}',
                                               index=tab.page_id)
                else:
                    logger.info("刷新页面")
                    tab.refresh()

            if total > 60:
                total = 0
            total += 1

            # —— 检查是否到达两天，触发重启 ——
            if time.monotonic() - last_restart >= RESTART_INTERVAL_SEC:
                pages[:] = restart_browsers(pages, profiles)  # 原地替换列表内容
                last_restart = time.monotonic()

        except Exception as e:
            logger.info("appInfo", args.ip + ',检查过程中出现异常: ' + str(e))

# ============== 入口 ==============

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--param", type=str, help="参数")
    parser.add_argument("--ip", type=str, help="参数")
    args = parser.parse_args()

    # 解析账号 -> 启动所有实例
    profiles = build_profiles(args.param)
    pages = launch_all_profiles(profiles)

    # 进入循环，持续监控切换按钮状态，并按两天周期重启
    monitor_switch(pages=pages, profiles=profiles)
