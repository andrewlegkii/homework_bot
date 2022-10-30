import logging
import time
from http import HTTPStatus
import os
import sys

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_TOKEN')
BOT = telegram.Bot(token=TELEGRAM_TOKEN)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

class MException(Exception):
    """Кастомное исключение для бота."""

    pass

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Функция отправки сообщения в чат телеграмма."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Успешная отправка сообщения.')
    except Exception as error:
        raise SystemError(f'Не отправляются сообщения, {error}')


def get_api_answer(current_timestamp):
    """Функция запроса к API Яндекс.Практикум."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(
            f'Сбой работы {homework_statuses.status_code}')
        send_message(
            BOT, f'Сбой работы {homework_statuses.status_code}')
        raise MException(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}')
    status_json = homework_statuses.json()
    return status_json



def check_response(response):
    """Функция проверки корректности ответа API Яндекс.Практикум."""
    if not isinstance(response['homeworks'], list):
        logging.error('Запрос к серверу пришел с ошибкой')
        send_message(BOT, 'Запрос к серверу пришел с ошибкой')
        raise MException('Ошибка')
    return response['homeworks']



def parse_status(homework):
    """Функция, проверяющая статус домашнего задания."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Статус не обнаружен')
        send_message(BOT, 'Статус не обнаружен')
        raise MException('Статус не обнаружен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверки наличия токена и чат id телеграмма."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.critical('Ошибка импорта токенов Telegram.')
        return False
    elif not PRACTICUM_TOKEN:
        raise SystemError('Ошибка импорта токенов Homework.')
    else:
        return True


def main():
    """Основная логика работы бота."""
    global old_message
    if not check_tokens():
        raise SystemExit('Я вышел')

    current_timestamp = int(time.time()) - RETRY_TIME

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            logging.info(f'Обновлен список работ {homework}')
            if len(homework) > 0:
                send_message(BOT, parse_status(homework[0]))
            logging.info('Ожидайте')
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except KeyboardInterrupt:
            stop = input('Прервать работу бота? (Y/y)')
            if stop == 'Y':
                break
            elif stop != 'Y':
                print('продолжение работы')
            if stop == 'y':
                break
            elif stop != 'y':
                print('продолжение работы')



        except Exception as error:
            logging.error(f'Сбой, проверьте код: {error}')
            send_message(BOT, f'Сбой, проверьте код: {error}')
            time.sleep(RETRY_TIME)

if __name__ == '__main__':
    main()
