import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from loguru import logger

def send_chat_request(authorization, user_question):
    # 设置 URL 和 headers
    url = "https://asia.gaia.domains/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {authorization}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # 设置请求体
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_question}
        ]
    }

    # 发送 POST 请求
    response = requests.post(url, headers=headers, json=data)

    # 返回响应内容
    return response.json()


def read_questions_from_file(file_path):
    with open(file_path, "r") as file:
        questions = file.readlines()
    # 过滤掉空白行并去除每行末尾的换行符
    return [question.strip() for question in questions if question.strip()]

def get_random_question(questions):
    return random.choice(questions)

def extract_response_content(response):
    # 从返回结果中提取 message 中的 content
    return response['choices'][0]['message']['content']


# 主任务调度
def run_tasks(questions, tokens):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []

        # 提交所有任务，不需要等待每个任务完成
        for token in tokens:
            future = executor.submit(__do_task, token, questions)
            futures.append(future)

    logger.info("所有任务完成")


def __do_task(token, questions):
    # 计划提问次数
    run_count = random.randint(2, 5)
    split_data = token.split(':')
    for i in range(run_count):
        random_question = get_random_question(questions)
        logger.info(f"{split_data[0]}提问: {random_question}")
        response = send_chat_request(split_data[1], random_question)
        logger.info(f"{split_data[0]}回答结果1")
        # logger.info(f"{split_data[0]}回答结果1: {response}")
        response = send_chat_request(split_data[1], f"Optimize the following results as a professional, {extract_response_content(response)}")
        logger.info(f"{split_data[0]}回答结果2")
        # logger.info(f"{split_data[0]}回答结果2: {response}")
    return True


if __name__ == "__main__":
    questions_file_path = "C://Users//liulei//Desktop//service//questions.txt"
    token_file_path = "C://Users//liulei//Desktop//service//wallet//gaia_token.txt"

    while True:
        questions = read_questions_from_file(questions_file_path)
        tokens = read_questions_from_file(token_file_path)
        run_tasks(questions, tokens)
