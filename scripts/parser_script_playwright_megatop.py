from typing import Any, Union
from openpyxl.styles import Alignment
import pandas as pd
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
    process_categories_to_excel(result)


def process_categories_to_excel(
        initial_data: list[dict],
        output_filename: str = "categories.xlsx",
        exclude_root_in_path: bool = True
) -> None:
    """
    Обрабатывает категории и сохраняет их в Excel файл с уровнями вложенности

    Args:
        initial_data: Исходные данные категорий (список словарей)
        output_filename: Имя выходного файла Excel
        exclude_root_in_path: Исключать ли корневой элемент из пути
    """

    def _get_categories_with_levels(
            item: dict[str, Any],
            current_level: int = 0,
            parent_path: list[str] | None = None
    ) -> list[dict[str, Union[str, int]]]:
        """Рекурсивно извлекает категории с уровнями вложенности"""
        categories: list[dict[str, Union[str, int]]] = []
        current_path = parent_path if parent_path is not None else []

        # Формируем путь (исключаем корневой уровень если требуется)
        if not exclude_root_in_path or current_level > 0:
            current_path = current_path + [item['name']]

        # Обрабатываем категории текущего элемента
        if 'Категория' in item:
            item_categories = item['Категория']
            if isinstance(item_categories, list):
                for category in item_categories:
                    categories.append({
                        'Категория': category,
                        'Уровень': current_level,
                        'Путь': ' → '.join(current_path) if current_path else "Основной раздел"
                    })
            else:
                categories.append({
                    'Категория': item_categories,
                    'Уровень': current_level,
                    'Путь': ' → '.join(current_path) if current_path else "Основной раздел"
                })

        # Рекурсивно обрабатываем подкатегории
        if 'subcategories' in item:
            for sub in item['subcategories']:
                categories.extend(_get_categories_with_levels(
                    sub,
                    current_level + 1,
                    current_path.copy()
                ))

        return categories

    # Создаем Excel-файл
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        for section in initial_data:
            section_name = section['name']
            all_categories: list[dict[str, Union[str, int]]] = []

            if 'subcategories' in section:
                for subcategory in section['subcategories']:
                    all_categories.extend(_get_categories_with_levels(
                        subcategory,
                        current_level=1,
                        parent_path=[]
                    ))

            # Создаем DataFrame
            df = pd.DataFrame(all_categories)
            if not df.empty:
                df = df[['Категория', 'Уровень', 'Путь']]
                df.to_excel(writer, sheet_name=section_name, index=False)

                # Форматирование листа
                worksheet = writer.sheets[section_name]

                # Центрирование столбца с уровнями
                for row in worksheet.iter_rows(min_row=2, min_col=2, max_col=2):
                    for cell in row:
                        cell.alignment = Alignment(horizontal='center', vertical='center')

                # Центрирование заголовка
                worksheet['B1'].alignment = Alignment(horizontal='center', vertical='center')

                # Настройка ширины столбцов
                worksheet.column_dimensions['A'].width = 30  # Категория
                worksheet.column_dimensions['B'].width = 10  # Уровень
                worksheet.column_dimensions['C'].width = 50  # Путь


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
        blocked_types = ["image", "media", "other"]
        if request.resource_type in blocked_types:
            route.abort()
        else:
            route.continue_()
    except Exception as e:
        print(f"Error in route handler for {request.url}: {str(e)}")
        route.continue_()  # В случае ошибки лучше пропустить запрос


@timeit
def load_main_categories(context: BrowserContext) -> list:
    """
    Загружает основные категории с веб-страницы, используя Playwright.

    Эта функция открывает новую страницу в браузере, переходит по указанному URL,
    ожидает загрузки меню и извлекает основные категории, исключая указанные.

    Args:
        context (BrowserContext): Контекст браузера Playwright для открытия новой страницы.

    Returns:
        list: Список словарей, содержащих информацию о каждой категории,
              включая название, URL и идентификатор меню.
    """
    result = []
    # Открытие новой вкладки
    page = context.new_page()
    page.route("**/*", route_handler)

    try:
        # Увеличиваем таймаут навигации и отключаем ожидание полной загрузки
        page.goto(
            f"{TARGET_URL}",
            timeout=120000,  # 2 минуты на загрузку
            wait_until = "networkidle"  # Ждём, пока не закончатся сетевые запросы
        )

        # Ожидаем появления кнопки меню и кликаем по ней
        button_burger = page.locator('button.nav-element__burger.j-menu-burger-btn').first
        if button_burger:
            button_burger.click()

        # Ждем появления меню с категориями
        page.wait_for_selector('ul.menu-burger__main-list a.menu-burger__main-list-link:has-text("Бренды"):visible')

        # Получаем категории
        main_categories = page.locator('ul.menu-burger__main-list > li.menu-burger__main-list-item').all()

        for category in main_categories:
            category_link = category.locator('a.menu-burger__main-list-link')
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

    except PlaywrightTimeoutError:
        print(f"Таймаут ожидания элемента")
    except Exception as e:
        print(f"{Fore.RED}Обработка ошибок: {str(e)}{Style.RESET_ALL}")
    finally:
        page.close()

    return result


def load_subcategories(
        category: dict,
        context: BrowserContext,
        level: int = 1
) -> dict:
    category_parent = f'. {Fore.CYAN}Родитель - {category.get("parent")}{Style.RESET_ALL}' if category.get("parent") else ""
    print(f'{level * "-" + " " if level != 1 else ""}{category["name"]}{category_parent}')
    while True:
        page = context.new_page()
        try:
            page.route("**/*", route_handler)

            page.goto(
                f"{TARGET_URL}{category['url']}",
                timeout=120000,  # 2 минуты на загрузку
                # wait_until="domcontentloaded"  # Ждём полной загрузки DOM (но не всех ресурсов)
                # wait_until="load"  # Ждем только загрузки DOM, а не всех ресурсов
                wait_until = "networkidle"  # Ждём, пока не закончатся сетевые запросы
            )

            menu_subcategory = page.locator('ul.menu-category__subcategory')
            if menu_subcategory.count() > 0:
                process_menu_items(page, context, category, 'subcategory', level)
                break

            menu_list = page.locator('ul.menu-category__list')
            if menu_list.count() > 0:
                process_menu_items(page, context, category, 'list', level)
                break

            # Получаем все элементы "Категория"
            category_filter = page.locator("div.dropdown-filter:has-text('Категория'):visible").first
            if category_filter:
                category_filter.hover()
                load_and_collect_categories(page, category, level)
                break


            page.wait_for_timeout(TIME_WAIT)
            btm_burger = page.wait_for_selector('button.dropdown-filter__btn--burger > div.dropdown-filter__btn-name')
            if btm_burger.text_content() not in category.get('parent'):
                btm_burger.hover()
                page.wait_for_timeout(TIME_WAIT)
                all_items = page.query_selector_all('ul.filter-category__list > li.filter-category__item')
                for item in all_items:
                    # Извлекаем ссылки
                    link = item.query_selector('a.filter-category__link')
                    if link:
                        parent = category['parent'].copy() if category.get('parent') else []
                        parent.append(category['name'])
                        result.append({
                            'name': link.inner_text().strip(),
                            'url': link.get_attribute('href'),
                            'parent': parent,
                            'level': level,
                        })

            print(f"{Fore.BLUE}{[i['name'] for i in result]}{Style.RESET_ALL}")
            category['subcategories'] = []
            for item in result:
                print(f'идем по списку {item["name"]} - {level}')
                category['subcategories'].append(load_subcategories(item, context, level + 1))
            else:
                print(f'{Fore.GREEN}{level * "-" + "-"} Категорий НЕТ!, [Родитель: {category["name"]}], {level}{Style.RESET_ALL}')
                category['Категория'] = f'Категорий нет'
            break

        except Exception as e:
            print(f"{Fore.RED}Обработка ошибок {category['name']}: {str(e)}{Style.RESET_ALL}")
        finally:
            page.close()

    return category


def process_menu_items(
        page: Page,
        context: BrowserContext,
        category: dict,
        menu_type: str,
        level: int
) -> None:
    """
    Обрабатывает элементы меню категорий и собирает данные о подкатегориях.

    Парсит структуру меню на странице, извлекая названия и ссылки подкатегорий.
    Поддерживает два типа меню: 'subcategory' и 'list'.

    Args:
        page (Page): Экземпляр страницы Playwright.
        context (BrowserContext): Контекст браузера для создания новых страниц.
        category (dict): Словарь с данными текущей категории. Должен содержать:
            - 'name': Название категории
            - 'url': URL категории
            - 'parent': Список родительских категорий (опционально)
        menu_type (str): Тип меню ('subcategory' или 'list').
        level (int): Текущий уровень вложенности (для отладки).

    Returns:
        None: Результаты сохраняются в переданном словаре `category`.
    """
    selector = {
        'subcategory': ('li.menu-category__subcategory-item', 'a.menu-category__subcategory-link'),
        'list': ('li.menu-category__item', 'a.menu-category__link')
    }[menu_type]
    result = []
    menu_items = page.locator(selector[0]).all()
    for item in menu_items:
        # Пропускаем элементы-заголовки (с тегом <p>)
        if menu_type == 'list' and item.locator('p.menu-category__item').count() > 0:
            continue
        link = item.locator(selector[1])
        if link.count() > 0:
            parent = category['parent'].copy() if category.get('parent') else []
            parent.append(category['name'])
            result.append({
                'name': link.inner_text().strip(),
                'url': link.get_attribute('href'),
                'parent': parent,
                'level': level,
            })

    print_results_and_load_subcategories(context, category, result, level)

def print_results_and_load_subcategories(
        context: BrowserContext,
        category: dict,
        result: list,
        level: int
) -> None:
    """
    Выводит результаты парсинга и запускает обработку подкатегорий.

    Args:
        context (BrowserContext): Контекст браузера для создания новых страниц.
        category (dict): Словарь текущей категории для сохранения результатов.
        result (list): Список найденных подкатегорий.
        level (int): Текущий уровень вложенности (для форматирования вывода).
    """
    print(f"{Fore.BLUE}{[i['name'] for i in result]}{Style.RESET_ALL}")
    category['subcategories'] = []

    for item in result:
        print(f'идем по списку {item["name"]} - {level + 1}')
        category['subcategories'].append(load_subcategories(item, context, level + 1))


def load_and_collect_categories(page: Page, category: dict, level: int) -> None:
    try:
        show_all_button = page.locator("button.filter__show-all:has-text('Показать все'):visible").first
        if show_all_button:
            show_all_button.click()

        current_items = page.locator('li.filter__item:visible').all()
        while True:
            if not current_items:
                page.wait_for_timeout(500)
                current_items = page.locator('li.filter__item:visible').all()
                continue

            current_items[-1].hover()
            page.wait_for_timeout(100)

            new_items = page.locator('li.filter__item:visible').all()
            if len(new_items) == len(current_items):
                break

            current_items = new_items

        result = []
        for item in current_items:
            link = item.locator('span.checkbox-with-text__text')
            if link:
                result.append(link.inner_text().strip())

        print(f'{Fore.YELLOW}{level * "-" + "-"} Категорий {len(result)}, [Родитель: {category["name"]}], {level}{Style.RESET_ALL}')
        category['Категория'] = result

    except PlaywrightTimeoutError:
        print("Таймаут ожидания элемента")
    except Exception as e:
        print(f"Произошла ошибка: {e}")


def parse_all_categories() -> list | None:
    with (sync_playwright() as p):
        browser, context = create_browser_session(p)

        result = []
        try:
            print('Получаю категории')
            main_categories = load_main_categories(context)
            print('- Получаю подкатегории для категорий')
            for category in main_categories[:3]:
                result.append(load_subcategories(category, context))

            return result

        except PlaywrightTimeoutError as e:
            print(f"{Fore.BLUE}Timeout error occurred: {e}{Style.RESET_ALL}")
            # Можно сделать скриншот для диагностики
            # page.screenshot(path="error_screenshot.png")
            return None

        except Exception as e:
            print(f"{Fore.BLUE}Other error occurred: {e}{Style.RESET_ALL}")
            return None

        finally:
            # Всегда закрываем контекст и браузер
            context.close()
            browser.close()


if __name__ == "__main__":
    run_wb_parser()
