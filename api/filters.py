import django_filters

from parser.models import Item


class ItemFilter(django_filters.FilterSet):
    # Фильтрация по цене
    price = django_filters.NumberFilter(field_name='price', lookup_expr='exact')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Фильтрация по рейтингу
    rating = django_filters.NumberFilter(field_name='rating', lookup_expr='exact')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')

    # Фильтрация по количеству отзывов
    reviews_count = django_filters.NumberFilter(field_name='reviews_count', lookup_expr='exact')
    min_reviews_count = django_filters.NumberFilter(field_name='reviews_count', lookup_expr='gte')
    max_reviews_count = django_filters.NumberFilter(field_name='reviews_count', lookup_expr='lte')

    class Meta:
        model = Item
        fields = [
            'price', 'min_price', 'max_price',
            'rating', 'min_rating', 'max_rating',
            'reviews_count', 'min_reviews_count', 'max_reviews_count'
        ]