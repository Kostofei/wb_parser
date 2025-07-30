from colorama import Fore, Style, init
from playwright.sync_api import (sync_playwright, TimeoutError as PlaywrightTimeoutError,
                                 Page, Playwright, Browser, BrowserContext)

from parser.decorators import timeit

init()  # Инициализация (для Windows)

# Константы
TARGET_URL = "https://www.wildberries.by"
EXCLUDED_CATEGORIES = ['бренды', 'wibes', 'экспресс', 'акции', 'грузовая доставка']
TIME_WAIT = 1000


@timeit
def run_wb_parser():
    result = parse_all_categories()
    print(result)
    # print_categories(result)


def print_categories(categories, level=0):
    if not categories:
        return

    for cat in categories:
        # Отступ в зависимости от уровня вложенности
        indent = "  " * level
        # Печатаем информацию о категории
        # print(f"{indent}\n{cat['name']} ({len(cat['subcategories'])} подкатегорий): level{level}")
        print(f"{indent}\n{cat}: level{level}")

        # Если есть подкатегории, рекурсивно обрабатываем их

        if cat.get('subcategories', None):
            print_categories(cat['subcategories'], level + 2)


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
        # headless=True,
        headless=False,
        # args=[
        #     "--disable-blink-features=AutomationControlled",
        # "--no-sandbox",  # если запускаешь в Linux
        #     "--disable-dev-shm-usage",
        # ],
        timeout=60000,  # Увеличиваем таймаут запуска браузера
        slow_mo=0  # Добавляем задержку между действиями (мс)
    )

    # Создание контекста (окна браузера с настройками)
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        screen={"width": 1280, "height": 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )

    return browser, context


def route_handler(route, request):
    """Блокировка "лишних" ресурсов (ускорение загрузки)"""
    try:
        # blocked_types = ["image", "font", "stylesheet", "media", "other"]
        blocked_types = ["image", "font", "media"]
        if request.resource_type in blocked_types:
            route.abort()
        else:
            route.continue_()
    except Exception as e:
        print(f"Error in route handler for {request.url}: {str(e)}")
        route.continue_()  # В случае ошибки лучше пропустить запрос


@timeit
def load_main_categories(context: BrowserContext) -> list:
    # Открытие новой вкладки
    page = context.new_page()
    # page.route("**/*", route_handler)

    # Увеличиваем таймаут навигации и отключаем ожидание полной загрузки
    page.goto(
        f"{TARGET_URL}",
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
            'subcategories': []
        })
    page.close()
    return result


def load_subcategories(
        category: dict,
        context: BrowserContext,
        level: int = 1
) -> dict:
    print(f'{level * "-"} {category["name"]}')
    result = []
    page = context.new_page()
    try:
        # page.route("**/*", route_handler)

        page.goto(
            f"{TARGET_URL}{category['url']}",
            timeout=120000,  # 2 минуты на загрузку
            wait_until="domcontentloaded"  # Ждем только загрузки DOM, а не всех ресурсов
        )
        page.wait_for_timeout(TIME_WAIT)
        try:
            try:
                # Ждем появления меню с категориями subcategory-item
                page.wait_for_selector(selector='ul.menu-category__subcategory',
                                       state="visible",
                                       timeout=TIME_WAIT)
                # Получаем все элементы меню (включая заголовки)
                menu_items = page.query_selector_all('li.menu-category__subcategory-item')

                for menu_item in menu_items:
                    # Извлекаем ссылки
                    link = menu_item.query_selector('a.menu-category__subcategory-link')
                    if link:
                        result.append({
                            'name': link.inner_text().strip(),
                            'url': link.get_attribute('href'),
                            'parent': category['name'],
                        })
            except:
                # Ждем появления меню с категориями menu-category__list
                page.wait_for_selector(selector='ul.menu-category__list',
                                       state="visible",
                                       timeout=TIME_WAIT)
                # Получаем все элементы меню (включая заголовки)
                menu_items = page.query_selector_all('li.menu-category__item')

                for menu_item in menu_items:
                    # Пропускаем заголовки (элементы с тегом <p>)
                    if menu_item.query_selector('p.menu-category__item'):
                        continue

                    # Извлекаем ссылки
                    link = menu_item.query_selector('a.menu-category__link')
                    if link:
                        result.append({
                            'name': link.inner_text().strip(),
                            'url': link.get_attribute('href'),
                            'parent': category['name'],
                        })
            print(f"{Fore.RED} {[i['name'] for i in result]} {Style.RESET_ALL}")
            category['subcategories'] = []
            for item in result:
                print(f'идем по списку {item["name"]} - {level}')
                category['subcategories'].append(load_subcategories(item, context, level + 1))

        except:
            page.wait_for_timeout(TIME_WAIT)
            # Получаем все элементы "Категория"
            show_all_filter = page.locator("div.dropdown-filter:has-text('Категория')")
            if show_all_filter.count() >= 2:
                show_all_filter.nth(1).hover()

                show_all_buttons = page.locator("button.filter__show-all:has-text('Показать все')")
                if show_all_buttons.count() >= 2:
                    show_all_buttons.nth(1).click()

                count_items = 0
                while True:
                    page.wait_for_timeout(TIME_WAIT)
                    all_items = page.query_selector_all('li.filter__item')
                    all_items[-1].hover()
                    if count_items == len(all_items):
                        break
                    count_items = len(all_items)

                for i in all_items:
                    # Извлекаем ссылки
                    link = i.query_selector('span.checkbox-with-text__text')
                    parent_classes = i.evaluate("e => e.closest('.measurementContainer--GRwov') === null")
                    if link and parent_classes:
                        result.append(link.inner_text().strip())

                print(f'{level * "-" + "-"} Категорий {len(result)}, [Родитель: {category["name"]}], {level}')
                category['Категория'] = result
            else:
                page.wait_for_selector('button.dropdown-filter__btn--burger > div.dropdown-filter__btn-name').hover()
                page.wait_for_timeout(TIME_WAIT)
                all_items = page.query_selector_all('ul.filter-category__list > li.filter-category__item')
                for item in all_items:
                    # Извлекаем ссылки
                    link = item.query_selector('a.filter-category__link')
                    page.wait_for_timeout(TIME_WAIT)
                    if link:
                        result.append({
                            'name': link.inner_text().strip(),
                            'url': link.get_attribute('href'),
                            'parent': category['name'],
                        })

                if category['name'] not in [item['name'] for item in result]:
                    print(f"{Fore.RED} {[i['name'] for i in result]} {Style.RESET_ALL}")
                    category['subcategories'] = []
                    for item in result:
                        print(f'идем по списку {item["name"]} - {level}')
                        category['subcategories'].append(load_subcategories(item, context, level + 1))
                else:
                    print(f'{Fore.GREEN} {level * "-" + "-"} Категорий НЕТ!, [Родитель: {category["name"]}], {level} {Style.RESET_ALL}')
                    category['Категория'] = f'Категорий нет {level}'

    except Exception as e:
        print(f"Error processing {category['name']}: {str(e)}")
    finally:
        page.close()

    return category


def parse_all_categories() -> list | None:
    with (sync_playwright() as p):
        browser, context = create_browser_session(p)

        result = []
        try:
            print('Получаю категории')
            main_categories = load_main_categories(context)
            print('Получаю подкатегории 0')
            for category in main_categories[13:14]:
                result.append(load_subcategories(category, context))

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


if __name__ == "__main__":
    run_wb_parser()
