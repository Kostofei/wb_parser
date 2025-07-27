import os
import re
import time
import django
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement

from parser.decorators import timeit

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from parser.models import Item

# Переменные
search_query = "молды"  # Поисковый запрос на сайте
items_to_parse = 10000  # Общее количество товаров, которые нужно распарсить

# Константы
CHROMEDRIVER_PATH = r'../chromedriver.exe'  # Необходимо указать путь
TARGET_URL = "https://www.wildberries.by/"
SCROLL_PAUSE = 0.5  # Задержка (в секундах) после каждой прокрутки, чтобы успели подгрузиться элементы
PAGE_LOAD_TIMEOUT = 0.5  # Время ожидания загрузки страницы после действий (например, после поиска)
IMPLICIT_WAIT = 2  # Неявное ожидание элементов при поиске через Selenium


def setup_driver() -> WebDriver:
    """
    Создаёт и возвращает объект Selenium WebDriver.
    """
    options = Options()

    # headless-режим
    options.add_argument("--headless=new")

    # Отключаем признак, что это автоматизация (navigator.webdriver = false)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Устанавливаем размер окна браузера — важно, потому что по умолчанию в headless режиме окно маленькое
    options.add_argument("--window-size=1920,1080")

    # Стартуем браузер сразу в полноэкранном режиме (может влиять на рендеринг некоторых элементов)
    options.add_argument("--start-maximized")

    # Отключаем использование GPU (не нужно в headless-режиме и иногда вызывает баги в Linux)
    options.add_argument("--disable-gpu")

    # Отключаем sandbox (изолированное окружение), нужно в некоторых окружениях без root-доступа (например, Docker)
    options.add_argument("--no-sandbox")

    # Отключаем shared memory, чтобы избежать ошибок в ограниченных системах (например, low-RAM или Docker)
    options.add_argument("--disable-dev-shm-usage")

    # Устанавливаем реальный user-agent, как у обычного Chrome-пользователя на Windows
    # Это позволяет избежать банов и специальных версток для ботов
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/115.0.0.0 Safari/537.36")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)  # отключаем визуал
    # driver = webdriver.Chrome(service=service)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver


def setup_and_search(driver: WebDriver) -> None:
    """
    Открывает сайт и выполняет поиск по ключевому слову.
    """
    driver.get(TARGET_URL)
    time.sleep(PAGE_LOAD_TIMEOUT)

    search_input = driver.find_element(By.ID, "searchInput")
    search_input.clear()
    search_input.send_keys(search_query)
    search_input.send_keys(Keys.RETURN)
    time.sleep(PAGE_LOAD_TIMEOUT)


def scroll_page(driver: WebDriver) -> None:
    """
    Прокручивает страницу до тех пор, пока не будет получены все объекты на странице.
    """
    count = 0
    max_elements_page = 100
    found_elements_page = 0
    print(f"Прокрутка страницы для загрузки контента...")

    while count != max_elements_page:
        # Получаем текущее количество элементов
        elements = driver.find_elements(By.CSS_SELECTOR, "article.j-card-item")
        current_count = len(elements)

        # Если количество объектов не изменилось, выходим из цикла
        if found_elements_page == current_count:
            print(f"На странице всего {current_count} объектов.")
            break

        print(f"Шаг {count + 1}: найдено {current_count} объектов")

        # Прокручиваем к последнему элементу
        if elements:
            driver.execute_script("arguments[0].scrollIntoView();", elements[-1])

        if current_count >= 100:
            print(f"Достигнуто необходимое количество объектов {max_elements_page}.")
            break

        time.sleep(0.5)

        found_elements_page = current_count
        count += 1


def go_to_next_page(driver: WebDriver) -> bool:
    """
    Переходит на следующую страницу. Возвращает True, если получилось.
    """
    try:
        next_button = driver.find_element(By.PARTIAL_LINK_TEXT, 'Следующая страница')
        next_button.click()
        print("Перешли на следующую страницу")
        return True
    except Exception as e:
        print(f"Не удалось перейти на следующую страницу: {e}")
        return False


def parse_product_card(item: WebElement) -> dict[str, object] | None:
    """
    Оптимизированная версия парсера карточки товара.
    """
    try:
        # Получаем весь HTML элемента один раз
        html = item.get_attribute('outerHTML')

        title = re.search(r'<span class="product-card__name-separator.*?"> / </span>(.*?)</span>', html)
        price = re.search(r'<ins class="price__lower-price.*?">.*?(\d+[.,]?\d*).*?</ins>', html)
        discounted_price = re.search(r'<del>.*?(\d+[.,]?\d*).*?</del>', html)
        rating = re.search(r'<span class="address-rate-mini address-rate-mini--sm">(.*?)</span>', html)
        reviews_count = re.search(r'<span class="product-card__count">.*?(\d+).*?</span>', html)

        # если надо получаем валюту
        # currency = item.find_element(
        #         #     By.XPATH,
        #         #     "/html/body/div[1]/header/div/div[1]/div/div[2]/span/span[2]"
        #         # ).text

        currency = 'BYN'

        return {
            "title": title.group(1),
            "price": parse_number_from_text(price.group(1)),
            "discounted_price": parse_number_from_text(discounted_price.group(1)) if discounted_price else None,
            "rating": parse_number_from_text(rating.group(1)) if rating else None,
            "reviews_count": parse_number_from_text(reviews_count.group(1)) if reviews_count else 0,
            "currency": currency,
        }

    except Exception as e:
        print(f"Ошибка в карточке товара: {e}")
        return None


def parse_number_from_text(text: str) -> int | float | None:
    """
    Извлекает число из строки. Возвращает int, float или None.
    """
    if not isinstance(text, str):
        return 0

    text = text.replace(" ", "")
    match = re.search(r'(\d+[.,]?\d*)', text)

    if match:
        number_str = match.group(1).replace(',', '.')  # Заменяем запятую на точку
        number = float(number_str)  # Преобразуем в float
        number = int(number) if number.is_integer() else number
        return number

    return None


@timeit
def parse_products() -> None:
    """
    Запускает парсинг товаров: ищет, собирает данные и сохраняет в БД.
    """
    driver = setup_driver()
    products_info = []

    try:
        setup_and_search(driver)

        while True:
            time.sleep(PAGE_LOAD_TIMEOUT)
            scroll_page(driver)
            items = driver.find_elements(By.CSS_SELECTOR, "article.j-card-item")

            for item in items:
                product_data = parse_product_card(item)
                if product_data and product_data["title"] and product_data["price"]:
                    products_info.append(product_data)

            print(f"Товаров собрано: {len(products_info)}")

            if len(products_info) >= items_to_parse or len(items) < 100:
                break
            else:
                if not go_to_next_page(driver):
                    break

        print(f"Всего товаров для сохранения в БД: {len(products_info[:items_to_parse])} (лимит: {items_to_parse})")

        # Создаем список объектов Item и сохраняем их в БД за одну транзакцию
        items_to_create = [Item(**product) for product in products_info[:items_to_parse]]
        Item.objects.bulk_create(items_to_create)

    finally:
        driver.quit()


if __name__ == "__main__":
    parse_products()
