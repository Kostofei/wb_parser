from django.urls import path

from .views import ItemAPIView

urlpatterns = [
    path('products/', ItemAPIView.as_view(), name='news_section'),  # Список всех секций
]