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

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from parser.models import Item

# Переменные
SEARCH_QUERY = "трусы"  # Поисковый запрос на сайте
ITEMS_TO_PARSE = 250  # Общее количество товаров, которые нужно распарсить

# Константы
CHROMEDRIVER_PATH = r'./chromedriver.exe'  # Необходимо указать путь
TARGET_URL = "https://www.wildberries.by/"
ITEMS_PER_PAGE = 100  # Ожидаемое количество товаров на одной странице
SCROLL_STEP = 1700  # Количество пикселей на шаг прокрутки страницы
SCROLL_PAUSE = 3  # Задержка (в секундах) после каждой прокрутки, чтобы успели подгрузиться элементы
PAGE_LOAD_TIMEOUT = 5  # Время ожидания загрузки страницы после действий (например, после поиска)
IMPLICIT_WAIT = 20  # Неявное ожидание элементов при поиске через Selenium


def setup_driver() -> WebDriver:
    """
    Создаёт и возвращает объект Selenium WebDriver.
    """
    options = Options()
    options.add_argument("--headless")
    service = Service(CHROMEDRIVER_PATH)
    # driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome(service=service)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver


def scroll_and_load_all(driver: WebDriver, step: int = SCROLL_STEP) -> None:
    """
    Прокручивает страницу вниз до конца, чтобы подгрузить все товары.
    """
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


def parse_number_from_text(text: str) -> int | float | None:
    """
    Извлекает число из строки. Возвращает int, float или None.
    """
    if not isinstance(text, str):
        return 0

    text = text.replace(" ", "")
    match = re.search(r'(\d+)', text)

    if match:
        number_str = match.group(1).replace(',', '.')  # Заменяем запятую на точку
        number = float(number_str)  # Преобразуем в float
        return int(number) if number.is_integer() else number

    return None


def setup_and_search(driver: WebDriver) -> None:
    """
    Открывает сайт и выполняет поиск по ключевому слову.
    """
    driver.get(TARGET_URL)
    time.sleep(PAGE_LOAD_TIMEOUT)

    search_input = driver.find_element(By.ID, "searchInput")
    search_input.clear()
    search_input.send_keys(SEARCH_QUERY)
    search_input.send_keys(Keys.RETURN)
    time.sleep(PAGE_LOAD_TIMEOUT)


def parse_product_card(item: WebElement) -> dict[str, object] | None:
    """
    Достаёт данные из карточки товара.
    Возвращает словарь или None, если парсинг не удался.
    """
    try:
        title = item.find_element(By.CSS_SELECTOR, "span.product-card__name").text
        price = item.find_element(By.CSS_SELECTOR, "del").text
        discounted_price = item.find_element(By.CSS_SELECTOR, "ins.price__lower-price").text
        rating = item.find_element(By.CSS_SELECTOR, "span.address-rate-mini").text
        rating_count = item.find_element(By.CSS_SELECTOR, "span.product-card__count").text
        currency = item.find_element(
            By.XPATH,
            "/html/body/div[1]/header/div/div[1]/div/div[2]/span/span[2]"
        ).text

        title = title[2:] if title.startswith('/ ') else title

        return {
            "title": title,
            "price": parse_number_from_text(price),
            "discounted_price": parse_number_from_text(discounted_price),
            "rating": parse_number_from_text(rating),
            "reviews_count": parse_number_from_text(rating_count) or 0,
            "currency": currency,
        }

    except Exception as e:
        print(f"Ошибка в карточке товара: {e}")
        return None


def go_to_next_page(driver: WebDriver) -> bool:
    """
    Переходит на следующую страницу. Возвращает True, если получилось.
    """
    try:
        next_button = driver.find_element(By.XPATH, '//*[@id="catalog"]/div/div[5]/div/a[7]')
        next_button.click()
        print("Перешли на следующую страницу")
        return True
    except Exception as e:
        print(f"Не удалось перейти на следующую страницу: {e}")
        return False


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
            scroll_and_load_all(driver)
            items = driver.find_elements(By.CLASS_NAME, "j-card-item")

            for item in items:
                product_data = parse_product_card(item)
                if product_data and product_data["title"] and product_data["price"]:
                    products_info.append(product_data)

            print(f"Товаров собрано: {len(products_info)}")

            if len(products_info) <= ITEMS_TO_PARSE:
                if not go_to_next_page(driver):
                    break
            else:
                break

        print(f"Всего товаров для сохранения в БД: {len(products_info[:ITEMS_TO_PARSE])} (лимит: {ITEMS_TO_PARSE})")

        for idx, product in enumerate(products_info[:ITEMS_TO_PARSE], 1):
            item = Item(**product)
            item.save()
            print(f"[{idx}] Сохранено: {item.title}")

    finally:
        driver.quit()


if __name__ == "__main__":
    parse_products()
