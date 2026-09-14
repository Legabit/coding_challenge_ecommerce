from decimal import Decimal, InvalidOperation
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.response import Response

from products.models import Category, Product
from products.serializers import CategorySerializer, ProductSerializer
from products.services.csv_importer import CSVImporter


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    pagination_class = None


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("search", "").strip()
        if not query:
            query = self.request.query_params.get("q", "").strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(description__icontains=query)
            )

        category_param = self.request.query_params.get("category", "").strip()
        if category_param:
            if category_param.isdigit():
                queryset = queryset.filter(category_id=int(category_param))
            else:
                queryset = queryset.filter(
                    Q(category__name__iexact=category_param) |
                    Q(category__slug__iexact=category_param)
                )

        min_price = self.request.query_params.get("min_price", "").strip()
        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except (InvalidOperation, ValueError):
                pass

        max_price = self.request.query_params.get("max_price", "").strip()
        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except (InvalidOperation, ValueError):
                pass

        in_stock = self.request.query_params.get("in_stock", "").strip().lower()
        if in_stock in ("true", "1", "yes"):
            queryset = queryset.filter(stock__gt=0)
        elif in_stock in ("false", "0", "no"):
            queryset = queryset.filter(stock=0)

        ordering = self.request.query_params.get("ordering", "-created_at").strip()
        valid_orderings = ["price", "-price", "name", "-name", "stock", "-stock", "created_at", "-created_at"]
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            csv_content = request.data.get("csv_text")
            if not csv_content:
                return Response(
                    {"detail": "No file uploaded or csv_text provided."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            result = CSVImporter.import_from_stream(csv_content)
        else:
            result = CSVImporter.import_from_stream(file_obj)

        http_status = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)
