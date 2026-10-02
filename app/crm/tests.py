from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Company, Storage, Supplier, Product, Supply, Sale, ProductSale

User = get_user_model()


class CRMAllPhaseTests(APITestCase):

    def setUp(self):
        # Компания 1
        self.user = User.objects.create_user(email="owner1@test.com", password="password123")
        self.company = Company.objects.create(name="Компания 1", owner=self.user)
        self.storage = Storage.objects.create(name="Склад 1", company=self.company)
        self.supplier = Supplier.objects.create(title="Поставщик 1", INN="1111111111", company=self.company)
        self.product = Product.objects.create(title="Товар 1", purchase_price=10, sale_price=20, quantity=25,
                                              storage=self.storage)

        # Компания 2
        self.user2 = User.objects.create_user(email="owner2@test.com", password="password123")
        self.company2 = Company.objects.create(name="Компания 2", owner=self.user2)
        self.storage2 = Storage.objects.create(name="Склад 2", company=self.company2)
        self.product2 = Product.objects.create(title="Товар 2", purchase_price=50, sale_price=90, quantity=0,
                                               storage=self.storage2)


    def test_cannot_supply_with_foreign_supplier_or_product(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('supply-list')

        data_bad_product = {
            "supplier_id": self.supplier.id,
            "products": [{"id": self.product2.id, "quantity": 10}]
        }
        response = self.client.post(url, data_bad_product, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transaction_rollback_on_supply_error(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('supply-list')

        data = {
            "supplier_id": self.supplier.id,
            "products": [
                {"id": self.product.id, "quantity": 15},
                {"id": self.product2.id, "quantity": 10}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 25)

    def test_quantity_is_read_only_directly(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('product-detail', kwargs={'pk': self.product.id})

        data = {"quantity": 999}
        self.client.patch(url, data, format='json')

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 25)


    def test_create_sale_decreases_quantity(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('sale-list')

        data = {
            "buyer_name": "Тестовый Покупатель",
            "sale_date": timezone.now().isoformat(),
            "product_sales": [{"product": self.product.id, "quantity": 5}]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 20)

    def test_insufficient_quantity_raises_error(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('sale-list')

        data = {
            "buyer_name": "Жадный Покупатель",
            "sale_date": timezone.now().isoformat(),
            "product_sales": [{"product": self.product.id, "quantity": 100}]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_sale_restores_quantity(self):
        self.client.force_authenticate(user=self.user)

        sale = Sale.objects.create(buyer_name="Возвратный Покупатель", sale_date=timezone.now(), company=self.company)
        ProductSale.objects.create(sale=sale, product=self.product, quantity=5)
        self.product.quantity -= 5
        self.product.save()

        url = reverse('sale-detail', kwargs={'pk': sale.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 25)

