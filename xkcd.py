#!/usr/bin/python3
# coding: utf-8

import os
import re
import click
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from pathlib import Path

pathname = None
collection = []
dnd = [404, 1350, 1416, 1525, 1538, 1608, 1663, 1953, 2067, 2198]
XKCD_URL = 'https://xkcd.com'

@click.group()
@click.option('--folder', default='comics', type=click.Path())
def cli(folder):
    global pathname, collection
    pathname = Path(folder).expanduser().resolve()
    if not pathname.exists():
        os.mkdir(pathname)

@cli.command('stats')
def stats():
    items = folder_items()
    print(f"Number comics in folder: {len(items)}")

@cli.command('latest')
def latest():
    link, issue = latest_comic_info()
    print(f'Latest issue number {issue}, {link}')

@cli.command('analyze')
def analyze():
    link, issue = latest_comic_info()
    current_folder_items = folder_items()
    current_issues = build_current_issues(current_folder_items)
    missing_issues = find_missing_issues(sorted(current_issues), int(issue))
    print(f'Number of comics total:\t{issue}')
    print(f'Number of comics local:\t{len(current_folder_items)}')
    print(f'Interactive comics excluded ({len(dnd)}): {dnd}')
    print(f'Missing Issues:\t{len(missing_issues)}')
    
@cli.command('download')
@click.option('--start', default=1, help='Starting comic issue number.')
@click.option('--end', default=3, help='Ending comic issue number.')
def download(start, end):
    comic_urls = []
    for x in range(start, int(end) + 1):
        comic_urls.append(f'{XKCD_URL}/{x}')
    build_comic_collection(comic_urls)
    print('Download list built: ', len(collection))
    download_comic_collection(collection)
    print('Collection downloaded!')

@cli.command('sync')
def sync():
    link, issue = latest_comic_info()
    current_folder_items = folder_items()
    current_issues = build_current_issues(current_folder_items)
    missing_issues = find_missing_issues(sorted(current_issues), int(issue))
    comic_urls = []
    for issue in missing_issues:
        comic_urls.append(f'{XKCD_URL}/{issue}')
    build_comic_collection(comic_urls)
    print('Download list built: ', len(collection))
    download_comic_collection(collection)
    print('Collection downloaded!')

def download_comic(url):
    if int(url.get('issue')) in dnd:
        return
    filename = f"{pathname}/{url.get('issue')}-{url.get('img_link').split('/')[-1]}"
    with open(filename, 'wb') as handle:
        with requests.get(url.get('img_link'), stream=True) as response:
            if not response.ok:
                print(response)
                return
            file_size = int(response.headers.get('Content-Length', 0))/1000
            print(url.get('title'), "-", "{:.2f}".format(file_size),"Kb")
            for block in response.iter_content(1024):
                if not block:
                    break
                handle.write(block)

def download_comic_collection(to_collect):
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(download_comic, to_collect)

def grab_comic_info(url):
    with requests.get(url) as response:
        soup = BeautifulSoup(response.content, 'lxml')
        comic = soup.find('div', id='comic').find('img')
        issue = re.search(r'\d{1,4}', url)
        collection.append({
            'issue': issue.group(),
            'title': comic['alt'],
            'img_link': 'https:'+comic['src']
        })

def build_comic_collection(urls):
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(grab_comic_info, urls)

def folder_items():
    return os.listdir(pathname)

def build_current_issues(current_items):
    current_issues = []
    for item in current_items:
        issue = re.search(r'\d{1,4}', item)
        current_issues.append(int(issue[0]))
    return current_issues

def find_missing_issues(current_issues, latest_issue_number):
    if len(current_issues)==0:
        start=0
    else:
        start=current_issues[0]
    first_pass = [x for x in range(start, latest_issue_number+1) if x not in current_issues]
    return [x for x in first_pass if x not in dnd]

def latest_comic_info():
    response = requests.get(XKCD_URL)
    soup = BeautifulSoup(response.content, 'lxml')
    middle_content = soup.find('div', id='middleContainer')
    link = re.search(r'https://xkcd.com/\d{1,4}', middle_content.text)
    issue = re.search(r'\d{1,4}', link[0])
    return link[0], issue[0]

if __name__ == '__main__':
    cli()