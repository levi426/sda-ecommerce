from django.db import models
from users.models import User


class BaseProduct(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  

    def __str__(self):
        return self.name


class ClothingProduct(BaseProduct):
    CATEGORY_CHOICES = (
        ('shirt', 'Shirt'),
        ('pents', 'Pents'),
        ('shalwar_kameez', 'Shalwar Kameez'),
        ('accessories', 'Accessories'),
    )
    stock = models.PositiveIntegerField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)


class Review(models.Model):
    
    product_type = models.CharField(max_length=50, blank=True, null=True)  
    product_id = models.PositiveIntegerField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField() 
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.product_type}({self.product_id})"

