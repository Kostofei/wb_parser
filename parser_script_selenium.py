import os
import django
import time
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

# Установите переменную окружения DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Настройте Django
django.setup()

from parser.models import Item


# Функция для прокрутки страницы и загрузки всех элементов
def scroll_and_load_all(driver, step=1700):
    last_height = driver.execute_script("return document.body.scrollHeight")
    print('прокutilsрутка')
    while True:
        # Прокручиваем на заданное количество пикселей
        driver.execute_script(f"window.scrollBy(0, {step});")

        # Ждем загрузки страницы
        time.sleep(3)

        # Получаем новую высоту страницы и сравниваем с последней высотой
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print('прокрутка все')
            break
        last_height = new_height
        print(f"Прокручено до {new_height} пикселей")


class PythonOrgSearch(unittest.TestCase):

    def setUp(self):
        # Настройка опций для Chrome в безголовом режиме
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Включение безголового режима

        # Укажите полный путь к chromedriver.exe
        service = Service(r'C:\PycharmProjects\test_task\wb_parser\chromedriver.exe')
        self.driver = webdriver.Chrome(service=service)

    def test_search_in_python_org(self):
        print(1)
        driver = self.driver
        driver.get("https://www.wildberries.by/")
        time.sleep(5)
        elem = driver.find_element(By.ID, "searchInput")

        # Ожидание загрузки страницы
        driver.implicitly_wait(20)
        print(2)

        elem.clear()
        elem.send_keys("женские трусы")
        # driver.find_element(By.ID, "applySearchBtn").click()
        elem.send_keys(Keys.RETURN)
        time.sleep(5)
        print(3)
        # Прокручиваем страницу до конца
        scroll_and_load_all(driver)
        print(4)
        items = driver.find_elements(By.CLASS_NAME, "product-card")
        # self.assertNotIn("No results found.", driver.page_source)
        # print(items)
        print(len(items))

        # Список для хранения информации о товарах
        products_info = []

        # Извлечение информации из каждой карточки
        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, "span.product-card__name").text
                price = item.find_element(By.CSS_SELECTOR, "del").text
                discounted_price = item.find_element(By.CSS_SELECTOR, "ins.price__lower-price").text
                rating = item.find_element(By.CSS_SELECTOR, "span.product-card__count").text

                products_info.append({
                    "title": title,
                    "price": price,
                    "discounted_price": discounted_price,
                    "rating": rating
                })
            except Exception as e:
                print(f"Ошибка при обработке карточки: {e}")
                continue

        # Вывод информации о товарах
        for idx, product in enumerate(products_info, start=1):
            item = Item(
                title=product["title"],
                price=product["price"],
                discounted_price=product["discounted_price"],
                rating=product["rating"],
            )
            item.save()
            print(f"Сохранен товар {idx}: {item.title}")

    def tearDown(self):
        self.driver.close()


if __name__ == "__main__":
    unittest.main()
