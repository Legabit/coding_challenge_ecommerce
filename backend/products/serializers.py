from decimal import Decimal
from rest_framework import serializers
from products.models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "products_count"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True
    )
    category_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "description",
            "category",
            "category_id",
            "category_name",
            "price",
            "stock",
            "weight_kg",
            "created_at",
            "updated_at",
        ]

    def validate_price(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Price must be greater than or equal to 0.00")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock must be greater than or equal to 0")
        return value

    def validate_weight_kg(self, value):
        if value < Decimal("0.000"):
            raise serializers.ValidationError("Weight must be greater than or equal to 0.000")
        return value

    def create(self, validated_data):
        category_name = validated_data.pop("category_name", None)
        if category_name and not validated_data.get("category"):
            category, _ = Category.objects.get_or_create(name=category_name.strip())
            validated_data["category"] = category
        return super().create(validated_data)

    def update(self, instance, validated_data):
        category_name = validated_data.pop("category_name", None)
        if category_name:
            category, _ = Category.objects.get_or_create(name=category_name.strip())
            validated_data["category"] = category
        return super().update(instance, validated_data)
