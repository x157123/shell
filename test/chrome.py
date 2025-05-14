from DrissionPage import ChromiumPage, ChromiumOptions
from loguru import logger
import time


# 打开浏览器
def __get_page(index, user, chrome_port, retry: int = 0):
    page = ChromiumPage(
        addr_or_opts=ChromiumOptions()
        # .set_browser_path(path="/opt/google/chrome/google-chrome")
        .set_proxy(f"192.168.3.107:7890")
        .set_user_data_path(f"/home/{user}/task/test/{index}")
        # .set_argument(f"--proxy-bypass-list=*.local, 192.168.*.*")
        .set_local_port(chrome_port)
        .headless(on_off=False))

    # page.set.window.max()
    return page

# 获取元素
def __get_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
              find_all: bool = False,
              index: int = -1):
    loop_count = 1
    while True:
        logger.info(f'查找元素{xpath}:{loop_count}')
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


# 获取元素内容
def __get_ele_value(page, xpath: str = '', loop: int = 5, must: bool = False,
                    find_all: bool = False,
                    index: int = -1):
    try:
        logger.info(f'获取元素{xpath}')
        _ele = __get_ele(page=page, xpath=xpath, loop=loop, must=must, find_all=find_all, index=index)
        if _ele is not None:
            if _ele:
                return _ele.text
    except Exception as e:
        error = e
        pass
    return None


# 点击元素
def __click_ele(page, xpath: str = '', loop: int = 5, must: bool = False,
                by_js: bool = False,
                find_all: bool = False,
                index: int = -1) -> bool:
    loop_count = 1
    while True:
        logger.info(f'查找元素{xpath}:{loop_count}')
        try:
            if not find_all:
                if by_js:
                    page.ele(locator=xpath).click()
                else:
                    page.ele(locator=xpath).click(by_js=None)
            else:
                page.eles(locator=xpath)[index].click(by_js=None)
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

def monitor(pages, interval=30):
    """每隔 interval 秒，依次检查所有页面的速度并必要时重连"""
    while True:
        for nexus_page in pages:
            speed = __get_ele_value(page=nexus_page, xpath='x://*[@id="speed-display"]')
            if speed is None or speed == '0':
                __click_ele(page=nexus_page, xpath='x://*[@id="connect-toggle-button"]')
        time.sleep(interval)


if __name__ == '__main__':
    pages = []
    for offset in range(1, 6):
        port = 52558 + offset
        page = __get_page(index=offset, user='lm', chrome_port=port, retry=1)
        nexus = page.new_tab(url='https://app.nexus.xyz')

        checkbox = __get_ele(page=nexus, xpath="x://input[@type='checkbox']")
        if checkbox.attr('checked') is not None:
            print("Battery saver 已经勾选，无需操作")
        else:
            print("Battery saver 未勾选，开始点击勾上")
            checkbox.click()
        pages.append(nexus)
    monitor(pages=pages)



