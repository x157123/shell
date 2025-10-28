from DrissionPage import ChromiumPage, ChromiumOptions
from loguru import logger
import time

def install_chrome_extension(
        extension_id: str,
        coordinates: list,
        max_retry_times: int = 3,
        page: ChromiumPage = None
) -> bool:
    """
    安装 Chrome 扩展

    Args:
        extension_id: 扩展 ID
        coordinates: 文件选择坐标列表 [(x, y, wait_time), ...]
        max_retry_times: 最大重试次数
        page: ChromiumPage 实例，如果未提供则创建新实例

    Returns:
        bool: 安装成功返回 True，失败返回 False
    """
    # 检查是否已安装
    def is_installed():
        try:
            page.get('chrome://extensions/')
            time.sleep(1)

            extensions_manager = page.ele('tag:extensions-manager')
            if not extensions_manager:
                return False

            items_list = extensions_manager.shadow_root.ele('tag:extensions-item-list')
            if not items_list:
                return False

            for item in items_list.shadow_root.eles('tag:extensions-item'):
                if item.attr('id') and extension_id in item.attr('id'):
                    print(f"✓ 扩展已安装 (ID: {extension_id})")
                    return True
            return False
        except:
            return False

    # 安装扩展
    for attempt in range(1, max_retry_times + 1):
        print(f"\n=== 尝试第 {attempt}/{max_retry_times} 次 ===")

        try:
            # 如果已安装，直接返回
            if is_installed():
                return True

            # 访问扩展页面
            page.get('chrome://extensions/')
            time.sleep(1)

            # 获取必要元素
            extensions_manager = page.ele('tag:extensions-manager')
            if not extensions_manager:
                continue

            toolbar = extensions_manager.shadow_root.ele('tag:extensions-toolbar')
            if not toolbar:
                continue

            # 开启开发者模式
            dev_mode_toggle = toolbar.shadow_root.ele('#devMode')
            if dev_mode_toggle and not dev_mode_toggle.property('checked'):
                dev_mode_toggle.click()
                print("✓ 已开启开发者模式")
                time.sleep(0.5)

            # 点击加载未打包的扩展程序
            load_unpacked_btn = toolbar.shadow_root.ele('#loadUnpacked')
            if load_unpacked_btn:
                load_unpacked_btn.click()
                print("✓ 已点击'加载未打包的扩展程序'按钮")
                import pyautogui
                pyautogui.FAILSAFE = False
                # 执行文件选择操作
                for x, y, wait_time in coordinates:
                    pyautogui.moveTo(x, y)
                    time.sleep(wait_time)
                    pyautogui.click()
                    if wait_time == 0:  # 双击
                        pyautogui.click()
                time.sleep(0.5)

                # 验证安装
                time.sleep(2)
                if is_installed():
                    print(f"✓ 第 {attempt} 次尝试成功！扩展已安装")
                    return True

        except Exception as e:
            print(f"第 {attempt} 次尝试出现异常: {e}")

        if attempt < max_retry_times:
            print(f"等待 3 秒后重试...")
            time.sleep(3)

    print(f"\n✗ 所有 {max_retry_times} 次尝试都失败了")
    return False


def __get_page():
    options = ChromiumOptions()

    # 1. 设置浏览器路径
    options.set_browser_path('/opt/google/chrome')

    # 2. 使用系统默认的Chrome用户数据目录
    options.set_user_data_path("/home/ubuntu/.config/google-chrome")

    # 3. 使用Default配置文件
    options.set_argument('--profile-directory', 'Default')
    options.set_argument('--no-first-run', True)
    options.set_argument('--no-default-browser-check', True)

    # 4. 【关键修复】使用auto_port()自动分配端口,而不是set_local_port(0)
    options.auto_port()

    logger.info('正在启动浏览器...')
    _pages = ChromiumPage(options)
    logger.info('浏览器初始化成功')
    return _pages


if __name__ == '__main__':
    _page = __get_page()

    MAX_RETRY_TIMES = 3
    COORDINATES = [
        (446, 192, 1),
        (628, 225, 1),
        (628, 225, 0),  # 双击
        (628, 225, 1),
        (1471, 128, 1)
    ]

    # 调用函数
    success = install_chrome_extension(extension_id="ldninhacpndiahonpdbojalkpicbnldj", coordinates=COORDINATES,
                                       max_retry_times=MAX_RETRY_TIMES, page=_page)

    nexus = _page.new_tab(url='https://x.com')
    time.sleep(1000000)