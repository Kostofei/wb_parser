from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Item(models.Model):
    """
        Модель товара, содержащая информацию о названии, цене, скидке, рейтинге и валюте.

        Атрибуты:
            title (str): Название товара, максимум 255 символов.
            price (Decimal): Полная цена товара, до 11 цифр с 2 знаками после запятой.
            discounted_price (Decimal): Цена товара со скидкой, до 10 цифр с 2 знаками после запятой.
            rating (float, optional): Средний рейтинг товара от 0.0 до 5.0.
            rating_count (int): Общее количество оценок товара.
            currency (str): Валюта, в которой указана цена товара (до 10 символов).
        """
    title = models.CharField(
        verbose_name="Название товара",
        max_length=255,
        help_text="Полное наименование товара (до 255 символов)"
    )
    price = models.DecimalField(
        verbose_name="Цена",
        max_digits=11, decimal_places=2,
        help_text="Полная цена товара"
    )
    discounted_price = models.DecimalField(
        verbose_name="Цена со скидкой",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        default=None,
        help_text="Цена товара после применения всех скидок"
    )
    rating = models.FloatField(
        verbose_name="Рейтинг",
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        blank=True,
        null=True,
        default=None,
        help_text="Средняя оценка товара (от 0.0 до 5.0)"
    )
    rating_count = models.PositiveIntegerField(
        verbose_name="Количество оценок",
        blank=True,
        null=True,
        default=None,
        help_text="Сколько раз товар был оценён пользователями"
    )
    currency = models.CharField(
        verbose_name="Валюта",
        max_length=10,
        help_text="Валюта, в которой указана цена (например, BYN, USD, EUR)"
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]
        verbose_name = "Название товара"
        verbose_name_plural = "Название товаров"
