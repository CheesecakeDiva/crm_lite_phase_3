from rest_framework import serializers
from django.db import transaction
from .models import Company, Storage, Supplier, Product, Supply, SupplyProduct


class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.email')

    class Meta:
        model = Company
        fields = ['id', 'name', 'owner']

    def create(self, validated_data):
        user = self.context['request'].user
        if Company.objects.filter(owner=user).exists():
            raise serializers.ValidationError("У вас уже есть созданная компания.")
        return Company.objects.create(owner=user, **validated_data)


class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storage
        fields = ['id', 'name', 'company']
        read_only_fields = ['company']


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'title', 'INN', 'company']
        read_only_fields = ['company']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'title', 'purchase_price', 'sale_price', 'quantity', 'storage']
        read_only_fields = ['quantity']

    def create(self, validated_data):
        validated_data['quantity'] = 0
        return super().create(validated_data)


class SupplyProductCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    quantity = serializers.IntegerField()

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество товара должно быть больше нуля.")
        return value


class SupplyCreateSerializer(serializers.ModelSerializer):
    supplier_id = serializers.IntegerField()
    products = SupplyProductCreateSerializer(many=True)

    class Meta:
        model = Supply
        fields = ['supplier_id', 'products']

    def create(self, validated_data):
        supplier_id = validated_data['supplier_id']
        products_data = validated_data['products']
        user = self.context['request'].user

        user_company = Company.objects.filter(owner=user).first()
        if not user_company:
            user_company = Company.objects.filter(id=getattr(user, 'company_id', None)).first()

        if not user_company:
            raise serializers.ValidationError("Вы не привязаны ни к одной компании.")


        try:
            supplier = Supplier.objects.get(id=supplier_id, company=user_company)
        except Supplier.DoesNotExist:
            raise serializers.ValidationError({"supplier_id": "Поставщик не найден или принадлежит чужой компании."})


        verified_products = []
        for prod_item in products_data:
            product_id = prod_item['id']
            qty = prod_item['quantity']

            try:
                product = Product.objects.get(id=product_id, storage__company=user_company)
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Товар с id {product_id} не найден или принадлежит чужой компании.")

            verified_products.append((product, qty))


        with transaction.atomic():
            supply = Supply.objects.create(supplier=supplier)

            for product, qty in verified_products:
                SupplyProduct.objects.create(supply=supply, product=product, quantity=qty)

                product.quantity += qty
                product.save()

        return supply


class SupplyListSerializer(serializers.ModelSerializer):
    supplier = serializers.CharField(source='supplier.title')

    class Meta:
        model = Supply
        fields = ['id', 'supplier', 'delivery_date']


