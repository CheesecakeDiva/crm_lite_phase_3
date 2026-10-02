from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Company, Storage, Supplier, Product, Supply

User = get_user_model()


class CRMSecurityTests(APITestCase):

    def setUp(self):
        # Компания 1
        self.owner1 = User.objects.create_user(email="owner1@test.com", password="password123")
        self.company1 = Company.objects.create(name="Компания 1", owner=self.owner1)
        self.storage1 = Storage.objects.create(name="Склад 1", company=self.company1)
        self.supplier1 = Supplier.objects.create(title="Поставщик 1", INN="1111111111", company=self.company1)
        self.product1 = Product.objects.create(title="Товар 1", purchase_price=10, sale_price=20, quantity=0,
                                               storage=self.storage1)

        # Компания 2
        self.owner2 = User.objects.create_user(email="owner2@test.com", password="password123")
        self.company2 = Company.objects.create(name="Компания 2", owner=self.owner2)
        self.storage2 = Storage.objects.create(name="Склад 2", company=self.company2)
        self.supplier2 = Supplier.objects.create(title="Поставщик 2", INN="2222222222", company=self.company2)
        self.product2 = Product.objects.create(title="Товар 2", purchase_price=50, sale_price=90, quantity=0,
                                               storage=self.storage2)

    def test_cannot_supply_with_foreign_supplier_or_product(self):
        #Тест на изоляцию
        self.client.force_authenticate(user=self.owner1)
        url = reverse('supply-list')

        # Чужой поставщик (supplier2)
        data_bad_supplier = {
            "supplier_id": self.supplier2.id,
            "products": [{"id": self.product1.id, "quantity": 10}]
        }
        response = self.client.post(url, data_bad_supplier, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Чужой товар (product2)
        data_bad_product = {
            "supplier_id": self.supplier1.id,
            "products": [{"id": self.product2.id, "quantity": 10}]
        }
        response = self.client.post(url, data_bad_product, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transaction_rollback_on_error(self):
        #Тест на транзакции
        self.client.force_authenticate(user=self.owner1)
        url = reverse('supply-list')

        # Отправляем один хороший товар и один чужой (ошибочный) товар
        data = {
            "supplier_id": self.supplier1.id,
            "products": [
                {"id": self.product1.id, "quantity": 15},  # Хороший
                {"id": self.product2.id, "quantity": 10}  # Чужой (вызовет ошибку)
            ]
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, 0)

    def test_quantity_is_read_only(self):
        #Тест на read-only
        self.client.force_authenticate(user=self.owner1)
        url = reverse('product-detail', kwargs={'pk': self.product1.id})

        # Пытаемся напрямую переписать количество товара на 999
        data = {"quantity": 999, "title": "Хакинг остатков"}
        self.client.patch(url, data, format='json')

        # Проверяем, что поле проигнорировано и остаток остался равен 0
        self.product1.refresh_from_db()
        self.assertNotEqual(self.product1.quantity, 999)
        self.assertEqual(self.product1.quantity, 0)

