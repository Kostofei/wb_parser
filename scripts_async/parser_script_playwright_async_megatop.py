import gc
import asyncio
import tracemalloc
from playwright.async_api import (async_playwright, TimeoutError as PlaywrightTimeoutError,
                                  Page, Playwright, Browser, BrowserContext)

from parser.decorators import timeit

# Константы
TARGET_URL = "https://www.wildberries.by"
EXCLUDED_CATEGORIES = ['бренды', 'wibes', 'экспресс', 'акции', 'грузовая доставка']


class EmptyCategoriesError(Exception):
    """Вызывается, когда не удалось загрузить категории"""
    pass


@timeit
async def run_wb_parser():
    result = await parse_all_categories()
    print(result)
    # print_categories(result)


async def print_categories(categories, level=0):
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
            await print_categories(cat['subcategories'], level + 2)


async def create_browser_session(p: Playwright) -> tuple[Browser, BrowserContext]:
    """
    Настраивает и возвращает экземпляр браузера, контекст и страницу Playwright.

    Args:
        p (Playwright): Экземпляр Playwright.

    Returns:
        tuple[Browser, BrowserContext]: Экземпляр браузера, контекст и страница.
    """
    # Запускаем браузер с дополнительными параметрами
    browser = await p.chromium.launch(
        headless=True,
        # headless=False,
        timeout=60000,  # Увеличиваем таймаут запуска браузера
        slow_mo=0  # Добавляем задержку между действиями (мс)
    )

    # Создание контекста (окна браузера с настройками)
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )

    return browser, context


async def route_handler(route, request):
    """Блокировка "лишних" ресурсов (ускорение загрузки)"""
    try:
        blocked_types = ["image", "font", "stylesheet", "media", "other"]
        if request.resource_type in blocked_types:
            await route.abort()
        else:
            await route.continue_()
    except Exception as e:
        print(f"Error in route handler for {request.url}: {str(e)}")
        await route.continue_()  # В случае ошибки лучше пропустить запрос


async def load_main_categories(context: BrowserContext) -> list:
    """Загружает список основных категорий с сайта"""
    # Открытие новой вкладки
    page = await context.new_page()
    try:
        # Настройка страницы
        await page.route("**/*", route_handler)

        # Увеличиваем таймаут навигации и отключаем ожидание полной загрузки
        await page.goto(
            f"{TARGET_URL}",
            timeout=120000,  # 2 минуты на загрузку
            wait_until="domcontentloaded"  # Ждем только загрузки DOM, а не всех ресурсов
        )

        # Ожидание и клик по бургер-меню
        burger_button = await page.wait_for_selector(
            'button.nav-element__burger.j-menu-burger-btn',
            state="visible",
            timeout=30000
        )
        await burger_button.click()

        # Ждем появления второго меню
        await page.wait_for_selector(
            'ul.menu-burger__main-list a.menu-burger__main-list-link:has-text("Бренды")',
            state="visible",
            timeout=30000
        )

        # Основной сбор данных
        main_categories = await page.query_selector_all(
            'ul.menu-burger__main-list > li.menu-burger__main-list-item'
        )

        result = []
        for category in main_categories:
            try:
                category_link = await category.query_selector('a.menu-burger__main-list-link')
                if not category_link:
                    continue

                name = (await category_link.inner_text()).strip()
                if name.lower() in EXCLUDED_CATEGORIES:
                    continue

                result.append({
                    'name': name,
                    'url': await category_link.get_attribute('href'),
                    'data_menu_id': await category.get_attribute('data-menu-id'),
                })
            except Exception as e:
                print(f"Ошибка при обработке категории: {e}")
                continue

        return result
    except Exception as e:
        print(f"Ошибка в load_main_categories: {e}")
        return []
    finally:
        await page.close()
        del page
        gc.collect()


async def load_subcategories(
        category: dict,
        all_categories: list,
        context: BrowserContext,
        sem: asyncio.Semaphore,
        level: int = 1
) -> dict:
    """Загружает подкатегории для указанной категории"""
    async with sem:
        print(
            f'{level * "-"} {category["name"]} - [Родитель: {category.get("parent") if category.get("parent") else "Нет!"}]')
        page = await context.new_page()
        try:
            # Настройка страницы
            # await page.route("**/*", route_handler)

            # Навигация
            await page.goto(
                f"{TARGET_URL}{category['url']}",
                timeout=120000,
                wait_until="domcontentloaded"
            )

            # Основная логика сбора данных
            result = await _extract_subcategories(page, category, all_categories, level)

            if result:
                new_all_categories = [i['name'] for i in result]
                print(f'Получаю подкатегории {level}')
                sub_sem = asyncio.Semaphore(5)
                tasks = [load_subcategories(subcat, new_all_categories, context, sub_sem, level + 1) for subcat in result]
                category['subcategories'] = await asyncio.gather(*tasks, return_exceptions=False)

            return category

        except Exception as e:
            print(f"Ошибка обработки категории {category['name']}: {str(e)}")
            return category
        finally:
            await page.close()
            del page
            gc.collect()


async def _extract_subcategories(
        page: Page,
        category: dict,
        all_categories: list,
        level: int
) -> list:
    """Вспомогательная функция для извлечения подкатегорий"""

    # # 🔍 Старт мониторинга памяти
    # tracemalloc.start()
    # snapshot_before = tracemalloc.take_snapshot()

    result = []

    try:
        # Попытка первого варианта структуры страницы
        try:
            await page.wait_for_selector(
                'ul.menu-category__subcategory',
                state="visible",
                timeout=1500
            )
            menu_items = await page.query_selector_all(
                'li.menu-category__subcategory-item'
            )
            # Обработка найденных элементов
            for item in menu_items:
                link = await item.query_selector('a.menu-category__subcategory-link')
                if link:
                    result.append({
                        'name': (await link.inner_text()).strip(),
                        'url': await link.get_attribute('href'),
                        'parent': category['name'],
                    })
        except:
            # Попытка второго варианта структуры страницы
            await page.wait_for_selector(
                'ul.menu-category__list',
                state="visible",
                timeout=1500
            )
            menu_items = await page.query_selector_all(
                'li.menu-category__item'
            )
            # Обработка найденных элементов
            for item in menu_items:
                if await item.query_selector('p.menu-category__item'):
                    continue

                link = await item.query_selector('a.menu-category__link')
                if link:
                    result.append({
                        'name': (await link.inner_text()).strip(),
                        'url': await link.get_attribute('href'),
                        'parent': category['name'],
                    })
        return result

    except:
        # Альтернативная логика для других структур страниц
        return await _extract_alternative_structure(page, category, all_categories, level)

    # finally:
    #     # 📸 Снимок памяти после выполнения
    #     snapshot_after = tracemalloc.take_snapshot()
    #     stats = snapshot_after.compare_to(snapshot_before, 'lineno')
    #
    #     print(f"\n📈 [Топ 5 по потреблению памяти в _extract_subcategories (level={level})]:")
    #     for i, stat in enumerate(stats[:5]):
    #         print(f"{i + 1}. {stat}")
    #
    #     tracemalloc.stop()
    #
    # return result


async def _extract_alternative_structure(
        page: Page,
        category: dict,
        all_categories: list,
        level: int
) -> list | None:
    """Обработка альтернативных структур страниц (категории в фильтрах)"""
    result = []

    try:
        # Ожидание и обработка фильтра "Категория"
        await page.wait_for_timeout(1500)
        show_all_filter = page.locator("div.dropdown-filter:has-text('Категория')")
        await page.wait_for_timeout(1500)
        if await show_all_filter.count() >= 2:
            await show_all_filter.nth(1).hover()

            show_all_buttons = page.locator("button.filter__show-all:has-text('Показать все')")
            await page.wait_for_timeout(1500)
            if await show_all_buttons.count() >= 2:
                await show_all_buttons.nth(1).click()

            # Сбор всех элементов категорий
            all_items = []
            count_items = 0
            while True:
                current_items = await page.query_selector_all('li.filter__item')
                if not current_items or count_items == len(current_items):
                    break

                await current_items[-1].hover()
                await page.wait_for_timeout(500)
                count_items = len(current_items)
                all_items = current_items

            # Обработка элементов фильтра
            for item in all_items:
                link = await item.query_selector('span.checkbox-with-text__text')
                parent_container = await item.evaluate("el => el.closest('.measurementContainer--GRwov') === null")

                if link and parent_container:
                    result.append((await link.inner_text()).strip())

            result.append({'parent': category['name'], 'level': level})
            print(f'{level * "-" + "-"} Категорий {len(result)}, [Родитель: {category["name"]}], {level}')
            category['Категория'] = result
            return None
        else:
            # Вариант 2: Категории в бургер-меню
            await page.wait_for_timeout(1500)
            burger_button = await page.wait_for_selector(
                "button.dropdown-filter__btn--burger > div.dropdown-filter__btn-name",
                timeout=5000
            )
            await burger_button.hover()
            await page.wait_for_timeout(1500)

            # Сбор элементов из бургер-меню
            menu_items = await page.query_selector_all('li.filter-category__item')
            for item in menu_items:
                link = await item.query_selector('a.filter-category__link')
                if link:
                    result.append({
                        'name': (await link.inner_text()).strip(),
                        'url': await link.get_attribute('href'),
                        'parent': category['name']
                    })
            new_result = [i['name'] for i in result]
            if new_result != all_categories:
                return result
            else:
                print(f'{level * "-" + "-"} Категорий НЕТ!, [Родитель: {category["name"]}], {level}')
                category['Категория'] = f'Категорий нет {level}'
                return None

    except Exception as e:
        print(f"Ошибка при обработке альтернативной структуры: {str(e)}")
        return None


async def parse_all_categories() -> list | None:
    async with async_playwright() as p:
        browser, context = await create_browser_session(p)

        try:
            print('Получаю категории')
            list_main_categories = await load_main_categories(context)
            if not list_main_categories:
                raise EmptyCategoriesError("Не удалось загрузить категории (пустой список)")

            print('Получаю подкатегории 0')
            sem = asyncio.Semaphore(10)  # Максимум X задач одновременно
            all_categories = [category['name'] for category in list_main_categories]
            tasks = [load_subcategories(category, all_categories, context, sem) for category in list_main_categories[13:14]]
            results = await asyncio.gather(*tasks)

            # Фильтруем результаты, удаляя исключения
            valid_results = [r for r in results if not isinstance(r, Exception)]
            return valid_results

        except EmptyCategoriesError as e:
            print(f"Ошибка: {e}")  # Логируем кастомную ошибку
            return None

        except PlaywrightTimeoutError as e:
            print(f"Timeout error occurred: {e}")
            return None

        except Exception as e:
            print(f"Other error occurred: {e}")
            return None

        finally:
            # Всегда закрываем контекст и браузер
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(run_wb_parser())
