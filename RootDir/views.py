import os  # library for OS dependent functionality like working with files etc.

from RootDir.operation.data_loading import download_file_from_url, fill_books_table_with_csv, \
    delete_all_data_from_database, fill_book_ratings_table_with_csv, calculate_correlation_table
from django.shortcuts import render, get_object_or_404
from .models import Book
from django.db.models import Q


# This function displays all the books found by the query
def book_list(request):
    book = Book.objects.all()
    return render(request, 'Homepage/index.html', {'book': book})


# Define function to display the particular book
def book_detail(request, id):
    book = get_object_or_404(Book, id=id)
    correlation_table = calculate_correlation_table(book)

    return render(request, 'Homepage/book_detail.html',
                  {'book': book, 'correlations': correlation_table.to_html(index=False, justify='left')})

# This function represents view for search
def search(request):
    results = []
    if request.method == "GET":
        query = request.GET.get('search')
        if query == '':
            query = 'None'
        results = Book.objects.filter(Q(book_title__icontains=query) | Q(book_author__icontains=query))
    return render(request, 'Homepage/search.html', {'query': query, 'results': results})


# This function represents view for the index.html
def home_page_view(request):
    if is_request_method_post(request.method) and was_btn_pressed('run_script', request):
        download_file_from_url("http://www2.informatik.uni-freiburg.de/~cziegler/BX/BX-CSV-Dump.zip", "BX-CSV-Dump.zip")
        delete_all_data_from_database()
        fill_books_table_with_csv(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data/BX-Books.csv'))
        fill_book_ratings_table_with_csv(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data/BX-Book-Ratings.csv'))
    return render(request, "Homepage/index.html")


def is_request_method_post(request_method):
    return True if request_method == 'POST' else False


def was_btn_pressed(btn_name, request):
    return True if (btn_name in request.POST) else False
