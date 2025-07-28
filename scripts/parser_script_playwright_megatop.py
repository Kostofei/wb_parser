import os
import re
import time
import asyncio

from playwright.async_api import async_playwright, Page, Locator
from playwright.sync_api import (sync_playwright, TimeoutError as PlaywrightTimeoutError,
                                 Page, Playwright, Browser, BrowserContext,
                                 ElementHandle)
from asgiref.sync import sync_to_async

from parser.decorators import timeit

# Константы
TARGET_URL = "https://www.wildberries.by/"
EXCLUDED_CATEGORIES = ['бренды', 'wibes', 'экспресс', 'акции', 'грузовая доставка']


@timeit
def run_wb_parser():
    result = parse_all_categories()
    if result:
        for cat in result:
            print(f"\n{cat['name']} - {cat['url']}")
            # print(f"\n{cat['name']} ({len(cat['subcategories'])} подкатегорий):")
            # for sub in cat['subcategories']:
            #     print(f"  - {sub['name']}: {sub['url'] or 'Нет ссылки'}")


def create_browser_session(p: Playwright) -> tuple[Browser, BrowserContext]:
    """
    Настраивает и возвращает экземпляр браузера, контекст и страницу Playwright.

    Args:
        p (Playwright): Экземпляр Playwright.

    Returns:
        tuple[Browser, BrowserContext, Page]: Экземпляр браузера, контекст и страница.
    """
    # Запускаем браузер с дополнительными параметрами
    browser = p.chromium.launch(
        headless=True,
        timeout=60000,  # Увеличиваем таймаут запуска браузера
        slow_mo=0  # Добавляем задержку между действиями (мс)
    )

    # Создание контекста (окна браузера с настройками)
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )

    return browser, context


def route_handler(route, request):
        """Блокировка "лишних" ресурсов (ускорение загрузки)"""
        if request.resource_type in ["image", "font", "stylesheet", "media"]:
            route.abort()
        else:
            route.continue_()


def load_main_categories(context: BrowserContext) -> list:
    # Открытие новой вкладки
    page = context.new_page()
    page.route("**/*", route_handler)

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

        result.append({
            'name': category_link.inner_text().strip(),
            'url': category_link.get_attribute('href'),
            'data_menu_id': category.get_attribute('data-menu-id'),
            'subcategories': ''
        })
    page.close()
    return result


def load_sub_items(category: list[dict], context: BrowserContext) -> list:
    # Наводим курсор на категорию, чтобы открылись подкатегории
    # category.hover()
    # time.sleep(2)  # Ждем появления подкатегорий

    subcategories = []
    # Получаем подкатегории
    sub_items = page.query_selector_all(
        'div.menu-burger__first > ul.menu-burger__set > li.menu-burger__item')

    for items in sub_items:
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
    return subcategories


def parse_all_categories() -> list | None:
    with (sync_playwright() as p):
        browser, context = create_browser_session(p)

        try:
            main_categories = load_main_categories(context)
            # result = load_sub_items(main_categories, context)

            return main_categories

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


if __name__ == "__main__":
    run_wb_parser()