from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from api.serializers import ItemSerializers
from parser.models import Item


class ItemAPIView(generics.ListAPIView):
    """
    GET /api/v1/products/ - Получение списка товаров

    Предоставляет список всех товаров в формате JSON через сериализатор ItemSerializer.

    Параметры: отсутствуют

    Пример запроса:
    GET /api/v1/products/

    Пример ответа (200 OK):
    ```json
    [
        {
            "title": "Смартфон",
            "price": 59990.35,
            "discounted_price": 54990.00,
            "rating": 4.7,
            "currency": "RUB"
        },
        {
            "title": "Ноутбук",
            "price": 1590.78,
            "discounted_price": null,
            "rating": 4.9,
            "currency": "BYN"
        }
    ]
    ```

    Структура ответа:
    - title (string): Название товара
    - price (decimal): Цена (2 знака после запятой)
    - discounted_price (decimal|null): Цена со скидкой
    - rating (float): Рейтинг
    - currency (string): Код валюты

    Возможные ошибки:
    - 500: Ошибка сервера
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializers


class ItemSearchAPIView(generics.ListAPIView):
    """
    API endpoint для поиска товаров.

    Этот класс предоставляет API endpoint для поиска товаров по различным полям.
    Использует сериализатор `ItemSerializers` для преобразования данных в формат JSON.

    Атрибуты:
        queryset (QuerySet): Запрос к базе данных для получения всех объектов модели `Item`.
        serializer_class (ModelSerializer): Класс сериализатора, используемый для сериализации данных.
        filter_backends (list): Список бэкендов фильтрации, используемых для фильтрации запросов.
        search_fields (list): Список полей, по которым выполняется поиск.

    Пример использования:
        Для поиска товаров выполните GET-запрос к этому endpoint с параметром `search`.
        Пример запроса:
        GET /api/items/search/?search=Название товара

    Возвращаемые данные:
    Пример ответа (200 OK):
    ```json
    [
        {
            "title": "Название товара",
            "price": "Цена товара",
            "discounted_price": "Цена со скидкой",
            "rating": "Рейтинг товара",
            "currency": "Валюта"
        },
        {
            "title": "Название другого товара",
            "price": "Цена другого товара",
            "discounted_price": "Цена со скидкой другого товара",
            "rating": "Рейтинг другого товара",
            "currency": "Валюта"
        }
    ]
    ```

    Возможные ошибки:
    - 500: Ошибка сервера
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializers
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['price', 'discounted_price', 'rating']





