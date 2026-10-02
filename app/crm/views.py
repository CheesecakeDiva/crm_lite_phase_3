from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from django.db import models
from django.contrib.auth import get_user_model

from .models import Company, Storage, Supplier, Product, Supply
from .serializers import (
    CompanySerializer, StorageSerializer, SupplierSerializer,
    ProductSerializer, SupplyCreateSerializer, SupplyListSerializer
)
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from .models import Sale, ProductSale
from .serializers import SaleCreateSerializer, SaleUpdateSerializer, SaleListSerializer


User = get_user_model()


class IsCompanyEmployee(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return Company.objects.filter(owner=user).exists() or getattr(user, 'company_id', None) is not None


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Company.objects.filter(
            models.Q(owner=user) | models.Q(id=getattr(user, 'company_id', None))
        )


    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def attach_user(self, request):
        try:
            company = Company.objects.get(owner=request.user)
        except Company.DoesNotExist:
            return Response({"error": "Вы не являетесь владельцем компании."}, status=status.HTTP_403_FORBIDDEN)

        user_email = request.data.get('email')
        if not user_email:
            return Response({"error": "Укажите email пользователя в теле запроса."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return Response({"error": "Пользователь с таким email не найден."}, status=status.HTTP_404_NOT_FOUND)

        target_user.company = company
        target_user.save()
        return Response({"message": f"Пользователь {user_email} успешно прикреплен к компании {company.name}."},
                        status=status.HTTP_200_OK)


class StorageViewSet(viewsets.ModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        user = self.request.user
        return Storage.objects.filter(
            models.Q(company__owner=user) | models.Q(company_id=getattr(user, 'company_id', None))
        ).distinct()

    def create(self, request, *args, **kwargs):
        try:
            company = Company.objects.get(owner=request.user)
        except Company.DoesNotExist:
            raise ValidationError(
                {"error": "Сначала создайте компанию. Вы не являетесь владельцем какой-либо компании."})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(company=company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        user = self.request.user
        return Supplier.objects.filter(
            models.Q(company__owner=user) | models.Q(company_id=getattr(user, 'company_id', None))
        ).distinct()

    def perform_create(self, serializer):
        try:
            if Company.objects.filter(owner=self.request.user).exists():
                company = Company.objects.get(owner=self.request.user)
            else:
                company = Company.objects.get(id=self.request.user.company_id)
            serializer.save(company=company)
        except Exception:
            raise ValidationError({"error": "Вы не привязаны ни к одной компании."})



class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        user = self.request.user
        return Product.objects.filter(
            models.Q(storage__company__owner=user) | models.Q(storage__company_id=getattr(user, 'company_id', None))
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        storage_id = self.request.data.get('storage')

        try:
            storage = Storage.objects.get(id=storage_id)
        except Storage.DoesNotExist:
            raise ValidationError({"storage": "Указанный склад не существует."})

        user_company_id = Company.objects.filter(owner=user).first().id if Company.objects.filter(
            owner=user).exists() else getattr(user, 'company_id', None)

        if storage.company_id != user_company_id:
            raise ValidationError({"error": "Вы не можете добавить товар на склад чужой компании."})

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        storage_id = self.request.data.get('storage')

        if storage_id:
            try:
                storage = Storage.objects.get(id=storage_id)
            except Storage.DoesNotExist:
                raise ValidationError({"storage": "Указанный склад не существует."})

            user_company_id = Company.objects.filter(owner=user).first().id if Company.objects.filter(
                owner=user).exists() else getattr(user, 'company_id', None)

            if storage.company_id != user_company_id:
                raise ValidationError({"error": "Вы не можете перенести товар на склад чужой компании."})

        serializer.save()


class SupplyViewSet(viewsets.ModelViewSet):
    queryset = Supply.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_serializer_class(self):
        if self.action == 'create':
            return SupplyCreateSerializer
        return SupplyListSerializer

    def get_queryset(self):
        user = self.request.user
        return Supply.objects.filter(
            models.Q(supplier__company__owner=user) | models.Q(supplier__company_id=getattr(user, 'company_id', None))
        ).distinct()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return SaleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SaleUpdateSerializer
        return SaleListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Sale.objects.filter(
            models.Q(company__owner=user) | models.Q(company_id=getattr(user, 'company_id', None))
        ).distinct()

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(sale_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__lte=end_date)

        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            product_sales = ProductSale.objects.filter(sale=instance)

            for item in product_sales:
                product = item.product
                product.quantity += item.quantity
                product.save()

            instance.delete()

        return Response({"message": "Продажа успешно удалена, товары возвращены на склад."},
                        status=status.HTTP_204_NO_CONTENT)


