import time
from DrissionPage._base.chromium import Chromium
from DrissionPage._configs.chromium_options import ChromiumOptions
from DrissionPage._base.wait import Wait
from loguru import logger
import pyperclip


def configure_browser():
    """配置并启动浏览器"""
    co = ChromiumOptions().set_local_port(9515).set_paths(r"/opt/google/chrome/google-chrome")
    arguments = [
        "--accept-lang=en-US", "--no-first-run", "--force-color-profile=srgb",
        "--metrics-recording-only", "--password-store=basic", "--use-mock-keychain",
        "--export-tagged-pdf", "--disable-gpu", "--disable-web-security",
        "--disable-infobars", "--disable-popup-blocking", "--allow-outdated-plugins",
        "--deny-permission-prompts", "--disable-suggestions-ui", "--window-size=1920,1080",
        "--disable-mobile-emulation", "--user-data-dir=/tmp/DrissionPage/userData/9515",
        "--disable-features=ServerSentEvents"
    ]

    for arg in arguments:
        co.set_argument(arg)

    co.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

    browser = Chromium(co)
    tab = browser.new_tab(url="https://node.hyper.space/")
    return tab


def click_element(tab, xpath, timeout=2):
    """点击页面元素，若元素不存在则返回False"""
    try:
        element = Wait(tab, timeout=timeout).until(xpath)
        element.click()
        logger.info(f"Clicked the element: {xpath}")
        return True
    except TimeoutError:
        logger.info(f"No element found for XPath: {xpath} within {timeout} seconds.")
        return False
    except Exception as e:
        logger.error(f"Error while clicking element {xpath}: {e}")
        return False


def get_clipboard_text():
    """从剪贴板获取文本"""
    time.sleep(1)  # 确保剪贴板内容更新
    clipboard_text = pyperclip.paste()
    logger.info(f"Clipboard text: {clipboard_text}")
    return clipboard_text


def get_points(tab):
    # 获取积分：点击按钮后从剪贴板读取
    if click_element(tab, "x://button[.//span[text()='Points']]"):
        time.sleep(3)  # 确保剪贴板内容更新
        # 定位到指定的 div 元素并获取其文本内容
        target_div = tab.ele("x://div[text()='Accumlated points']/following-sibling::div")
        # 获取该 div 中的文本
        text = target_div.text
        logger.info(f"Text from the div: {text}")


def main():
    # 启动浏览器
    tab = configure_browser()

    # 关闭弹窗（如果存在）
    click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)

    # 切换按钮（将状态从未开启变为开启）
    click_element(tab, 'x://button[@role="switch" and @aria-checked="false"]', timeout=5)

    # 获取公钥：点击按钮后从剪贴板读取
    if click_element(tab, "x://p[contains(text(), 'Public Key:')]/following-sibling::div//button"):
        public_key = get_clipboard_text()

    # 获取私钥：点击按钮后从剪贴板读取
    if click_element(tab, "x://div[contains(@class, 'justify-between') and .//p[contains(text(), 'Public Key:')]]/button"):
        if click_element(tab, "//button[contains(., 'copy current private key')]"):
            private_key = get_clipboard_text()

    # 关闭私钥弹窗（如果存在）
    click_element(tab, 'x://button[.//span[text()="Close"]]', timeout=2)

    # 获取积分:
    get_points(tab)



def get_app_info(serverId, appId, operationType, description):
    return {
        "serverId": f"{serverId}",
        "applicationId": f"{appId}",
        "operationType": f"{operationType}",
        "description": f"{description}",
    }


if __name__ == '__main__':
    main()

