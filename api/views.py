from rest_framework.generics import ListAPIView, DestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import status

from api.filters import ItemFilter
from api.serializers import ItemSerializer
from parser.models import Item


class ItemAPIView(ListAPIView):
    """
    Получение списка товаров

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
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializer


class ItemSearchAPIView(ListAPIView):
    """
    API endpoint для фильтрации товаров.

    Позволяет отфильтровать список товаров по следующим параметрам:
    - цене (`price`, `min_price`, `max_price`)
    - рейтингу (`rating`, `min_rating`, `max_rating`)
    - количеству отзывов (`reviews_count`, `min_reviews_count`, `max_reviews_count`)

    Использует сериализатор `ItemSerializers` для преобразования объектов модели `Item` в формат JSON.

    Поддерживаемые параметры запроса:
        - `price` — точное значение цены
        - `min_price`, `max_price` — диапазон цены
        - `rating` — точное значение рейтинга
        - `min_rating`, `max_rating` — диапазон рейтинга
        - `reviews_count` — точное количество отзывов
        - `min_reviews_count`, `max_reviews_count` — диапазон отзывов

    Пример использования:
        Выполните GET-запрос с нужными параметрами:

        Примеры запросов:
            GET /api/products/?min_price=1000&max_price=5000
            GET /api/products/?rating=4.5
            GET /api/products/?min_reviews_count=10

    Пример ответа (200 OK):
    ```json
    [
        {
            "id": 1,
            "title": "Смартфон Galaxy",
            "price": "4999.99",
            "discounted_price": "4499.99",
            "rating": "4.6",
            "reviews_count": 152,
            "currency": "BYN"
        },
        {
            "id": 2,
            "title": "Планшет Tab X",
            "price": "3200.00",
            "discounted_price": "2999.00",
            "rating": "4.5",
            "reviews_count": 87,
            "currency": "BYN"
        }
    ]
    ```
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ItemFilter


class DeleteAllItemsListAPIView(DestroyAPIView):
    """
    API endpoint для удаления всех записей модели Item.

    Поддерживает только DELETE-запрос.
    При успешном удалении возвращает количество удалённых записей.
    """
    queryset = Item.objects.all()

    def delete(self, request, *args, **kwargs):
        try:
            # Удаляем все записи из модели Item
            deleted_count, _ = self.get_queryset().delete()
            return Response(
                {"message": f"Все записи успешно удалены. Удалено записей: {deleted_count}."},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
