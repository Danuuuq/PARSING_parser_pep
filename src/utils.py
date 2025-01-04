import logging

from requests import RequestException
from bs4 import BeautifulSoup

from exceptions import ParserFindTagException
from constants import EXPECTED_STATUS


def get_response(session, url) -> str:
    """Получение ответа от сервера.

    :param session: сессия
    :param url: URL-адрес страницы"""
    try:
        response = session.get(url)
    except RequestException:
        error_msg = f'Возникла ошибка при загрузке страницы {url}'
        logging.exception(error_msg, stack_info=True)
        raise RequestException(error_msg)
    else:
        response.encoding = 'utf-8'
        return response


def find_tag(soup, tag, attrs=None, many_tags=False, **kwargs) -> str:
    """Поиск тега на странице.

    :param soup: объект BeautifulSoup
    :param tag: тег искомого элемента
    :param attrs: атрибуты искомого элемента
    :param many_tags: флаг, указывающий на то, что искомых элементов несколько"""
    if many_tags:
        find_tag = soup.find_all(tag, attrs=(attrs or {}), **kwargs)
    else:
        find_tag = soup.find(tag, attrs=(attrs or {}), **kwargs)
    if find_tag is None or not find_tag:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return find_tag


def check_status(session, status, url) -> str:
    """Проверка статуса PEP.

    :param session: сессия
    :param status: ожидаемый статус
    :param url: URL-адрес страницы
    :return: фактический статус"""
    status = EXPECTED_STATUS[status]
    response = get_response(session, url)
    soup = BeautifulSoup(response.text, 'lxml')
    pep_info = find_tag(soup, tag=None, id='pep-content')
    pep_list = find_tag(pep_info, 'dl',
                        attrs={'class': 'rfc2822 field-list simple'})
    dt_status = find_tag(pep_list, tag=None, text='Status')
    actual_status = dt_status.find_next('dd').text
    if actual_status not in status:
        error_msg = f'''Несовпадающий статус PEP:
                     Ссылка на карточку: {url}
                     Статус в карточке: {actual_status}
                     Ожидаемый статус: {status}'''
        logging.error(error_msg)
    return actual_status
