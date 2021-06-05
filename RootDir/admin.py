from django.contrib import admin

# Register your models here.
from .models import Book, BookRating

admin.site.register(Book)
admin.site.register(BookRating)