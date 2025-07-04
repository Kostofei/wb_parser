from rest_framework import serializers

from parser.models import Item

class ItemSerializers(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['title', 'price', 'discounted_price', 'rating']
