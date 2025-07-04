from django.db import models


class Item(models.Model):
    title = models.CharField(verbose_name="Название товара", max_length=255)
    price = models.DecimalField(verbose_name="Цена", max_digits=11, decimal_places=2)
    discounted_price = models.DecimalField(verbose_name="Цена со скидкой",
                                           max_digits=10,
                                           decimal_places=2,
                                           blank=True,
                                           null=True)
    rating = models.CharField(verbose_name="Рейтинг", max_length=50, blank=True, null=True)
    currency = models.CharField(verbose_name="Валюта", max_length=10)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]
        verbose_name = "Название товара"
        verbose_name_plural = "Название товаров"
