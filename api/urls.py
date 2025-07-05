from django.urls import path

from .views import ItemAPIView, ItemSearchAPIView

urlpatterns = [
    path('products/', ItemAPIView.as_view(), name='products'),  # Список всех продуктов
    path('products/search/', ItemSearchAPIView.as_view(), name='products_search'),  # Поиск продуктов
]
