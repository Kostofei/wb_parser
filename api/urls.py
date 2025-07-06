from django.urls import path

from .views import ItemAPIView, ItemSearchAPIView, DeleteAllItemsListAPIView

urlpatterns = [
    path('products/', ItemAPIView.as_view(), name='products'),
    path('products/search/', ItemSearchAPIView.as_view(), name='products_search'),
    path('products/delete_all/', DeleteAllItemsListAPIView.as_view(), name='delete_all_product'),
]
