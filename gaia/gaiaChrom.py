import subprocess
import os
import signal
from DrissionPage._pages.chromium_page import ChromiumPage
import time
from DrissionPage._configs.chromium_options import ChromiumOptions
import paho.mqtt.client as mqtt
import json
import argparse
from loguru import logger
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import random
from datetime import datetime, timedelta


# =================================================   MQTT   ======================================
def create_mqtt_client(broker, port, username, password, topic):
    """
    创建并配置MQTT客户端，使用 MQTTv5 回调方式
    protocol=mqtt.MQTTv5 来避免旧版回调弃用警告
    """
    client = mqtt.Client(
        protocol=mqtt.MQTTv5,  # 指定使用 MQTTv5
        userdata={"topic": topic}  # 传递自定义数据
    )
    client.username_pw_set(username, password)

    # 注册回调函数（使用 v5 风格签名）
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        raise ConnectionError(f"Error connecting to broker: {e}")

    return client


# ========== MQTT 事件回调函数（MQTTv5） ==========
def on_connect(client, userdata, flags, reason_code, properties=None):
    """
    当客户端与 Broker 建立连接后触发
    reason_code = 0 表示连接成功，否则为失败码
    """
    if reason_code == 0:
        print("Connected to broker successfully.")
        # 仅发布消息，去除订阅
        pass
    else:
        print(f"Connection failed with reason code: {reason_code}")


def on_disconnect(client, userdata, reason_code, properties=None):
    """
    当客户端与 Broker 断开连接后触发
    可以在此处进行自动重连逻辑
    """
    print(f"Disconnected from broker, reason_code: {reason_code}")
    # 如果 reason_code != 0，则表示非正常断开
    while True:
        try:
            print("Attempting to reconnect...")
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # 等待 5 秒后重试


def on_message(client, userdata, msg):
    """
    当收到订阅主题的新消息时触发
    v5 中的 on_message 参数与 v3.x 相同： (client, userdata, message)
    """
    print(f"Message received on topic {msg.topic}: {msg.payload.decode()}")


# =================================================   MQTT   ======================================


def read_file(file_path):
    """从文件中读取内容并去除多余空白"""
    try:
        # logger.info(f"读取文件: {file_path}")
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError(f"文件未找到: {file_path}")


def decrypt_aes_ecb(secret_key, data_encrypted_base64, key):
    """
    解密 AES ECB 模式的 Base64 编码数据，
    去除 PKCS7 填充后返回所有 accountType 为 "hyper" 的记录中的指定 key 值列表。
    """
    try:
        # Base64 解码
        encrypted_bytes = base64.b64decode(data_encrypted_base64)
        # 创建 AES 解密器
        cipher = AES.new(secret_key.encode('utf-8'), AES.MODE_ECB)
        # 解密数据
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        # 去除 PKCS7 填充（AES.block_size 默认为 16）
        decrypted_bytes = unpad(decrypted_bytes, AES.block_size)
        # 将字节转换为字符串
        decrypted_text = decrypted_bytes.decode('utf-8')

        # logger.info(f"获取数据中的 {key}: {decrypted_text}")

        # 解析 JSON 字符串为 Python 对象（通常为列表）
        data_list = json.loads(decrypted_text)

        # 创建结果列表，收集所有匹配的 key 值
        result = []
        for item in data_list:
            if item.get('accountType') == 'gaia':
                value = item.get(key)
                if value is not None:  # 确保只添加存在的 key 值
                    result.append(value)

        # 返回结果列表，如果没有匹配项则返回空列表
        return result

    except Exception as e:
        raise ValueError(f"解密失败: {e}")


class TaskSet:
    def __init__(self, args):
        global q
        self.appId = args.appId
        self.serverId = args.serverId
        self.co = ChromiumOptions()
        self.meta_id = 'dholkoaddiccbagimjcfjaldcacogjgc'
        self.co.set_paths(r"/opt/google/chrome/google-chrome")
        self.ex_path = r"/home/" + args.user + "/extensions/chrome-cloud"
        self.co.set_user_data_path(
            os.path.join("/home/" + args.user + "/task/" + args.chromePort + "/", args.index))
        self.co.add_extension(self.ex_path)
        self.co.set_argument('--start-maximized')

        self.co.set_user_agent(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )

        self.co.set_local_port(args.chromePort)

        self.browser = ChromiumPage(addr_or_opts=self.co)
        self.tab = self.browser.latest_tab
        self.browser.set.cookies.clear()
        self.res_info = None
        self.dmail_tab = None
        self.__thank_list = """
            Thank you.
            Thanks.
            Many thanks.
            Thanks a lot.
            Thank you very much.
            I really appreciate it.
            I appreciate your help.
            Thanks a million.
            Thank you so much.
            I’m grateful for your help.
            Your help is greatly appreciated.
            Thanks for your time.
            I can’t thank you enough.
            Thank you for your kindness.
            Thanks for everything.
            I owe you one.
            You’re a lifesaver, thank you.
            Thank you for your understanding.
            Thanks for having me.
            Thank you for considering this.
            """.strip().split('\n')

        self.__story_title = [
            # Weight Loss (减肥)
            "What are the most effective exercises for losing belly fat?",
            "How can I lose weight without dieting?",
            "What are the best foods for weight loss?",
            "Can drinking water help with weight loss?",
            "How long does it take to lose 10 pounds?",
            "What are the risks of rapid weight loss?",
            "Is intermittent fasting effective for weight loss?",
            "Can sleep affect my weight loss progress?",
            "What are some common weight loss mistakes?",
            "How does stress impact weight gain?",

            # Computers (计算机)
            "What is the difference between RAM and ROM?",
            "How does a CPU process information?",
            "What is an operating system?",
            "How can I improve my computer’s speed?",
            "What is the role of a motherboard?",
            "What is cloud computing?",
            "What is the difference between SSD and HDD?",
            "How do computer viruses spread?",
            "What is the purpose of a firewall?",
            "Why is cybersecurity important?",

            # Artificial Intelligence (人工智能)
            "What is machine learning?",
            "How does deep learning differ from machine learning?",
            "What are neural networks in AI?",
            "Can AI surpass human intelligence?",
            "What are the applications of AI in healthcare?",
            "What are some ethical concerns about AI?",
            "What is natural language processing?",
            "How does facial recognition work?",
            "Can AI write creative content?",
            "What are the dangers of AI in the wrong hands?",

            # Health (健康)
            "How can I improve my immune system?",
            "What are the benefits of regular exercise?",
            "How does stress affect my health?",
            "What foods should I avoid for better health?",
            "How can I maintain a balanced diet?",
            "What are some ways to reduce high blood pressure?",
            "How much water should I drink daily?",
            "What is the best way to handle anxiety?",
            "Why is mental health just as important as physical health?",
            "How do vitamins affect our health?",

            # Meditation (冥想)
            "How do I start a meditation practice?",
            "What are the benefits of daily meditation?",
            "How long should I meditate for beginners?",
            "Can meditation help reduce stress?",
            "What is mindfulness meditation?",
            "How does meditation improve sleep?",
            "Can meditation enhance creativity?",
            "What is guided meditation?",
            "How do I maintain focus during meditation?",
            "What are the different types of meditation?",

            # Home (家居)
            "What are some budget-friendly home decor ideas?",
            "How can I make my home more eco-friendly?",
            "What are the best plants for home interiors?",
            "How can I organize my living space?",
            "What are the benefits of smart home technology?",
            "How do I create a cozy home atmosphere?",
            "What’s the best way to maintain hardwood floors?",
            "How can I reduce clutter at home?",
            "What are some tips for small apartment living?",
            "How do I decorate a room on a budget?",

            # Beauty (美妆)
            "What is the best skincare routine for oily skin?",
            "How can I reduce acne breakouts?",
            "What makeup products are best for sensitive skin?",
            "How can I achieve a natural makeup look?",
            "What are the benefits of using a facial serum?",
            "How do I prevent makeup from fading throughout the day?",
            "What are the top anti-aging products?",
            "How can I protect my skin from sun damage?",
            "What is the best foundation for dry skin?",
            "How often should I exfoliate my skin?",

            # Phones (手机)
            "What is the best phone for gaming?",
            "How do I improve my phone’s battery life?",
            "What’s the difference between Android and iOS?",
            "What are some hidden features of smartphones?",
            "How do I clean my phone’s screen properly?",
            "How can I make my phone run faster?",
            "What should I look for in a smartphone camera?",
            "How can I free up space on my phone?",
            "Are foldable phones worth the investment?",
            "What are the latest trends in smartphone technology?",

            # Beer (啤酒)
            "What are the different types of beer?",
            "How is craft beer different from regular beer?",
            "What foods pair best with beer?",
            "What is the difference between lager and ale?",
            "How do I properly store beer?",
            "What are some health benefits of drinking beer?",
            "How do I pour beer correctly?",
            "What is the alcohol content of a typical beer?",
            "How can I make my own beer at home?",
            "What are the best beers for beginners?",

            # Fashion (着装)
            "What are the essentials for a minimalist wardrobe?",
            "How can I style a white shirt in different ways?",
            "What shoes should I wear for comfort and style?",
            "How do I pick the right clothes for my body type?",
            "What are the best accessories to wear for a night out?",
            "How can I wear a suit without looking too formal?",
            "What is the best color for a professional wardrobe?",
            "How do I keep my clothes looking new longer?",
            "What are the trends in fashion for this season?",
            "How can I wear a dress for both day and night?",

            # Travel (旅游)
            "What are the best tips for budget travel?",
            "How do I plan a solo travel trip?",
            "What are the must-see destinations in Europe?",
            "How do I stay healthy while traveling?",
            "What’s the best way to pack for a week-long trip?",
            "How can I travel safely in a foreign country?",
            "What are the best apps for international travel?",
            "How can I find cheap flights online?",
            "What are the most popular tourist attractions in Asia?",
            "What should I know before visiting a new country?",

            # Outdoor & Sports (运动户外)
            "What are the best outdoor exercises for beginners?",
            "How do I prepare for a long-distance hike?",
            "What are the benefits of outdoor running?",
            "How can I get better at cycling?",
            "What should I bring on a camping trip?",
            "What’s the best way to stay active during winter?",
            "What are some great team sports for beginners?",
            "How do I protect myself from the sun during outdoor activities?",
            "What are some safety tips for rock climbing?",
            "How can I improve my endurance for sports?",
            "How can I lose weight effectively without a strict diet?",
            "What are the latest trends in computer science?",
            "How can artificial intelligence improve healthcare?",
            "What are the benefits of drinking water for health?",
            "How does mindfulness meditation help reduce stress?",
            "What are some easy home decor ideas on a budget?",
            "What are the must-have skincare products for sensitive skin?",
            "Which smartphone has the best camera quality?",
            "What is the best beer for someone new to craft beers?",
            "How can I choose the right outfit for a business interview?",
            "What are the top destinations for solo travel?",
            "What is the best outdoor workout for beginners?",
            "What are some quick ways to lose belly fat?",
            "How do you build a career in computer programming?",
            "What role does AI play in autonomous vehicles?",
            "What foods should I avoid for better gut health?",
            "How long should I meditate each day for maximum benefits?",
            "What are the latest trends in modern interior design?",
            "How can I get clear skin naturally?",
            "What are the top features to look for in a smartphone?",
            "What are the health benefits of drinking craft beer in moderation?",
            "How can I improve my wardrobe with a small budget?",
            "What is the best travel destination for adventure seekers?",
            "What are the benefits of outdoor exercise?",
            "How can I increase my metabolism to lose weight faster?",
            "What programming languages should I learn for artificial intelligence?",
            "How does machine learning impact our daily lives?",
            "What are the most effective ways to stay hydrated?",
            "How can I meditate effectively in a busy environment?",
            "What is the importance of minimalism in home decor?",
            "How do I find a skincare routine that works for me?",
            "What smartphone apps help track fitness goals?",
            "What is the difference between IPA and lager beers?",
            "How do I dress for different seasons while staying stylish?",
            "What are the best destinations for a relaxing beach vacation?",
            "How can I improve my flexibility for outdoor activities?",
            "What are some quick exercises to burn calories at home?",
            "What are the latest advancements in artificial intelligence?",
            "How can I use AI to automate my daily tasks?",
            "What is the healthiest diet to support weight loss?",
            "How does mindfulness meditation impact mental clarity?",
            "What are the best home organization hacks?",
            "What are the top beauty products for oily skin?",
            "How do I choose the right smartphone for gaming?",
            "What are the health benefits of drinking dark beer?",
            "What is the best way to mix and match outfits?",
            "What are the top adventure travel destinations for 2025?",
            "How can I prepare for an outdoor hiking trip?",
            "What are some effective exercises to lose weight fast?",
            "How can computer science help solve climate change?",
            "What are the ethical concerns surrounding artificial intelligence?",
            "What foods can improve brain health?",
            "How does breathing meditation reduce anxiety?",
            "What are some stylish yet functional home decor ideas?",
            "How can I create a skincare routine that’s easy to follow?",
            "Which smartphone features are essential for everyday use?",
            "What are some types of beer to try for beginners?",
            "How can I create a professional yet fashionable work wardrobe?",
            "What are the best off-the-beaten-path travel destinations?",
            "What should I pack for an active outdoor vacation?",
            "How can I avoid overeating while losing weight?",
            "What is the best way to learn coding for artificial intelligence?",
            "What are the key applications of AI in healthcare?",
            "How do probiotics help with digestive health?",
            "How long should I meditate each morning?",
            "What are some budget-friendly home decor tips?",
            "What is the best skincare routine for acne-prone skin?",
            "What is the best smartphone for social media?",
            "What are the best beers to pair with different foods?",
            "How can I dress to feel confident at any occasion?",
            "What are the top travel destinations for nature lovers?",
            "How can I stay motivated to work out outdoors?",
            "What are the most effective exercises to tone muscles?",
            "How do AI algorithms help in social media recommendations?",
            "What are the biggest challenges in artificial intelligence?",
            "What are the benefits of intermittent fasting for weight loss?",
            "How can meditation improve focus and concentration?",
            "How can I refresh my living room with minimal effort?",
            "What skincare products help with aging skin?",
            "Which smartphone has the best battery life?",
            "What are some unique craft beer styles to try?",
            "How do I create a capsule wardrobe for work?",
            "What are the top destinations for cultural travel?",
            "How do I stay safe when hiking alone?",
            "What are some fun ways to incorporate outdoor workouts?",
            "What are some low-impact exercises for weight loss?",
            "How can artificial intelligence be used in education?",
            "What are some ways to increase my productivity using AI?",
            "What are the top foods for boosting immunity?",
            "What are the psychological benefits of regular meditation?",
            "How can I organize my home for a more productive environment?",
            "What are the most effective anti-aging skincare ingredients?",
            "What are the best smartphones for multitasking?",
            "How can I learn more about the craft beer brewing process?",
            "What should I wear for a job interview in tech?",
            "What are the best hiking trails in Europe?",
            "What are some outdoor activities that burn the most calories?",
            "How can I lose weight without sacrificing my social life?",
            "What is the best programming language for AI development?",
            "How can AI assist in personalized learning?",
            "What are some high-protein foods for weight loss?",
            "How can meditation help with managing chronic pain?",
            "How can I make my bedroom feel more spacious?",
            "What skincare ingredients should I avoid if I have sensitive skin?",
            "How can I choose the right smartphone for photography?",
            "What is the difference between craft beer and mass-produced beer?",
            "How do I create a wardrobe for every season?",
            "What are the best hidden gems for travel enthusiasts?",
            "How can I prepare my body for a long outdoor hike?",
            "What are the most effective workouts to target fat loss?",
            "How do AI algorithms predict consumer behavior?",
            "What are some ethical dilemmas in artificial intelligence?",
            "How can I build muscle and lose fat at the same time?",
            "What role does meditation play in reducing emotional reactivity?",
            "What are some quick home renovation ideas?",
            "How do different skincare products affect acne?",
            "What are the best smartphones for video editing?",
            "What beers are best for pairing with pizza?",
            "How can I build a versatile wardrobe on a budget?",
            "What are the best eco-friendly travel destinations?",
            "How do I stay fit when traveling?",
            "What are some simple outdoor activities for improving fitness?",
            "How can I get rid of stubborn belly fat?",
            "How can I improve my AI skills for a career in tech?",
            "What are the most popular AI applications in daily life?",
            "What types of foods are best for maintaining good mental health?",
            "How does mindfulness meditation help with decision-making?",
            "How can I improve my home’s energy efficiency?",
            "What are the best skincare products for dry skin?",
            "What smartphone features should I prioritize for gaming?",
            "What are the best types of beer to try at a bar?",
            "How can I create a minimalist wardrobe?",
            "What are some good travel destinations for nature photography?",
            "What are the essential things to pack for an outdoor adventure?",
            "How do I incorporate outdoor activities into my fitness routine?",
            "What are the most effective fat-burning exercises at home?",
            "How can AI be used to improve personalized healthcare?",
            "What are some of the challenges faced by AI in medicine?",
            "How do antioxidants help with weight loss?",
            "How can meditation improve emotional intelligence?",
            "How can I transform my living space on a budget?",
            "What are some natural skincare treatments for glowing skin?",
            "What are the best smartphones for multitasking?",
            "What is the best craft beer to drink during the summer?",
            "How can I enhance my wardrobe without spending too much?",
            "What are the best places to visit for a hiking vacation?",
            "How do I prepare for a long-distance outdoor run?",
            "What are some fun outdoor activities for weight loss?",
            "How do AI chatbots work and how can they be improved?",
            "What are some challenges that artificial intelligence faces in natural language processing?",
            "What are some foods that can help reduce inflammation?",
            "How can I use meditation to improve my sleep quality?",
            "What are some home decor trends for 2025?",
            "How do I choose the best skincare routine for my skin type?",
            "What smartphone has the best user interface?",
            "What is the best beer for someone who doesn’t like bitter flavors?",
            "How can I dress for success without breaking the bank?",
            "What are some of the top cities for digital nomads?",
            "How can I stay active when traveling for work?",
            "What are the best outdoor activities for family fitness?",
            "What are the easiest ways to shed fat without exercise?",
            "What programming languages are crucial for AI research?",
            "How does AI impact data privacy?",
            "What are some foods that help to reduce stress?",
            "How can meditation improve your overall productivity?",
            "What are some simple home decor ideas for small spaces?",
            "What are the top skincare products for brightening your complexion?",
            "What are the best smartphones for photography in 2025?",
            "What beers are best paired with cheese?",
            "How can I create a chic work wardrobe on a budget?",
            "What are the best travel destinations for winter sports?",
            "What are the best outdoor activities for mental health?",
            "How can I improve my cardiovascular health?",
            "What is the best AI for home automation?",
            "What are the benefits of using AI in customer service?",
            "What are some foods that boost metabolism?",
            "How does meditation help with managing stress at work?",
            "How can I redecorate my house with minimal cost?",
            "What are the top skincare ingredients for acne prevention?",
            "What are the best smartphones for battery longevity?",
            "What beers are best for beginners?",
            "How can I curate a stylish wardrobe for work?",
            "What are some lesser-known travel destinations?",
            "How can I stay fit during a vacation?",
            "What are the best outdoor exercises for beginners?",
            "What are the most effective ways to lose weight quickly?",
            "How can I reduce belly fat in a month?",
            "What are the top diet plans for weight loss?",
            "Is intermittent fasting a good strategy for weight loss?",
            "How many calories should I consume to lose weight?",
            "How can I stay motivated during a weight loss journey?",
            "What are the benefits of drinking water for weight loss?",
            "Can a vegetarian diet help with weight loss?",
            "How important is sleep for weight loss?",
            "How does exercise contribute to weight loss?",
            "What are the key components of a balanced diet?",
            "How can I maintain weight loss after reaching my goal?",
            "What are the most common mistakes people make while losing weight?",
            "What foods should I avoid to lose weight?",
            "How can I lose weight without feeling hungry all the time?",
            "What role does stress play in weight gain?",
            "Can supplements aid in weight loss?",
            "How does eating late at night affect weight loss?",
            "How much cardio is needed to lose weight?",
            "Can strength training help with weight loss?",

            "What are the best programming languages for beginners?",
            "What is the difference between Python and Java?",
            "How can I become a software engineer?",
            "What are the most in-demand programming languages?",
            "What is machine learning and how does it work?",
            "How do algorithms work in computer science?",
            "What are the best resources for learning coding?",
            "What is the difference between a compiler and an interpreter?",
            "How do I build my first website?",
            "What is the role of a database in computing?",
            "How does cloud computing work?",
            "What is the best way to learn data structures and algorithms?",
            "What are the most common errors in coding?",
            "How do I debug my code effectively?",
            "What is object-oriented programming?",
            "What is the future of computer programming?",
            "How do I become a full-stack developer?",
            "What is version control and why is it important?",
            "How does the internet work?",
            "What is artificial intelligence?",

            "What is artificial intelligence and how does it function?",
            "How does machine learning differ from artificial intelligence?",
            "What are the applications of artificial intelligence in everyday life?",
            "How can artificial intelligence impact the future of work?",
            "What are neural networks and how do they work?",
            "How does AI improve healthcare?",
            "What are the ethical concerns surrounding artificial intelligence?",
            "How can AI be used in education?",
            "What is deep learning and how does it relate to AI?",
            "What are the risks associated with AI in decision-making?",
            "How is AI being used in autonomous vehicles?",
            "What are chatbots and how do they work?",
            "How does AI impact data security?",
            "What are the limitations of artificial intelligence?",
            "How does natural language processing work in AI?",
            "Can AI ever be truly conscious?",
            "What are the dangers of AI in military applications?",
            "How does AI affect the job market?",
            "What are some examples of AI being used in entertainment?",
            "What are the most advanced AI technologies available today?",

            "How can I improve my overall health?",
            "What are the best ways to stay healthy?",
            "How important is mental health in overall well-being?",
            "What foods should I include in my diet for better health?",
            "How can I reduce stress and stay healthy?",
            "How often should I exercise to stay healthy?",
            "What is the importance of hydration for health?",
            "How can I improve my sleep quality for better health?",
            "What vitamins and minerals are essential for good health?",
            "How can I boost my immune system naturally?",
            "What are the benefits of a plant-based diet?",
            "How do I know if I am healthy or not?",
            "How does smoking affect my health?",
            "What are the long-term benefits of exercise for health?",
            "How can I avoid getting sick during cold and flu season?",
            "What are some signs of a healthy lifestyle?",
            "How can I maintain my health as I age?",
            "How does mental health affect physical health?",
            "What are the benefits of regular checkups with a doctor?",
            "How can I lower my cholesterol naturally?",

            "What is meditation and how can it help me?",
            "How do I start a daily meditation practice?",
            "What are the benefits of mindfulness meditation?",
            "How does meditation reduce stress?",
            "How long should I meditate each day?",
            "Can meditation improve sleep quality?",
            "What is the difference between mindfulness and meditation?",
            "What types of meditation are best for beginners?",
            "How can meditation improve my focus?",
            "What is transcendental meditation?",
            "Can meditation help with anxiety and depression?",
            "What is guided meditation and how does it work?",
            "How does deep breathing relate to meditation?",
            "Can meditation improve my emotional well-being?",
            "How do I stay focused during meditation?",
            "What is the role of a mantra in meditation?",
            "How can I incorporate meditation into my daily routine?",
            "What is the best time of day to meditate?",
            "Can meditation help with pain management?",
            "What are the spiritual benefits of meditation?",

            "What are the latest trends in home decor?",
            "How can I make my home feel more cozy?",
            "What are the best tips for organizing your home?",
            "How do I choose the right furniture for my space?",
            "What are some small space living tips?",
            "How can I decorate my home on a budget?",
            "What are the most popular home design styles?",
            "How can I make my home more energy-efficient?",
            "What are the best plants for indoor decor?",
            "How can I add personality to my home with art?",
            "How do I create a minimalist home design?",
            "What colors are trending in home decor this year?",
            "How can I make my small apartment feel bigger?",
            "What are some practical tips for home improvement?",
            "What are the benefits of open shelving in kitchens?",
            "How do I make my home more sustainable?",
            "How can I improve my outdoor living space?",
            "What are the essential items for a functional kitchen?",
            "What is the best way to organize a home office?",
            "How can I incorporate smart home technology into my space?",

            "What are the best beauty products for glowing skin?",
            "How do I create a skincare routine?",
            "What are the benefits of using natural beauty products?",
            "How can I get rid of acne scars?",
            "What is the best way to take care of dry skin?",
            "How can I make my skin look younger?",
            "What are the top anti-aging skincare tips?",
            "How do I choose the right foundation for my skin type?",
            "What are the best makeup products for a natural look?",
            "How can I get rid of dark circles under my eyes?",
            "What are the benefits of using sunscreen daily?",
            "How do I prevent hair loss?",
            "What are the best ways to hydrate my skin?",
            "How can I achieve a flawless makeup look?",
            "What skincare ingredients should I look for?",
            "How do I manage oily skin?",
            "What is the best makeup for sensitive skin?",
            "What are some DIY beauty treatments for glowing skin?",
            "How can I enhance my lashes naturally?",
            "What are the best ways to get rid of blackheads?",

            "What are the latest smartphone features?",
            "How do I choose the best smartphone for my needs?",
            "What is the difference between Android and iOS?",
            "How can I make my phone battery last longer?",
            "What are the top smartphone apps for productivity?",
            "How do I transfer data between phones?",
            "What are the best phones for gaming?",
            "How do I protect my smartphone from viruses?",
            "What are the benefits of using a phone case?",
            "How can I improve the performance of my smartphone?",
            "What is the best phone for photography?",
            "How do I manage storage on my phone?",
            "What are the latest trends in smartphone design?",
            "How can I save battery on my iPhone?",
            "What are some must-have accessories for my smartphone?",
            "How do I enable mobile hotspot on my phone?",
            "What is 5G and how does it affect smartphones?",
            "How can I protect my smartphone privacy?",
            "What are the best apps for editing photos on my phone?",
            "How do I upgrade my smartphone's software?",

            "What are the different types of beer?",
            "How is beer made?",
            "What is the difference between craft beer and mass-produced beer?",
            "What are the best beers for beginners?",
            "How do I taste beer like a connoisseur?",
            "What is the role of hops in beer?",
            "How do I pair beer with food?",
            "What is a lager vs an ale?",
            "What is the alcohol content in beer?",
            "How is gluten-free beer made?",
            "What are the health benefits of drinking beer?",
            "What are the most popular beer brands in the world?",
            "How should beer be stored?",
            "What are the different beer styles?",
            "How do I serve beer properly?",
            "What is the history of beer?",
            "What is the process of brewing beer?",
            "What is a beer tasting event?",

        ]
        # 主题列表
        topics = [
            "weight loss", "computer", "artificial intelligence", "health", "meditation",
            "home decor", "makeup", "smartphone", "beer", "fashion", "travel", "sports & outdoors"
        ]

        # 生成500个随机提问
        questions = []
        for _ in range(500):
            topic = random.choice(topics)
            if topic == "weight loss":
                q = random.choice([
                    "How to lose belly fat fast?",
                    "Best exercises for weight loss?",
                    "Is keto diet effective?",
                    "How many calories to lose weight?",
                    "What foods help burn fat?",
                    "How to stay motivated to lose weight?",
                    "Is intermittent fasting safe?",
                    "Best apps for weight loss?",
                    "How to avoid weight loss plateaus?",
                    "Can drinking water help lose weight?"
                ])
            elif topic == "computer":
                q = random.choice([
                    "How to speed up a slow PC?",
                    "Best laptops for programming?",
                    "How to build a gaming PC?",
                    "What is cloud computing?",
                    "How to fix a frozen computer?",
                    "Best antivirus software?",
                    "How to recover deleted files?",
                    "What is a GPU used for?",
                    "How to upgrade RAM?",
                    "What is the best operating system?"
                ])
            elif topic == "artificial intelligence":
                q = random.choice([
                    "What is machine learning?",
                    "How does AI work?",
                    "Best programming language for AI?",
                    "What are neural networks?",
                    "How to start a career in AI?",
                    "What is deep learning?",
                    "Can AI replace humans?",
                    "What is natural language processing?",
                    "How to train an AI model?",
                    "What are AI ethics?"
                ])
            elif topic == "health":
                q = random.choice([
                    "How to boost immunity?",
                    "What are superfoods?",
                    "How to lower cholesterol?",
                    "Best vitamins for energy?",
                    "How to improve gut health?",
                    "What causes high blood pressure?",
                    "How to sleep better?",
                    "What is a balanced diet?",
                    "How to reduce stress?",
                    "What are the signs of diabetes?"
                ])
            elif topic == "meditation":
                q = random.choice([
                    "How to meditate for beginners?",
                    "What are the benefits of meditation?",
                    "Best meditation apps?",
                    "How to focus during meditation?",
                    "What is mindfulness?",
                    "How long should I meditate?",
                    "Can meditation reduce anxiety?",
                    "What is guided meditation?",
                    "How to create a meditation routine?",
                    "What is transcendental meditation?"
                ])
            elif topic == "home decor":
                q = random.choice([
                    "How to decorate a small apartment?",
                    "Best colors for a living room?",
                    "How to organize a closet?",
                    "What is minimalist decor?",
                    "How to choose the right furniture?",
                    "Best lighting for a bedroom?",
                    "How to style a bookshelf?",
                    "What are trending home decor ideas?",
                    "How to make a room cozy?",
                    "What is Scandinavian design?"
                ])
            elif topic == "makeup":
                q = random.choice([
                    "How to apply foundation?",
                    "Best makeup for oily skin?",
                    "How to do a smokey eye?",
                    "What is contouring?",
                    "How to choose the right lipstick?",
                    "Best mascara for volume?",
                    "How to remove makeup easily?",
                    "What is the no-makeup look?",
                    "How to make makeup last longer?",
                    "What are the best makeup brands?"
                ])
            elif topic == "smartphone":
                q = random.choice([
                    "How to extend battery life?",
                    "Best smartphones under $500?",
                    "How to take better photos?",
                    "What is 5G?",
                    "How to free up storage space?",
                    "Best apps for productivity?",
                    "How to protect my phone from hackers?",
                    "What is the best phone camera?",
                    "How to use dark mode?",
                    "What are the latest phone trends?"
                ])
            elif topic == "beer":
                q = random.choice([
                    "How is beer made?",
                    "Best beers for beginners?",
                    "What is IPA?",
                    "How to pair beer with food?",
                    "What is craft beer?",
                    "How to store beer properly?",
                    "What are the health benefits of beer?",
                    "How to pour a perfect beer?",
                    "What is the alcohol content of beer?",
                    "Best beer festivals in the world?"
                ])
            elif topic == "fashion":
                q = random.choice([
                    "How to dress for a job interview?",
                    "Best outfits for summer?",
                    "How to style a leather jacket?",
                    "What are capsule wardrobes?",
                    "How to choose the right shoes?",
                    "Best fashion trends this year?",
                    "How to accessorize an outfit?",
                    "What is sustainable fashion?",
                    "How to dress for your body type?",
                    "What are timeless fashion pieces?"
                ])
            elif topic == "travel":
                q = random.choice([
                    "Best travel destinations in 2023?",
                    "How to pack light for a trip?",
                    "What are hidden travel gems?",
                    "How to find cheap flights?",
                    "Best travel apps?",
                    "How to stay safe while traveling?",
                    "What to do in Paris?",
                    "How to plan a budget trip?",
                    "What are eco-friendly travel tips?",
                    "How to overcome jet lag?"
                ])
            elif topic == "sports & outdoors":
                q = random.choice([
                    "Best hiking trails in the US?",
                    "How to start running?",
                    "What are the benefits of yoga?",
                    "How to choose a camping tent?",
                    "Best exercises for strength?",
                    "How to stay hydrated during sports?",
                    "What are the best outdoor activities?",
                    "How to train for a marathon?",
                    "What is HIIT?",
                    "How to prevent sports injuries?"
                ])
            questions.append(q)

            self.__story_title = self.__story_title + questions

    def restart_task(self, args):
        """Restart the task by reinitializing the TaskSet object."""
        self.__init__(args)

    def get_app_info(self, serverId, appId, operationType, publicKey, description):
        return {
            "serverId": f"{serverId}",
            "applicationId": f"{appId}",
            "operationType": f"{operationType}",
            "publicKey": f"{publicKey}",
            "description": f"{description}",
        }

    def signma_log(self, message: str, task_name: str, index: str, server_url: str, chain_id="9004"):
        logger.info("数据。" + message)
        client.publish("appInfo",
                       json.dumps(self.get_app_info(self.serverId, self.appId, 3, index, message)))

    # 添加网络
    def __add_net_work(self, page, coin_name='base'):
        obj = {
            'arb': 42161,
            'base': 8453,
            'opt': 10,
        }
        number = obj[coin_name]
        url = f'https://chainlist.org/?search={number}&testnets=false'
        page.get(url=url)
        time.sleep(2)
        logger.info('点击1')
        page.wait.ele_displayed(loc_or_ele='x://button[text()="Connect Wallet"]', timeout=10)
        logger.info('点击2')
        self.__click_ele(page=page, xpath=f'x://td[contains(text(), "{number} ")]/../../../following-sibling::button[1]')
        logger.info('点击3')
        time.sleep(3)
        logger.info('点击4')
        self.__deal_window(page=page)
        time.sleep(2)
        logger.info('点击5')
        self.__click_ele(page=page,
                               xpath=f'x://td[contains(text(), "{number} ")]/../../../following-sibling::button[1]')
        time.sleep(2)
        logger.info('点击6')
        self.__deal_window(page=page)
        logger.info('点击7')
        if self.browser.tabs_count >= 2:
            logger.info('点击8')
            self.__deal_window(page=page)
        time.sleep(3)
        if self.browser.tabs_count >= 2:
            logger.info('点击9')
            self.__deal_window(page=page)
        return True

    # 处理弹窗
    def __deal_window(self, page):
        # 如果窗口大于2才进行操作
        if self.browser.tabs_count >= 2:
            time.sleep(3)
            tab = self.browser.get_tab()
            logger.info(tab)
            if '/popup.html?page=%2Fdapp-permission' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                self.__click_ele(page=tab, xpath='x://button[@id="grantPermission"]')
                time.sleep(2)

            elif '/notification.html#connect' in tab.url:
                self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                time.sleep(2)

            elif '/notification.html#confirmation' in tab.url:
                self.__click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                time.sleep(2)
                self.__click_ele(page=tab, xpath='x://*[@data-testid="confirmation-submit-button"]')
                time.sleep(2)

            elif '/notification.html#confirm-transaction' in tab.url:
                self.__click_ele(page=tab, xpath='x://*[@data-testid="page-container-footer-next"]')
                time.sleep(2)

            elif '/popup.html?page=%2Fsign-transaction' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)

            elif '/popup.html?page=%2Fsign-data' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)

            elif 'popup.html?page=%2Fpersonal-sign' in tab.url:
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                self.__click_ele(page=tab, xpath='x://button[@id="sign"]')
                time.sleep(2)

            elif ('&tab=%2Fadd-evm-chain' in tab.url) or ('/popup.html?requestId=' in tab.url):
                if tab.wait.ele_displayed(loc_or_ele='x://*[@id="close"]', timeout=1):
                    self.__click_ele(page=tab, xpath='x://*[@id="close"]')
                    time.sleep(1)
                self.__click_ele(page=tab, xpath='x://button[@id="addNewChain"]')
                time.sleep(2)

            elif '&page=%2Fadd-evm-chain' in tab.url:
                self.__click_ele(page=tab, xpath='x://button/div[text()="关闭"]')

            elif 'popout.html?windowId=backpack' in tab.url:
                self.__click_ele(page=tab, xpath='x://div/span[text()="确认"]')
                time.sleep(2)
        return True
    
    def setup_wallet(self, args):
        self.tab = self.browser.new_tab(url="chrome://extensions/")
        time.sleep(12)
        self.tab.wait.ele_displayed("x://html/body/extensions-manager", 30)
        toggle_ele = (
            self.tab.ele(
                "x://html/body/extensions-manager"
            )  # /html/body/extensions-manager
            .shadow_root.ele('x://*[@id="viewManager"]')
            .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
            .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
            .shadow_root.ele("tag:cr-toggle@@id=enableToggle")
        )

        refresh_ele = (
            self.tab.ele(
                "x://html/body/extensions-manager"
            )  # /html/body/extensions-manager
            .shadow_root.ele('x://*[@id="viewManager"]')
            .ele('x://*[@id="items-list"]')  # //*[@id="items-list"]
            .shadow_root.ele('x://*[@id="ohgmkpjifodfiomblclfpdhehohinlnn"]')
            .shadow_root.ele("tag:cr-icon-button@@id=dev-reload-button")
        )

        if toggle_ele.attr("aria-pressed") == "false":
            toggle_ele.click()
        refresh_ele.click()
        time.sleep(6)
        # pyautogui.moveTo(600, 600)  # 需要你先手动量好按钮在屏幕上的位置
        # pyautogui.click()
        # time.sleep(2)
        # pyautogui.press('enter')
        time.sleep(2)
        if len(self.browser.get_tabs(
                url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding")) > 0:
            wallet_tab = self.browser.get_tab(
                url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
            )
        else:
            wallet_tab = self.browser.new_tab(
                url="chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/tab.html#/onboarding"
            )

        time.sleep(3)
        index_input_path = (
            "x://html/body/div/div[1]/div[4]/section/div/section/div/div/input"
        )
        wallet_tab.ele(index_input_path).input(args.index, clear=True)
        index_button_path = "tag:button@@id=existingWallet"
        index_set_button = wallet_tab.ele(index_button_path)
        time.sleep(1)
        index_set_button.click()

        time.sleep(3)
        result = True
        return result

    def close_browser(self):
        try:
            self.browser.reconnect()
            self.browser.close_tabs(tabs_or_ids=self.tab, others=True)
            self.browser.quit(timeout=60, force=True, del_data=True)
        except Exception as e:
            logger.info(f"错误关闭: {e}")

        try:
            # 获取占用 9518 端口的 PID
            pids = subprocess.getoutput("lsof -t -i:9518 -sTCP:LISTEN")
            if pids:
                pid_list = pids.splitlines()  # 按行分割 PID
                print(f"找到占用 9518 端口的进程: {pid_list}")
                for pid_str in pid_list:
                    try:
                        pid = int(pid_str.strip())  # 转换为整数并移除多余空格
                        os.kill(pid, signal.SIGKILL)
                        logger.info(f"成功终止进程 {pid}")
                        time.sleep(1)  # 每次杀死后等待 1 秒
                    except PermissionError:
                        logger.info(f"无权限终止进程 {pid}，请检查进程所有者和 admin 用户权限")
                    except ValueError:
                        logger.info(f"无效 PID: {pid_str}")
                    except Exception as e:
                        logger.info(f"发生错误: {e}")
            else:
                print("9518 端口未被占用")
        except Exception as e:
            print(f"错误关闭: {e}")

    def process_pop(self):
        if len(self.browser.get_tabs(title="Signma")) > 0:
            pop_tab = self.browser.get_tab(title="Signma")

            back_path = 'x://*[@id="sign-root"]/div/div/section/main/div[1]/section[1]/div/button'
            conn_path = "tag:div@@class=jsx-3858486283 button_content@@text()=连接"
            sign_enable_path = (
                "tag:button@@class=jsx-3858486283 button large primaryGreen"
            )

            sign_blank_path = (
                "tag:div@@class=jsx-1443409666 subtext@@text()^希望您使用您的登录"
            )

            time.sleep(10)

            logger.info("弹出框:"+pop_tab.url)

            if pop_tab.url == 'chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/popup.html?page=%2Fdapp-permission':
                if pop_tab.ele(back_path) is not None:
                    pop_tab.ele(back_path).click()
                time.sleep(2)

                if pop_tab.ele(conn_path) is not None:
                    pop_tab.ele(conn_path).click()
                    time.sleep(3)
            elif pop_tab.url == "chrome-extension://ohgmkpjifodfiomblclfpdhehohinlnn/popup.html?page=%2Fpersonal-sign":
                if pop_tab.ele('x://button[@id="sign"]') is not None:
                    pop_tab.ele('x://button[@id="sign"]').click()
                    time.sleep(2)
            else:
                while pop_tab.wait.ele_displayed(sign_enable_path, timeout=3) is False:
                    if pop_tab.wait.ele_displayed(sign_blank_path, timeout=3):
                        pop_tab.actions.move_to(sign_blank_path)
                        pop_tab.ele(sign_blank_path).click()
                        time.sleep(2)

                if pop_tab.ele(sign_enable_path) is not None:
                    pop_tab.ele(sign_enable_path).click()

    def __click_ele(self, page, xpath: str = '', err: bool = True, find_all: bool = False, index: int = -1) -> int:
        loop_count = 0
        while True:
            try:
                if not find_all:
                    page.ele(locator=xpath).click()
                else:
                    page.eles(locator=xpath)[index].click()
                break
            except Exception as e:
                error = e
                pass
            if loop_count >= 5:
                # print(f'---> {xpath} 无法找到元素。。。', str(error)[:100])
                if err:
                    self.tab.close()
                self.res_info = '元素无法找到'
                return 0
            loop_count += 1
            time.sleep(2)
        return 1

    def __getNumber(self, page, xpath):
        value_elem = page.ele(xpath)
        if value_elem:
            value = value_elem.text
            if value is not None:
                value = value.replace(",", "")
            # logger.info(f"找到{xpath}: {value}")
            return value
        else:
            logger.info(f"未找到{xpath}")
            return 0

    def gaianet(self, args):
        chat_count = 0
        try:
            # 设置钱包
            logger.info('设置钱包')
            res = self.setup_wallet(all_args)
            if res:
                # 设置钱包网络
                logger.info('设置钱包网络')
                self.__add_net_work(page=self.tab, coin_name='base')

                # 兑换积分
                logger.info('兑换积分')
                self.redeem_points(args)

                time.sleep(100)

                self.res_info = ''
                self.tab.get(url='https://www.gaianet.ai/chat')
                logger.info('进入页面，开始访问1')
                time.sleep(5)

                accept_all = self.tab.ele('x://button[text()="Accept All"]')
                if accept_all:
                    self.__click_ele(page=self.tab, xpath='x://button[text()="Accept All"]', err=False)
                logger.info('进入页面，开始访问2')
                time.sleep(2)
                connect = self.tab.ele('x://button[text()="Connect"]')
                if connect:
                    self.__click_ele(page=self.tab, xpath='x://button[text()="Connect"]', err=False)
                    logger.info('进入页面，开始访问3')
                    time.sleep(2)
                    accept = self.tab.ele('x://button[text()="Accept"]')
                    if accept:
                        self.__click_ele(page=self.tab, xpath='x://button[text()="Accept"]', err=False)
                    signma = self.tab.ele('x://div[text()="Signma"]')
                    if signma:
                        logger.info('进入页面，开始访问5')
                        self.__click_ele(page=self.tab, xpath='x://div[text()="Signma"]', err=False)
                    logger.info('进入页面，开始访问4')
                    time.sleep(5)
                    for _ in range(3):
                        self.process_pop()
                        time.sleep(8)
                # self.browser.close_tabs(others=True)

                accept = self.tab.ele('x://button[text()="Accept"]')
                if accept:
                    self.__click_ele(page=self.tab, xpath='x://button[text()="Accept"]', err=False)
                    logger.info('进入页面，开始访问5')
                    sign = self.tab.ele('x://button[text()="SIGN"]')
                    if sign:
                        self.__click_ele(page=self.tab, xpath='x://button[text()="SIGN"]', err=False)
                    logger.info('进入页面，开始访问6')
                    for _ in range(3):
                        self.process_pop()
                        time.sleep(8)
                time.sleep(2)
                self.__click_ele(page=self.tab, xpath='x://a/span[text()="Chat"]')
                time.sleep(2)
                self.__click_ele(page=self.tab, xpath='x://p[text()="SELECT A DOMAIN"]')
                time.sleep(5)

                domain = random.choice([
                    "llama.gaia.domains",
                    "vortex.gaia.domains",
                    "hyper.gaia.domains",
                    "we-are-gaia.gaia.domains",
                ])
                self.res_info = self.res_info + f'domain:{domain}'
                js_code = f"""            
                    const randomDomain = '{domain}'; 
                    Array.from(document.getElementsByTagName('span')).filter(ele => {{
                        (ele?.textContent === randomDomain) ? (ele.scrollIntoView(), ele?.click()) : 0
                    }})
                """

                self.tab.run_js(js_code)
                time.sleep(2)
                chat = self.tab.ele('x://button[text()="Chat"]')
                if chat:
                    self.__click_ele(page=self.tab, xpath='x://a/span[text()="Chat"]')
                time.sleep(2)
                start = self.tab.ele('x://button[text()="Start"]')
                if start:
                    self.__click_ele(page=self.tab, xpath='x://button[text()="Start"]')
                    time.sleep(2)
                if self.tab.wait.ele_displayed(loc_or_ele='x://button[text()="Connect"]', timeout=10) is not False:
                    logger.error(f'link_account {args.index, args.address}')
                    self.close_browser()
                    return False

                self.__click_ele(page=self.tab, xpath='x://button[text()="New chat"]')
                time.sleep(3)

                run_count = random.randint(5, 10)
                self.res_info = self.res_info + f',计划次数:{run_count}'
                for i in range(run_count):

                    content = random.choice(self.__story_title).strip()
                    self.tab.ele(locator='x://textarea[@placeholder="Ask me anything..."]').clear()
                    time.sleep(1)
                    self.tab.ele(locator='x://textarea[@placeholder="Ask me anything..."]').input(content)
                    time.sleep(2)
                    if self.tab.wait.ele_displayed(loc_or_ele='x://button/p[text()="Send"]', timeout=10):
                        self.__click_ele(page=self.tab, xpath='x://button/p[text()="Send"]')
                    if self.tab.wait.ele_displayed(loc_or_ele='x://button/p[text()="Send"]', timeout=80) is False:
                        if self.tab.wait.ele_displayed(loc_or_ele='x://button/p[text()="Stop"]',
                                                       timeout=3) is not False:
                            self.tab.ele(locator='x://button/p[text()="Stop"]').click()
                    else:
                        chat_count = chat_count + 1

                    self.tab.wait.ele_displayed(loc_or_ele='x://button/p[text()="Send"]', timeout=60)
                    time.sleep(3)

                thank_content = random.choice(self.__thank_list).strip()
                self.tab.ele(locator='x://textarea[@placeholder="Ask me anything..."]').input(thank_content)
                time.sleep(2)
                if self.tab.wait.ele_displayed(loc_or_ele='x://button/p[text()="Send"]', timeout=10):
                    self.__click_ele(page=self.tab, xpath='x://button/p[text()="Send"]')

                if self.tab.wait.ele_displayed(loc_or_ele='x://button/p[text()="Send"]', timeout=20) is False:
                    if self.tab.wait.ele_displayed(loc_or_ele='x://button/p[text()="Stop"]', timeout=3) is not False:
                        self.tab.ele(locator='x://button/p[text()="Stop"]').click()
                        self.signma_log('已对话', all_args.task, all_args.index, "https://signma.bll06.xyz")
                # self.res_info = f'已对话,第{args.count}对话'

                # 获取积分
                self.getPoints(args)

            else:
                self.res_info = '钱包初始化错误'
            # logger.info(self.res_info)
            # return True
        except Exception as e:
            logger.info(f"---------发生异常：{str(e)}-----------------")
            self.res_info = self.res_info + f"发生异常：{str(e)}"
        finally:
            self.res_info = f'已对话,第{args.count}回对话,本次执行次数{chat_count}次,' + self.res_info
            self.signma_log(self.res_info, all_args.task, all_args.index, "https://signma.bll06.xyz")

            logger.info(f"---------完成情况：序号:{args.index} {self.res_info}-----------------")

    def redeem_points(self, args):
        self.tab.get(url='https://www.gaianet.ai/reward-summary')
        points = self.__getNumber(self.tab, 'xpath://span[text()="Current Redeemable Points"]/ancestor::div[contains(@class, "justify-between")]/span[contains(@class, "typography-header-8") and not(text()="Current Redeemable Points")]')
        if points > 0:
            redeem = self.tab.ele('x://button[text()="Redeem"]')
            if redeem:
                redeem_now = self.tab.ele('x://button[text()="Redeem Now"]')
                if redeem_now:
                    self.__click_ele(page=self.tab, xpath='x://button[text()="Redeem Now"]')
                    time.sleep(10)
                    loop_count = 0
                    while True:
                        try:
                            credits_balance = self.__getNumber(self.tab, 'x://span[text()="My Credits Balance"]/ancestor::div[contains(@class, "flex-1")]//span[contains(@class, "typography-heading-4-medium")]')
                            if credits_balance <= 0:
                                refresh = self.tab.ele('x://span[text()="My Credits Balance"]/ancestor::div[contains(@class, "flex-1")]//svg[contains(@class, "cursor-pointer")]')
                                if refresh:
                                    self.__click_ele(page=self.tab, xpath='x://span[text()="My Credits Balance"]/ancestor::div[contains(@class, "flex-1")]//svg[contains(@class, "cursor-pointer")]')
                            else:
                                return
                        except Exception as e:
                            error = e
                            pass
                        if loop_count >= 5:
                            return
                        loop_count += 1
                        time.sleep(2)



    def getPoints(self, args):
        global user_points, total_points, task_points, credits_balance, total_redeemed, total_consumed
        self.res_info = ''
        self.tab.get(url='https://www.gaianet.ai/reward-summary')

        container = self.tab.ele(
            locator='x://span[text()="My gaiaPoints (Total)"]/ancestor::div[contains(@class, "flex-1")]')

        if container:
            # 读取 My gaiaPoints (Total) 的值
            # 使用正确的CSS选择器并检查返回值
            total_points = self.__getNumber(self.tab, 'x://span[text()="My gaiaPoints (Total)"]/ancestor::div[contains(@class, "flex-1")]//span[contains(@class, "typography-heading-4-medium")]')
            user_points = self.__getNumber(self.tab, 'xpath://span[text()="User Points"]/ancestor::div[contains(@class, "justify-between")]/span[contains(@class, "typography-heading-8") and not(text()="User Points")]')
            task_points = self.__getNumber(self.tab, 'xpath://span[text()="Task Points"]/ancestor::div[contains(@class, "justify-between")]/span[contains(@class, "typography-heading-8") and not(text()="Task Points")]')
            logger.info(f"My gaiaPoints (Total): {total_points}")
            logger.info(f"User Points: {user_points}")
            logger.info(f"Task Points: {task_points}")
        else:
            logger.info("未找到包含 'My gaiaPoints (Total)' 的容器")

        container = self.tab.ele(
            locator='x://span[text()="My Credits Balance"]/ancestor::div[contains(@class, "flex-1")]')

        if container:
            # 读取 My gaiaPoints (Total) 的值
            # 使用正确的CSS选择器并检查返回值
            credits_balance = self.__getNumber(self.tab, 'x://span[text()="My Credits Balance"]/ancestor::div[contains(@class, "flex-1")]//span[contains(@class, "typography-heading-4-medium")]')
            total_redeemed = self.__getNumber(self.tab, 'x://span[text()="Total Redeemed"]/following-sibling::span[contains(@class, "typography-heading-8")]')
            total_consumed = self.__getNumber(self.tab, 'x://span[text()="Total Consumed"]/following-sibling::span[contains(@class, "typography-heading-8")]')
            logger.info(f"credits_balance: {credits_balance}")
            logger.info(f"total_redeemed: {total_redeemed}")
            logger.info(f"task_points: {total_consumed}")
        else:
            logger.info("未找到包含 'My gaiaPoints (Total)' 的容器")

        app_info = self.get_app_info_integral(total_points,user_points,task_points,credits_balance,total_redeemed,total_consumed)
        client.publish("appInfo", json.dumps(app_info))
        logger.info(f"推送积分:{app_info}")

    def get_app_info_integral(self, integral, integralA, integralB, integralC, integralD, integralE):
        return {
            "serverId": f"{all_args.serverId}",
            "applicationId": f"{all_args.appId}",
            "publicKey": f"{all_args.index}",
            "integral": f"{integral}",
            "integralA": f"{integralA}",
            "integralB": f"{integralB}",
            "integralC": f"{integralC}",
            "integralD": f"{integralD}",
            "integralE": f"{integralE}",
            "operationType": "2",
            "description": f"采集积分：total_points：{integral}，user_points：{integralA}，task_points：{integralB}，credits_balance：{integralC}，total_redeemed：{integralD}，total_consumed：{integralE}",
        }

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="获取应用信息")
    parser.add_argument("--serverId", type=str, help="服务ID", required=True)
    parser.add_argument("--appId", type=str, help="应用ID", required=True)
    parser.add_argument("--decryptKey", type=str, help="解密key", required=True)
    parser.add_argument("--user", type=str, help="执行用户", required=True)
    parser.add_argument("--display", type=str, help="执行窗口", required=True)
    parser.add_argument("--chromePort", type=str, help="浏览器端口", required=True)
    all_args = parser.parse_args()
    data_map = {}

    # 创建 MQTT 客户端（使用 MQTTv5）
    client = create_mqtt_client("150.109.5.143", 1883, "userName", "liuleiliulei", "appInfo")
    client.loop_start()

    # 从文件加载密文
    encrypted_data_base64 = read_file('/opt/data/' + all_args.appId + '_user.json')

    # 解密并发送解密结果
    public_key_tmp = decrypt_aes_ecb(all_args.decryptKey, encrypted_data_base64, 'secretKey')

    if len(public_key_tmp) > 0:
        logger.info(f"发现账号{public_key_tmp}")
        while True:
            current_date = datetime.now().strftime('%Y%m%d')  # 当前日期
            all_args.day_count = 1
            all_args.count = 1
            if current_date in data_map and data_map[current_date] is not None:
                all_args.day_count = data_map[current_date]
                logger.info(f"找到现在第{all_args.day_count}轮")
            if all_args.day_count < 10:
                num = 0
                for key in public_key_tmp:
                    data_key = f"{current_date}_{key}"
                    if data_key in data_map and data_map[data_key] is not None:
                        all_args.count = data_map[data_key]
                        if all_args.count > 6:
                            break
                    else:
                        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                        yesterday_data_key = f"{current_date}_{key}"
                        if yesterday_data_key in data_map:
                            del data_map[yesterday_data_key]
                    num = 1
                    all_args.index = key
                    all_args.task = 'test'
                    all_args.res_info = ''
                    logger.info(f"执行: {key}，次数：{all_args.count}，现在是今日第{all_args.day_count}轮")
                    global task_set
                    try:
                        task_set = TaskSet(all_args)
                        all_args.index = 88762
                        task_set.gaianet(all_args)
                        data_map[data_key] = all_args.count + 1
                    except Exception as e:
                        logger.info(f"发生错误: {e}")
                    finally:
                        task_set.close_browser()
                        time.sleep(random.randint(23, 50))
                logger.info(f"执行完第{all_args.day_count}轮")
                data_map[current_date] = all_args.day_count + 1
            else:
                logger.info(f"执行完毕等待一小时")
                time.sleep(3600)
    else:
        logger.info("未绑定需要执行的账号")
