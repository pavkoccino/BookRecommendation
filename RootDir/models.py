from django.db import models
from django.urls import reverse


# This class represents Book model
class Book(models.Model):
    book_title = models.CharField(max_length=255)
    book_isbn = models.CharField(max_length=13)
    book_author = models.CharField(max_length=255)
    book_year_pub = models.PositiveSmallIntegerField()
    book_publisher = models.CharField(max_length=255)

    class Meta:
        ordering = ('book_title',)
        indexes = [
            models.Index(fields=['book_title', ]),
            models.Index(fields=['book_author', ])
        ]

    def __str__(self):
        return self.book_title + ", by: " + self.book_author

    def get_url(self):
        return reverse('book_detail', args=[self.id])


# This class represents Book Ratings model
class BookRating(models.Model):
    user_id = models.CharField(max_length=10)
    book_isbn = models.CharField(max_length=13)
    book_rating = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('book_isbn',)
        indexes = [
            models.Index(fields=['book_isbn', ]),
            models.Index(fields=['user_id', ])
        ]

    def __str__(self):
        return self.book_isbn + ", given rating: " + str(self.book_rating) + ", by user id: " + self.user_id
