import logging

from requests import RequestException
from bs4 import BeautifulSoup

from exceptions import ParserFindTagException
from constants import EXPECTED_STATUS


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def check_status(session, status, url):
    status = EXPECTED_STATUS[status]
    response = get_response(session, url)
    soup = BeautifulSoup(response.text, 'lxml')
    pep_info = soup.find(id='pep-content')
    pep_list = pep_info.find('dl',
                             attrs={'class': 'rfc2822 field-list simple'})
    dt_status = pep_list.find(text='Status')
    actual_status = dt_status.find_next('dd').text
    if actual_status not in status:
        error_msg = f'''Несовпадающий статус PEP:
                     Ссылка на карточку: {url}
                     Статус в карточке: {actual_status}
                     Ожидаемый статус: {status}'''
        logging.error(error_msg)
    return actual_status
