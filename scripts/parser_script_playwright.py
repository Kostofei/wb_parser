import os
import re
import asyncio
import django

from playwright.async_api import async_playwright, Page
from playwright.async_api import Locator
from asgiref.sync import sync_to_async

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from parser.models import Item
from parser.decorators import timeit

# Константы
TARGET_URL = "https://www.wildberries.by/"
search_query = "молды"
items_to_parse = 6500

SCROLL_PAUSE = 0.5
PAGE_LOAD_TIMEOUT = 0.5
MAX_ELEMENTS = 100

async def setup_and_search(page: Page) -> None:
    await page.goto(TARGET_URL, timeout=5000)
    # await page.screenshot(path="screenshot.png", full_page=True)
    await page.wait_for_timeout(PAGE_LOAD_TIMEOUT * 1000)

    search_input = await page.wait_for_selector("input[type='search']")
    await search_input.fill(search_query)
    await search_input.press("Enter")

    await page.wait_for_timeout(PAGE_LOAD_TIMEOUT * 1000)


async def scroll_page(page: Page) -> None:
    """
    Прокручивает страницу, пока не будут загружены все элементы или не прекратится рост их количества.
    """
    print("Прокрутка страницы для загрузки контента...")

    count = 0
    found_elements_count = 0

    while count != MAX_ELEMENTS:
        # Получаем текущее количество элементов на странице
        await page.wait_for_selector("article.j-card-item", timeout=10000)
        elements = await page.query_selector_all("article.j-card-item")
        current_count = len(elements)

        # Если количество элементов не изменилось — останавливаемся
        if found_elements_count == current_count:
            print(f"На странице всего {current_count} объектов. Прокрутка завершена.")
            break

        print(f"Шаг {count + 1}: найдено {current_count} объектов")

        # Прокручиваем к последнему элементу
        if elements:
            await elements[-1].scroll_into_view_if_needed()

        # Проверка на достижение максимума
        if current_count >= MAX_ELEMENTS:
            print(f"Достигнуто необходимое количество объектов ({MAX_ELEMENTS}).")
            break

        await asyncio.sleep(SCROLL_PAUSE)

        found_elements_count = current_count
        count += 1


async def go_to_next_page(page: Page) -> bool:
    try:
        next_button = await page.query_selector("a:has-text('Следующая страница')")
        if next_button:
            await next_button.click()
            print("Перешли на следующую страницу")
            await page.wait_for_timeout(PAGE_LOAD_TIMEOUT * 1000)
            return True
        return False
    except Exception as e:
        print(f"Не удалось перейти на следующую страницу: {e}")
        return False


async def parse_number_from_text(text: str) -> int | float | None:
    if not isinstance(text, str):
        return 0
    text = text.replace(" ", "")
    match = re.search(r'(\d+[.,]?\d*)', text)
    if match:
        number_str = match.group(1).replace(',', '.')
        number = float(number_str)
        return int(number) if number.is_integer() else number
    return None


async def parse_product_card(card: Locator) -> dict | None:
    """
    Оптимизированный асинхронный парсинг карточки товара с использованием регулярных выражений.
    """
    try:
        # Получаем весь HTML карточки единожды
        html = await card.evaluate("element => element.outerHTML")

        title_match = re.search(
            r'<span class="product-card__name-separator.*?"> / </span>(.*?)</span>', html
        )
        price_match = re.search(
            r'<ins class="price__lower-price.*?">.*?(\d+[.,]?\d*).*?</ins>', html
        )
        discounted_match = re.search(
            r'<del>.*?(\d+[.,]?\d*).*?</del>', html
        )
        rating_match = re.search(
            r'<span class="address-rate-mini address-rate-mini--sm">(.*?)</span>', html
        )
        reviews_match = re.search(
            r'<span class="product-card__count">.*?(\d+).*?</span>', html
        )

        currency = "BYN"  # Можно подставить динамически, если надо

        return {
            "title": title_match.group(1) if title_match else "Неизвестно",
            "price": await parse_number_from_text(price_match.group(1)) if price_match else None,
            "discounted_price": await parse_number_from_text(discounted_match.group(1)) if discounted_match else None,
            "rating": await parse_number_from_text(rating_match.group(1)) if rating_match else None,
            "reviews_count": await parse_number_from_text(reviews_match.group(1)) if reviews_match else 0,
            "currency": currency,
        }

    except Exception as e:
        print(f"Ошибка в карточке товара: {e}")
        return None


@sync_to_async
def save_item(data: list):
    items_to_create = [Item(**product) for product in data]
    Item.objects.bulk_create(items_to_create)


@timeit
def parse_products():
    asyncio.run(_parse_products())


async def _parse_products():
    from playwright.async_api import async_playwright

    products_info = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )

        page = await context.new_page()

        await setup_and_search(page)

        while True:
            await scroll_page(page)

            items = await page.locator("article.j-card-item").all()

            for card in items:
                data = await parse_product_card(card)
                if data and data["title"] and data["price"]:
                    products_info.append(data)

            print(f"Товаров собрано: {len(products_info)}")

            if len(products_info) >= items_to_parse:
                break
            if not await go_to_next_page(page):
                break

        print(f"Всего товаров для сохранения в БД: {len(products_info[:items_to_parse])}")

        # Создаем список объектов Item и сохраняем их в БД за одну транзакцию
        await save_item(products_info[:items_to_parse])

        await browser.close()


if __name__ == "__main__":
    parse_products()
