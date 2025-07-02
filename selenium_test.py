from selenium import webdriver

# Шаг 1: запускаем браузер
driver = webdriver.Chrome()

# Шаг 2: открываем сайт с цитатами
driver.get("https://quotes.toscrape.com/js/")

# Проверка на то что в title есть слово Python
# assert "Python" in driver.title, 'нет в title слова Python'

# try:
#     if "Python" not in driver.title:
#         raise Exception("Жопа")
# except Exception as e:
#     print(e)


# Шаг 3: ищем все элементы с классом 'text' — это сами цитаты
quotes = driver.find_elements("class name", "text")

# Шаг 4: выводим текст каждой цитаты
for quote in quotes:
    print(quote.text)

# Шаг 5: закрываем браузер
driver.quit()