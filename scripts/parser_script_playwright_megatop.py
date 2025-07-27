import os
import re
import time
import asyncio

from playwright.async_api import async_playwright, Page, Locator
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from asgiref.sync import sync_to_async

from parser.decorators import timeit

# Константы
TARGET_URL = "https://www.wildberries.by/"
SCROLL_PAUSE = 0.5
PAGE_LOAD_TIMEOUT = 0.5
EXCLUDED_CATEGORIES = ['бренды', 'wibes', 'экспресс', 'акции', 'грузовая доставка']


@timeit
def parse_products():
    # asyncio.run(_parse_products())
    result = get_categories()
    for cat in result:
        print(f"\n{cat['name']} ({len(cat['subcategories'])} подкатегорий):")
        for sub in cat['subcategories']:
            print(f"  - {sub['name']}: {sub['url'] or 'Нет ссылки'}")


async def setup_playwright(page: Page) -> None:
    await page.goto(TARGET_URL, timeout=50000)
    await page.wait_for_timeout(PAGE_LOAD_TIMEOUT * 1000)
    await page.wait_for_timeout(PAGE_LOAD_TIMEOUT * 1000)


def get_categories():
    with (sync_playwright() as p):
        # Запускаем браузер с дополнительными параметрами
        browser = p.chromium.launch(
            headless=False,
            timeout=60000,  # Увеличиваем таймаут запуска браузера
            slow_mo=100  # Добавляем задержку между действиями (мс)
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()

        try:
            # Увеличиваем таймаут навигации и отключаем ожидание полной загрузки
            page.goto(
                "https://www.wildberries.ru/",
                timeout=120000,  # 2 минуты на загрузку
                wait_until="domcontentloaded"  # Ждем только загрузки DOM, а не всех ресурсов
            )

            # Ожидаем появления кнопки меню
            page.wait_for_selector(
                'button.nav-element__burger.j-menu-burger-btn',
                state="visible",
                timeout=30000
            )
            time.sleep(5)  # Даем меню полностью раскрыться

            # Кликаем с обработкой возможных ошибок
            page.click('button.nav-element__burger.j-menu-burger-btn')

            # Ждем появления меню с категориями
            page.wait_for_selector(
                'ul.menu-burger__main-list a.menu-burger__main-list-link:has-text("Бренды")',
                state="visible",
                timeout=30000
            )

            # Получаем категории
            main_categories = page.query_selector_all('ul.menu-burger__main-list > li.menu-burger__main-list-item')

            result = []
            for category in main_categories:
                # Прокручиваем категорию в область видимости
                # category.scroll_into_view_if_needed()

                category_link = category.query_selector('a.menu-burger__main-list-link')

                if not category_link:
                    continue

                name_category = category_link.inner_text().strip()
                if name_category.lower() in EXCLUDED_CATEGORIES:
                    continue

                # Наводим курсор на категорию, чтобы открылись подкатегории
                category.hover()
                time.sleep(2)  # Ждем появления подкатегорий

                subcategories = []
                # Получаем подкатегории
                sub_items  = page.query_selector_all(
                    'div.menu-burger__first > ul.menu-burger__set > li.menu-burger__item')

                for items  in sub_items :
                    # Проверяем, является ли элемент ссылкой или заголовком
                    link = items.query_selector('a.menu-burger__link')
                    if link:
                        subcategory_name = link.inner_text().strip()
                        subcategory_url = link.get_attribute('href')
                        subcategories.append({'name': subcategory_name,
                                              'url': subcategory_url,
                                              'type': 'link'
                                              })
                    else:
                        title = items.query_selector('span.menu-burger__link')
                        if title:
                            subcategories.append({
                                'name': title.inner_text().strip(),
                                'url': None,
                                'type': 'title'
                            })

                result.append({
                    'name': category_link.inner_text().strip(),
                    'url': category_link.get_attribute('href'),
                    'data_menu_id': category.get_attribute('data-menu-id'),
                    'subcategories': subcategories
                })
            return result

        except PlaywrightTimeoutError as e:
            print(f"Timeout error occurred: {e}")
            # Можно сделать скриншот для диагностики
            # page.screenshot(path="error_screenshot.png")
            return None

        except Exception as e:
            print(f"Other error occurred: {e}")
            return None

        finally:
            # Всегда закрываем контекст и браузер
            context.close()
            browser.close()


async def _parse_products():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )

        page = await context.new_page()

        await setup_playwright(page)

        await browser.close()


if __name__ == "__main__":
    parse_products()
