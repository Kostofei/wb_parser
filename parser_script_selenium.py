import os
import re
import time
import django
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from parser.models import Item

# Константы
CHROMEDRIVER_PATH = r'./chromedriver.exe'  # Необходимо указать путь
TARGET_URL = "https://www.wildberries.by/"
ITEMS_PER_PAGE = 100  # Ожидаемое количество товаров на одной странице
SCROLL_STEP = 1700  # Количество пикселей на шаг прокрутки страницы
SCROLL_PAUSE = 3  # Задержка (в секундах) после каждой прокрутки, чтобы успели подгрузиться элементы
PAGE_LOAD_TIMEOUT = 5  # Время ожидания загрузки страницы после действий (например, после поиска)
IMPLICIT_WAIT = 20  # Неявное ожидание элементов при поиске через Selenium

# Переменные
SEARCH_QUERY = "ноутбук"  # Поисковый запрос на сайте
ITEMS_TO_PARSE = 1000  # Общее количество товаров, которые нужно распарсить


def scroll_and_load_all(driver, step=SCROLL_STEP):
    """Плавная прокрутка страницы до конца"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    print("Начинаем прокрутку")

    while True:
        driver.execute_script(f"window.scrollBy(0, {step});")
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Прокрутка завершена")
            break
        last_height = new_height
        print(f"Прокручено до: {new_height} пикселей")


def setup_driver():
    """Настройка и возврат экземпляра драйвера"""
    options = Options()
    options.add_argument("--headless")
    service = Service(CHROMEDRIVER_PATH)
    # driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome(service=service)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver


def parse_number_from_text(text):
    if not isinstance(text, str):
        return 0
    text = text.replace(" ", "")
    match = re.search(r'(\d+)', text)
    if match:
        number_str = match.group(1).replace(',', '.')  # Заменяем запятую на точку
        number = float(number_str)  # Преобразуем в float
        if number.is_integer():  # Проверяем, целое ли число
            number = int(number)
    else:
        number = None
    return number


def parse_products():
    driver = setup_driver()
    try:
        driver.get(TARGET_URL)
        time.sleep(PAGE_LOAD_TIMEOUT)

        search_input = driver.find_element(By.ID, "searchInput")
        search_input.clear()
        search_input.send_keys(SEARCH_QUERY)
        search_input.send_keys(Keys.RETURN)
        time.sleep(PAGE_LOAD_TIMEOUT)

        products_info = []

        for page in range(ITEMS_TO_PARSE // ITEMS_PER_PAGE):
            time.sleep(PAGE_LOAD_TIMEOUT)
            scroll_and_load_all(driver)
            items = driver.find_elements(By.CLASS_NAME, "j-card-item")

            for idx, item in enumerate(items):
                try:
                    title = item.find_element(By.CSS_SELECTOR, "span.product-card__name").text
                    price = item.find_element(By.CSS_SELECTOR, "del").text
                    discounted_price = item.find_element(By.CSS_SELECTOR, "ins.price__lower-price").text
                    rating = item.find_element(By.CSS_SELECTOR, "span.address-rate-mini").text
                    rating_count = item.find_element(By.CSS_SELECTOR, "span.product-card__count").text
                    currency = item.find_element(By.XPATH,
                                                 "/html/body/div[1]/header/div/div[1]/div/div[2]/span/span[2]").text

                    title = title[2:] if title.startswith('/ ') else title
                    price = parse_number_from_text(price)
                    discounted_price = parse_number_from_text(discounted_price)
                    rating = parse_number_from_text(rating)
                    rating_count = parse_number_from_text(rating_count)

                    if title and price:
                        products_info.append({
                            "title": title,
                            "price": price,
                            "discounted_price": discounted_price,
                            "rating": rating,
                            "rating_count": rating_count if rating_count else 0,
                            "currency": currency,
                        })
                except Exception as e:
                    print(f"Ошибка в карточке #{idx}: {e}")
                    continue

            if page != (ITEMS_TO_PARSE // ITEMS_PER_PAGE) - 1:
                try:
                    next_button = driver.find_element(By.XPATH, '//*[@id="catalog"]/div/div[5]/div/a[7]')
                    next_button.click()
                    print("Перешли на следующую страницу")
                except Exception as e:
                    print(f"Ошибка при переходе на следующую страницу: {e}")
                    break

        print(f"Всего товаров собрано: {len(products_info)}")

        for idx, product in enumerate(products_info, 1):
            item = Item(**product)
            item.save()
            print(f"[{idx}] Сохранено: {item.title}")

    finally:
        driver.quit()


if __name__ == "__main__":
    parse_products()
