import time

def install_chrome_extension(
        coordinates: list,
        max_retry_times: int = 3
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

    # 安装扩展
    for attempt in range(1, max_retry_times + 1):
        print(f"\n=== 尝试第 {attempt}/{max_retry_times} 次 ===")

        try:
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

        except Exception as e:
            print(f"第 {attempt} 次尝试出现异常: {e}")

        if attempt < max_retry_times:
            print(f"等待 3 秒后重试...")
            time.sleep(3)

    print(f"\n✗ 所有 {max_retry_times} 次尝试都失败了")
    return False


if __name__ == '__main__':
    COORDINATES = [

        (66, 15, 3),
        (92, 247, 2),
        (92, 247, 2),
        (225, 247, 3),

        (1150, 600, 3),
        (1235, 592, 3),
        (730, 774, 3),

        (929, 108, 2),
        (655, 775, 2),

        (44, 156, 2),
        (111, 766, 2),

        (920, 156, 3),
        (92, 212, 2),

        (446, 192, 2),
        (628, 225, 2),
        (628, 225, 0),  # 双击
        (628, 225, 3),
        (1471, 128, 2)
    ]

    # 调用函数
    success = install_chrome_extension(coordinates=COORDINATES, max_retry_times=1)
