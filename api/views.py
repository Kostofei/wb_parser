from rest_framework import generics
from rest_framework.pagination import LimitOffsetPagination

from api.serializers import ItemSerializers
from parser.models import Item


class ItemAPIView(generics.ListAPIView):
    """Выводим все секций новостей"""
    queryset = Item.objects.all()
    serializer_class = ItemSerializers
