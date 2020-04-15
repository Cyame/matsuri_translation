from celery import Celery
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from celery.exceptions import SoftTimeLimitExceeded
import time
import png
from .celeryconfig import self_url
from urllib import parse
from .tweet_process import TweetProcess
import json

celery = Celery('api')
celery.config_from_object('Matsuri_translation.celeryconfig')


def insert_text_chunk(src_png, dst_png, text):
    reader = png.Reader(filename=src_png)
    chunks = reader.chunks()  # ����һ��ÿ�η���һ��chunk��������
    chunk_list = list(chunks)  # ��������������Ԫ�ر��list
    # print(f"target png total chunks number is {len(chunk_list)}")
    chunk_item = tuple([b'tEXt', text])

    # ��һ��chunk�ǹ̶���IHDR�����ǰ�tEXt���ڵ�2��chunk
    index = 1
    chunk_list.insert(index, chunk_item)

    with open(dst_png, 'wb') as dst_file:
        png.write_chunks(dst_file, chunk_list)


@celery.task(time_limit=300, soft_time_limit=240)
def execute_event(event):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) Waterfox/56.2")
    # chrome_options.add_argument("--proxy-server=127.0.0.1:12333")
    driver = webdriver.Chrome(options=chrome_options)
    try:
        processor = TweetProcess(driver)
        processor.open_page(event['url'])
        processor.modify_tweet()
        processor.scroll_page_to_tweet(event['fast'])
        filename = processor.save_screenshots()
    except:
        driver.save_screenshot(f'Matsuri_translation/frontend/cache/LastError.png')
    finally:
        # time.sleep(5)
        driver.quit()
    return filename


@celery.task(time_limit=300, soft_time_limit=240)
def execute_event_auto(event):
    eventStartTime = int(round(time.time() * 1000))
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=TweetoasterAutomaticMode")
    # ����UA�Դ���Google Analytics
    # chrome_options.add_argument("--proxy-server=127.0.0.1:12333")
    driver_frontend = webdriver.Chrome(options=chrome_options)
    try:
        processor = TweetProcess(driver_frontend)
        param = {
            'tweet': event['tweet'],
            'template': event['template'],
            'out': 1
        }
        if event['translate'] != '':
            param['translate'] = event['translate']
        if 'noLikes' in event and event['noLikes']:
            param['noLikes'] = event['noLikes']
        processor.open_page(self_url + "?" + parse.urlencode(param).replace("+", "%20"))
        # time.sleep(20)
        try:
            WebDriverWait(driver_frontend, 60, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'canvas')))
        except:
            driver_frontend.save_screenshot(f'Matsuri_translation/frontend/cache/LastErrorAuto.png')
        finally:
            filename = processor.save_screenshots_auto(eventStartTime)
            try:
                event["filename"] = filename
                insert_text_chunk(f'Matsuri_translation/frontend/cache/{filename}.png',
                                  f'Matsuri_translation/frontend/cache/{filename}.png',
                                  json.dumps(event).encode("utf-8"))
            except:
                print("error in metadata")
    finally:
        # time.sleep(5)
        driver_frontend.quit()
    return filename
