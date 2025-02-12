import pyautogui
import keyboard
import time
import threading

# 全局变量，用于标识是否处于持续记录状态
recording = False

def toggle_recording():
    """切换记录状态"""
    global recording
    recording = not recording
    if recording:
        print("开始持续记录鼠标位置...")
    else:
        print("停止持续记录鼠标位置。")

def record_positions():
    """后台线程：在记录状态下持续获取鼠标位置"""
    while True:
        if recording:
            # 获取当前鼠标坐标
            x, y = pyautogui.position()
            print(f"鼠标位置：X = {x}, Y = {y}")
            # 可根据需要调整记录频率（单位：秒）
            time.sleep(1)
        else:
            # 未处于记录状态时，稍作休眠，避免 CPU 占用过高
            time.sleep(0.1)

# 注册 F4 热键，每次按下 F4 切换记录状态
keyboard.add_hotkey('F4', toggle_recording)

# 启动后台线程，负责持续记录鼠标位置
record_thread = threading.Thread(target=record_positions, daemon=True)
record_thread.start()

print("按下 F7 开始/停止持续记录鼠标位置，按 ESC 键退出程序。")
keyboard.wait('esc')
