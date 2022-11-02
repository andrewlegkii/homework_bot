import logging
import time
from http import HTTPStatus
import os

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
old_message = ''


class APIAnswerError(Exception):
    """Кастомная ошибка при незапланированной работе API."""

    pass


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
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
    except Exception as error:
        raise SystemError(f'Ошибка получения запроса, {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        logger.info('успешное получение конечной точки')
        homework = homework_statuses.json()
        return homework


def check_response(response):
    """Функция проверки корректности ответа API Яндекс.Практикум."""
    if not isinstance(response, dict):
        # ПРОБУЮ СДЕЛАТЬ, КАК ВЫ ПРЕДЛОГАЛИ,
        # НО НЕ ОЧЕНЬ  ПОЛУЧАЕТСЯ, ЕЩЕ ПРОБУЮ
        logging.error('API передал не словарь')
        raise TypeError('API передал не словарь')
    homework = response.get('homeworks')
    if homework is None:
        logging.error('API не содержит ключа homeworks')
        raise KeyError('API не содержит ключа homeworks')
    if not isinstance(homework, list):
        logging.error('Содержимое не список')
        raise TypeError('Содержимое не список')
    return homework


def parse_status(homework):
    """Функция, проверяющая статус домашнего задания."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_name and homework_status:
        if homework_status in HOMEWORK_STATUSES:
            verdict = HOMEWORK_STATUSES.get(homework_status)
            return ('Изменился статус проверки '
                    + f'работы "{homework_name}". {verdict}')
        else:
            raise SystemError('неизвестный статус')
    else:
        raise KeyError('нет нужных ключей в словаре')


def check_tokens():
    """Функция проверки наличия токена и чат id телеграмма."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.critical('Ошибка импорта токенов Telegramm.')
        return False
    elif not PRACTICUM_TOKEN:
        raise SystemError('Ошибка импорта токенов Домашки.')
    else:
        return True


def main():
    """Основная логика работы бота."""
    global old_message
    if not check_tokens():
        raise SystemExit('Я вышел')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME

    while True:
        try:
            response = get_api_answer(current_timestamp)
            response = check_response(response)

            if len(response) > 0:
                homework_status = parse_status(response[0])
                if homework_status is not None:
                    send_message(bot, homework_status)
            else:
                logger.debug('нет новых статусов')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != old_message:
                send_message(bot, message)
                old_message = message
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
