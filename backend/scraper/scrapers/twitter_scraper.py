from __future__ import annotations

import os
import queue
import time
from datetime import datetime
from datetime import timedelta
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from stocknlp.tasks import enqueue_scraper_data

from ..scraper import LogTypes
from ..scraper import Scraper
from ..scraper import ScraperStates
# import chromedriver_autoinstaller
### DB RELATED IMPORTS ###
### INTERNAL IMPORTS ###

load_dotenv()
username = os.getenv('twitter_username')
password = os.getenv('twitter_password')
email = os.getenv('twitter_email')


class TwitterScraper(Scraper):
    def __init__(self):
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        scraper_config = {
            'crawl_interval': 60,
            'source': [{'name': 'twitter', 'base_url': 'https://x.com/search?q='}],
            'credentials': {
                'email': email,
                'login': username,
                'password': password,
            },
            'max_time_running': None,
            'threads': 1,
            'twitter_query': {
                'start_date': yesterday,
                'end_date': today,
                'params': {
                    'filter': ['links', 'replies', 'media&src=typed_query'],
                    'lang': 'en',
                    'keywords': ['stock', 'market', 'trading', 'investing', 'shares'],
                    'ticker': ['TSLA', 'NVDA', 'AAPL', 'MSFT', 'GOOG'],
                },
            },
        }
        self.data_manager = apps.get_app_config('scraper').DATA_MANAGER
        super().__init__(scraper_config)

    def load_config(self) -> None:
        """
        Ładuje konfigurację z bazy danych po pełnym załadowaniu aplikacji Django.
        """
        # For now 1 stands for default config
        try:
            config_obj = apps.get_app_config('scraper').get_model(
                'Config',
            ).objects.get(active=True)
            config_string = config_obj.config_string
            user_config = config_string['user_config']
            scrapers_config = config_string['scrapers_config'][0]
            print('scrapers_config', scrapers_config)
            self.config = {
                'crawl_interval': scrapers_config.get('crawl_interval', 60),
                'source': scrapers_config['source'],
                'credentials': scrapers_config['credentials'],
                'max_time_running': scrapers_config.get('max_time_running'),
                'threads': scrapers_config.get('threads', 1),
                'twitter_query': {
                    'start_date': scrapers_config['twitter_query']['start_date'],
                    'end_date': scrapers_config['twitter_query']['end_date'],
                    'params': {
                        'filter': scrapers_config['twitter_query']['params'].get('filter', []),
                        'lang': scrapers_config['twitter_query']['params'].get('lang', 'en'),
                        'keywords': scrapers_config['twitter_query']['params'].get('keywords', []),
                        'ticker': user_config['tickers'],
                    },
                },
            }
        except ObjectDoesNotExist:
            raise ValueError(
                f"Config with ID {self.config['config_id']} not found.",
            )
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")

    def _gen_dates_pipeline(self) -> queue.Queue:
        dates_pipeline: queue.Queue = queue.Queue()
        start = datetime.strptime(
            self.config['twitter_query']['start_date'], '%Y-%m-%d',
        )
        end = datetime.strptime(
            self.config['twitter_query']['end_date'], '%Y-%m-%d',
        )

        while start <= end:
            dates_pipeline.put(
                start.strftime('%Y-%m-%d'),
            )
            start -= timedelta(days=1)

        return dates_pipeline

    def get_scraper_config(self, config_id: int) -> dict:
        """
        Pobiera `config_string` dla podanego `config_id`.
        """
        try:
            Config = apps.get_model('scraper', 'Config')
            config_obj = Config.objects.get(pk=config_id)
            return config_obj.config_string
        except Config.DoesNotExist:
            raise ValueError(f"Config with ID {config_id} not found.")

    def _setup_instances(self) -> None:
        try:
            self._set_status(ScraperStates.SETTING_UP)
            chrome_options = webdriver.ChromeOptions()
            # chrome_options.add_argument("--headless")
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            # chrome_options.add_argument("--disable-usb-keyboard-detect")
            # chrome_options.add_argument("--disable-extensions")
            self.instance = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            self._log(LogTypes.ERROR, f"Failed to setup driver instance: {e}")
            raise

    def _enter_credentials(self, identifier: str, password: str) -> None:
        identifier_input = WebDriverWait(self.instance, 10).until(
            EC.presence_of_element_located((By.NAME, 'text')),
        )
        identifier_input.send_keys(identifier)
        identifier_input.send_keys(Keys.RETURN)
        password_input = WebDriverWait(self.instance, 10).until(
            EC.presence_of_element_located((By.NAME, 'password')),
        )
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

    def _generate_twitter_query(self, ticker: str, start_date: str | None = None, end_date: str | None = None) -> list[str]:
        if start_date and end_date:
            pass
        else:
            try:
                qp = self.config['twitter_query']['params']
                filters = ' '.join(
                    [f"-filter:{filter}" for filter in qp['filter']],
                )
                query = ticker
                query += f" lang:{qp['lang']} since:{self.config['twitter_query']['start_date']} until:{self.config['twitter_query']['end_date']} {filters}"
                query = ''.join(query)
            except Exception as e:
                self._log(LogTypes.ERROR, f'69 {e}')
            return [query]

    def _login_twitter(self) -> None:
        try:
            self.instance.get('https://x.com/login')
            self._enter_credentials(
                self.config['credentials']['email'],
                self.config['credentials']['password'],
            )
            self._wait_for_homepage()
            self._log(LogTypes.MESSAGE, 'Login successful.')
        except Exception as e:
            self._log(
                LogTypes.WARNING,
                f"Login failed with email. Retrying with username. ",
            )
            try:
                self._enter_credentials(
                    self.config['credentials']['login'],
                    self.config['credentials']['password'],
                )
                self._wait_for_homepage()
                self._log(LogTypes.MESSAGE, 'Login successful with username.')
            except Exception as e2:
                self._log(
                    LogTypes.ERROR,
                    f"Login failed with username as well: {e2}",
                )
                raise

    def _wait_for_homepage(self) -> None:
        try:
            WebDriverWait(self.instance, 10).until(
                lambda driver: driver.current_url == 'https://x.com/home',
            )
            self._log(LogTypes.MESSAGE, 'Homepage loaded successfully.')
        except Exception as e:
            self._log(LogTypes.ERROR, f"Homepage did not load: {e}")
            raise

    def _extract_tweet_metadata(self, tweet_html: str) -> dict:
        soup = BeautifulSoup(tweet_html, 'html.parser')

        def extract_number_from_button(data_testid):
            button = soup.find('button', {'data-testid': data_testid})
            if button:
                try:
                    return int(button.get_text(strip=True).replace('K', '000').replace('M', '000000'))
                except ValueError:
                    pass
            return None

        likes = extract_number_from_button('like')
        retweets = extract_number_from_button('retweet')
        replies = extract_number_from_button('reply')

        views_div = soup.find(
            'a', {'aria-label': lambda x: x and 'views' in x.lower()},
        )
        views = None
        if views_div:
            aria_label = views_div['aria-label']
            try:
                views = int(
                    ''.join(filter(str.isdigit, aria_label.split('views')[0])),
                )
            except ValueError:
                views = None

        return {'likes': likes, 'retweets': retweets, 'replies': replies, 'views': views}

    def _process_and_store(self, tweet_object):
        self.data_manager.eval_sentiment(tweet_object)
        pass

    def run_procedure(self, crawling_mode=True):
        # print("1 conf", self.config)
        # self.load_config()
        self._setup_instances()
        self._login_twitter()
        self._set_status(ScraperStates.RUNNING)

        last_task = None

        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(1)
                continue

            if crawling_mode and self.state == ScraperStates.RUNNING:
                time.sleep(self.config['crawl_interval'])

                tickers_list = self.config['twitter_query']['params']['ticker']

                if last_task and 'ticker' in last_task:
                    if last_task['ticker'] in tickers_list:
                        start_index = tickers_list.index(last_task['ticker'])
                        tickers_list = tickers_list[start_index:]

                for ticker in tickers_list:

                    last_task = {
                        'source': self.config['source'][0]['name'],
                        'ticker': ticker,
                        'count': 0,
                    }
                    self._update_task(last_task, overwrite=True)

                    if self.state != ScraperStates.RUNNING:

                        while self.state not in [ScraperStates.RUNNING, ScraperStates.STOPPED]:
                            time.sleep(1)

                        if last_task:
                            self._update_task(last_task, overwrite=True)
                    count = 0
                    query = self._generate_twitter_query(ticker=ticker)[0]
                    url = self.config['source'][0]['base_url'] + \
                        quote_plus(query)
                    self.instance.get(url)
                    WebDriverWait(self.instance, 10).until(
                        lambda d: d.execute_script(
                            'return document.readyState',
                        ) == 'complete',
                    )

                    last_height = self.instance.execute_script(
                        'return document.body.scrollHeight',
                    )

                    while True:
                        if self.state == ScraperStates.STOPPED:
                            break

                        self.instance.execute_script(
                            'window.scrollTo(0, document.body.scrollHeight);',
                        )
                        time.sleep(5)
                        new_height = self.instance.execute_script(
                            'return document.body.scrollHeight',
                        )

                        if new_height == last_height:
                            try:
                                latest_button = self.instance.find_element(
                                    By.XPATH, "//span[text()='Latest']",
                                )
                                latest_button.click()
                                time.sleep(2)
                            except Exception as e:
                                break

                        last_height = new_height
                        page_source = self.instance.page_source
                        soup = BeautifulSoup(page_source, 'html.parser')
                        tweets = soup.find_all(
                            'article', {'data-testid': 'tweet'},
                        )

                        for tweet in tweets:
                            try:
                                text = tweet.find('div', {'lang': 'en'}).get_text(
                                    strip=True,
                                ) if tweet.find('div', {'lang': 'en'}) else None
                                date = tweet.find('time')['datetime'] if tweet.find(
                                    'time',
                                ) else None

                                if not text or not date:
                                    print(
                                        '[WARNING] Skipping tweet due to missing text or date.',
                                    )
                                    continue

                                tweet_data = self._extract_tweet_metadata(
                                    str(tweet),
                                )

                                tweet_data['ticker'] = '$' + ticker
                                tweet_data['date'] = datetime.fromisoformat(
                                    date[:-1],
                                ).date()
                                tweet_data['likes'] = tweet_data['likes']
                                tweet_data['shares'] = tweet_data['retweets']
                                tweet_data['views'] = tweet_data['views']
                                tweet_data['comments'] = tweet_data['replies']
                                tweet_data['text'] = text
                                tweet_data['source_name'] = self.config['source'][0]['name']

                                enqueue_scraper_data(tweet_data)
                                count += 1
                                self._update_task({'count': count})
                            except KeyError as e:
                                print(
                                    f"[ERROR] Missing key while processing tweet: {e}",
                                )
                            except ValueError as e:
                                print(f"[ERROR] Value error encountered: {e}")
                            except Exception as e:
                                print(f"[ERROR] Unexpected error: {e}")

                    self._log(
                        LogTypes.MESSAGE,
                        f"Found {count} tweets $'{ticker}'",
                    )

                    if self.state != ScraperStates.RUNNING:
                        while self.state not in [ScraperStates.RUNNING, ScraperStates.STOPPED]:
                            time.sleep(1)
                        if self.state == ScraperStates.STOPPED:
                            break
                        if last_task:
                            self._update_task(last_task, overwrite=True)

            else:
                pass

        self.instance.quit()

    ## GETTERS ###

    def get_source(self):
        return self.config['source']
