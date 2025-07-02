from django.db import models

class Item(models.Model):
    title = models.CharField(verbose_name="Название товара", max_length=255)
    price = models.CharField(verbose_name="Цена",  max_length=50)
    discounted_price = models.CharField(verbose_name="Цена со скидкой", max_length=50, blank=True, null=True)
    rating = models.CharField(verbose_name="Рейтинг", max_length=50, blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]
        verbose_name = "Название товара"
        verbose_name_plural = "Название товаров"


