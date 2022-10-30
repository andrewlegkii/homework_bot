import logging
import time
from http import HTTPStatus

import requests
import telegram


PRACTICUM_TOKEN = 'y0_AgAAAAAXiCsAAAYckQAAAADSK0Hl09fR7BlkQYmlndKB9V20yFj7Q3U'
TELEGRAM_TOKEN = '5646566299:AAHBZofSNIfnzEVtWw57XKvdKAjBt4u_n-g'
TELEGRAM_CHAT_ID = 360300829

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
    if homework_statuses.status_code == HTTPStatus.OK:
        logger.info('успешное получение конечной точки')
        homework = homework_statuses.json()
        if 'error' in homework:
            raise SystemError(f'Ошибка json, {homework["error"]}')
        elif 'code' in homework:
            raise SystemError(f'Ошибка json, {homework["code"]}')
        else:
            return homework
    elif homework_statuses.status_code == HTTPStatus.REQUEST_TIMEOUT:
        raise SystemError(f'Ошибка код {homework_statuses.status_code}')
    elif homework_statuses.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        raise SystemError(f'Ошибка код {homework_statuses.status_code}')
    else:
        raise SystemError(
            f'Ошибка, код {homework_statuses.status_code}')


def check_response(response):
    """Функция проверки корректности ответа API Яндекс.Практикум."""
    if isinstance(response, list):
        response = response[0]
        logging.info('API передал список')
    if not isinstance(response, dict):
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
    if PRACTICUM_TOKEN is None:
        logging.error('PRACTICUM_TOKEN not found')
        return False
    elif TELEGRAM_CHAT_ID is None:
        logging.error('TELEGRAM_CHAT_ID not found')
        return False
    elif TELEGRAM_TOKEN is None:
        logging.error('TELEGRAM_TOKEN not found')
        return False
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

        except KeyboardInterrupt:
            stop = input('Прервать работу бота? (Y)')
            if stop == 'Y':
                break
            elif stop != 'Y':
                print('Бот работает дальше')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != old_message:
                bot.send_message(TELEGRAM_CHAT_ID, message)
                old_message = message
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
