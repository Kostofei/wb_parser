import time
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

# Функция для прокрутки страницы и загрузки всех элементов
def scroll_and_load_all(driver, step=1700):
    last_height = driver.execute_script("return document.body.scrollHeight")
    # last_count = 0

    while True:
        # Прокручиваем до конца страницы
        driver.execute_script(f"window.scrollBy(0, {step});")

        # Ждем загрузки страницы
        time.sleep(3)

        # Получаем новое количество элементов
        # new_count = len(driver.find_elements(By.CSS_SELECTOR, "article.product-card"))

        # Если количество элементов не изменилось, выходим из цикла
        # if new_count == last_count:
        #     break

        # last_count = new_count

        # Получаем новую высоту страницы и сравниваем с последней высотой
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

class PythonOrgSearch(unittest.TestCase):

    def setUp(self):
        # Настраиваем опции Chrome
        options = Options()
        options.add_argument("--headless")  # Включение headless-режима
        options.add_argument("--disable-gpu")  # Рекомендуется для Windows

        # Укажите полный путь к chromedriver.exe
        service = Service(r'C:\PycharmProjects\test_task\wb_parser\chromedriver.exe')
        self.driver = webdriver.Chrome(service=service)


    def test_search_in_python_org(self):

        driver = self.driver
        driver.get("https://www.wildberries.by/")
        time.sleep(5)
        elem = driver.find_element(By.ID, "searchInput")
        # Ожидание загрузки страницы
        driver.implicitly_wait(20)

        elem.clear()
        elem.send_keys("женские трусы")
        # driver.find_element(By.ID, "applySearchBtn").click()
        elem.send_keys(Keys.RETURN)
        time.sleep(5)

        # Прокручиваем страницу до конца
        scroll_and_load_all(driver)

        items = driver.find_elements(By.CLASS_NAME, "product-card")
        # self.assertNotIn("No results found.", driver.page_source)
        # print(items)
        print(len(items))


    def tearDown(self):
        self.driver.close()

if __name__ == "__main__":
    unittest.main()