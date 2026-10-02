from django.db import models
from django.conf import settings

class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название компании")
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_company",
        verbose_name="Владелец"
    )

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"

    def __str__(self):
        return self.name

class Storage(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название склада")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="storages",
        verbose_name="Компания"
    )

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склады"

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Supplier(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название поставщика")
    INN = models.CharField(max_length=12, verbose_name="ИНН")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="suppliers",
        verbose_name="Компания"
    )

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"

    def __str__(self):
        return self.title

class Product(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название товара")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Закупочная цена")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена продажи")
    quantity = models.IntegerField(default=0, verbose_name="Количество")
    storage = models.ForeignKey(
        Storage,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="Склад"
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.title

class Supply(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="supplies",
        verbose_name="Поставщик"
    )
    delivery_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата поставки")
    products = models.ManyToManyField(
        Product,
        through="SupplyProduct",
        related_name="supplies",
        verbose_name="Товары"
    )

    class Meta:
        verbose_name = "Поставка"
        verbose_name_plural = "Поставки"

    def __str__(self):
        return f"Поставка №{self.id} от {self.delivery_date.strftime('%d.%m.%Y')}"

class SupplyProduct(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, verbose_name="Поставка")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.IntegerField(verbose_name="Количество")

    class Meta:
        verbose_name = "Товар в поставке"
        verbose_name_plural = "Товары в поставке"

