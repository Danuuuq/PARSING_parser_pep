import re
from urllib.parse import urljoin
import logging
from collections import defaultdict

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from constants import BASE_DIR, MAIN_DOC_URL, PEP_DOC_URL
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import get_response, find_tag, check_status
from exceptions import ParserFindTagException


def whats_new(session) -> list:
    """Парсинг раздела What's New в документации Python."""
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    soup = BeautifulSoup(response.text, 'lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = find_tag(div_with_ul, 'li',
                                  attrs={'class': 'toctree-l1'},
                                  many_tags=True)

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session) -> list:
    """Парсинг последних версий Python."""
    response = get_response(session, MAIN_DOC_URL)
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = find_tag(sidebar, 'ul', many_tags=True)
    for ul_tag in ul_tags:
        if 'All versions' in ul_tag.text:
            a_tags = find_tag(ul_tag, 'a', many_tags=True)
            break
    else:
        raise ParserFindTagException('Ничего не нашлось')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append((link, version, status))
    return results


def pep(session) -> list:
    """Парсинг PEP-документов."""
    response = get_response(session, PEP_DOC_URL)
    soup = BeautifulSoup(response.text, 'lxml')
    all_pep = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    pep_rows = all_pep.find_all('tr')
    pep_rows = find_tag(all_pep, 'tr', many_tags=True)
    results = defaultdict(int)
    results['Status'] = 'Total'
    for pep_row in tqdm(pep_rows):
        columns = pep_row.find_all('td')
        if len(columns) == 0:
            continue
        status, url_pep_page = columns[:2]
        status = status.text[1:]
        url_pep_page = find_tag(url_pep_page, 'a')['href']
        pep_link = urljoin(PEP_DOC_URL, url_pep_page)
        status_pep = check_status(session, status, pep_link)
        results[status_pep] += 1
    results['Total'] = sum([i for i in results.values() if i != 'Total'])
    return list(results.items())


def download(session) -> None:
    """Загрузка архива с документацией."""
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    soup = BeautifulSoup(response.text, 'lxml')
    main_div = find_tag(soup, 'div', attrs={'class': 'document'})
    table_tag = find_tag(main_div, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(table_tag, 'a',
                          attrs={'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_tag = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_tag)
    filename = archive_url.split('/')[-1]
    download_dir = BASE_DIR / 'downloads'
    download_dir.mkdir(exist_ok=True)
    archive_path = download_dir / filename
    response = get_response(session, archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
