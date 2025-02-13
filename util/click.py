import pyautogui
import time

ips = [
    "8.220.198.30",
    "8.213.146.185",
    "8.220.242.89",
    "8.220.244.19",
    "8.220.218.116"
]

defPwd = "LH99aPbFm0uQ6S+5sr6"


def init(ip):
    # 1. 点击屏幕上指定位置（这里的坐标(100, 200)可以根据需要修改）
    pyautogui.click(x=-1992, y=645)
    time.sleep(0.5)  # 点击后稍作等待
    # 2. 模拟键盘输入文字（这里输入 "Hello, world!"，可根据需要修改文本）
    pyautogui.write(ip, interval=0.1)
    time.sleep(0.5)
    # 3. 再次点击屏幕上另外一个指定位置（坐标(300, 400)可根据需要修改）
    pyautogui.click(x=-1719, y=653)
    # 给你一些时间切换到目标窗口（比如3秒）
    time.sleep(3)
    # 重置密码
    pyautogui.click(x=-2137, y=1144)
    # 第一个密码框
    time.sleep(1)
    pyautogui.click(x=-1552, y=480)
    pyautogui.write(defPwd, interval=0.1)
    # 第二个密码框
    time.sleep(1)
    pyautogui.click(x=-1552, y=550)
    pyautogui.write(defPwd, interval=0.1)
    # 在线修改密码
    pyautogui.click(x=-1552, y=638)
    # 确定修改
    pyautogui.click(x=-1096, y=812)
    time.sleep(8)
    #确定
    pyautogui.click(x=-1016, y=513)
    time.sleep(2)


for ip in ips:
    init(ip)
