import os
import requests
import zipfile
import pandas as pd
from lxml import html
import html as html_std

from django.db.transaction import atomic
from django.http import HttpResponse
from RootDir.models import Book, BookRating

# vars
books_to_import = []
book_ratings_to_import = []
books_incorrect_number_of_cols = []


# This function downloads the file from given link and saves it to data folder
# params: url - link that leads to the file, filename - name of the file
def download_file_from_url(url, filename):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = BASE_DIR + '/data/'
    r = requests.get(url, stream=True)
    with open(filepath + filename, "wb") as zip:
        for chunk in r.iter_content(chunk_size=1024):
            zip.write(chunk)
    unzip(filepath, filename)
    print('Download of the file successful.')


# This function unzips the given zip file (in the same folder)
# params: filepath - folder where the zip file is, filename - name of the file
def unzip(filepath, filename):
    with zipfile.ZipFile(filepath + filename) as zip_ref:
        zip_ref.extractall(filepath)


@atomic
def fill_book_ratings_table_with_csv(filepath):
    with open(filepath, 'r') as inputFile:
        reader = pd.read_csv(inputFile, encoding='cp1251', sep=';', error_bad_lines=False)
        iterate_through_book_ratings_csv(reader)

        try:
            BookRating.objects.bulk_create(book_ratings_to_import)
        except Exception as e:
            print('Import to table Books was not successful.')
            return HttpResponse(e)
        print("Import of ratings went well")
        return HttpResponse("Your file has been successfully uploaded")


# This function goes through the given csv file, checks the data and performs ORM
# params: reader - loaded csv file
def iterate_through_book_ratings_csv(reader):
    reader = reader[reader['Book-Rating'] != 0]  # drop those with 0 rating
    pattern_keep = r'(^(?!0000)\d{5,}X?$)'  # Regex to filter out some nonsense data like ґ3499128624 or VENAFRO001
    filter = reader['ISBN'].str.contains(pattern_keep)
    reader = reader[filter]  # Leave only those that matches filter, for debug
    # filtered_out = reader[~filter] # For debug and to see what was filtered out

    for row in reader.iterrows():
        user_id = row[1][0]
        book_isbn = row[1][1]
        book_rating = row[1][2]

        book_ratings_to_import.append(BookRating(user_id=user_id,
                                                 book_isbn=book_isbn,
                                                 book_rating=book_rating))


# This function fills Book table with data from given csv file
# params: filepath - path to the csv file
@atomic  # Commit all or nothing
def fill_books_table_with_csv(filepath):
    with open(filepath, 'r') as inputFile:
        reader = pd.read_csv(inputFile, encoding='cp1251', sep=';', error_bad_lines=False)
        reader = reader.drop_duplicates(subset='Book-Title', keep='first')
        iterate_through_books_csv(reader)
        try:
            Book.objects.bulk_create(books_to_import)
        except Exception as e:
            print('Import to table Books was not successful.')
            return HttpResponse(e)
        print("Import of books went well")
        return HttpResponse("Your file has been successfully uploaded")


# This function drops all data in table Book and BookRating
def delete_all_data_from_database():
    Book.objects.all().delete()
    BookRating.objects.all().delete()
    print('All data from database were dropped.')


# This function goes through the given csv file, checks the data and performs ORM
# params: reader - loaded csv file
def iterate_through_books_csv(reader):
    books_with_incorrect_format = []

    # Drop the columns with links to book covers
    del reader['Image-URL-S']
    del reader['Image-URL-M']
    del reader['Image-URL-L']

    for row in reader.iterrows():
        book_isbn = row[1][0]
        book_title = strip_html(html_std.unescape(remove_non_ascii(row[1][1])))
        book_author = remove_non_ascii(row[1][2])
        book_year_pub = 9999  # since some years have 0, set default value to 9999
        book_publisher = html_std.unescape(remove_non_ascii(row[1][4]))

        # Some checks based on observation
        if str(book_author).isdigit():
            books_with_incorrect_format.append(row)
            continue
        if row[1][3] != 0 and isinstance(row[1][3], int):
            book_year_pub = int((row[1][3]))
        if (isinstance(row[1][4], str)):
            if row[1][4].isnumeric():
                book_publisher = "IncorrectValue"
        else:
            books_with_incorrect_format.append(row)
            continue
        books_to_import.append(Book(book_isbn=book_isbn,
                                    book_title=book_title,
                                    book_author=book_author,
                                    book_year_pub=book_year_pub,
                                    book_publisher=book_publisher))


# This function checks whether the current row has data in all columns
# params: current_row_len - how many items is in the current row, expected_num_of_cols - how many we expect
# returns True if number of columns is not ok, else False
def check_num_of_cols(current_row_len, expected_num_of_cols):
    return True if current_row_len != expected_num_of_cols else False


# This function removes non ascii chars
# params: string where it is desired to remove non ascii chars
# returns string without non ascii chars
def remove_non_ascii(s):
    return "".join(c for c in str(s) if ord(c) < 128)


# This function strips html tags from the string
# params: string to strip
# returns stripped string
def strip_html(s):
    return str(html.fromstring(s).text_content())

# This function calculates the correlation table
# params: book for which the correlation table is desired
# returns: top 10 correlations in list
def calculate_correlation_table(book):
    rating_for_this_book = pd.DataFrame(
        BookRating.objects.values_list('id', 'user_id', 'book_isbn', 'book_rating').filter(book_isbn=book.book_isbn))

    user_ids_of_those_who_rated_this_book = rating_for_this_book[1].tolist()

    all_of_their_ratings = pd.DataFrame(
        BookRating.objects.values_list().filter(user_id__in=user_ids_of_those_who_rated_this_book))

    isbn_of_all_books_they_rated = all_of_their_ratings[2].tolist()

    all_books_they_rated = pd.DataFrame(Book.objects.values_list().filter(book_isbn__in=isbn_of_all_books_they_rated))

    merged_dataset_ratings_and_books = pd.merge(all_of_their_ratings, all_books_they_rated, on=2)  # column 2 is ISBN
    merged_dataset_ratings_and_books.columns = ['id_leva', 'user_id', 'book_isbn', 'book_rating', 'id_prava', 'book_title', 'book_author', 'book_year_pub', 'book_publisher']
    merged_dataset_ratings_and_books_lowercase = merged_dataset_ratings_and_books.apply(lambda x: x.str.lower() if (x.dtype == 'object') else x)

    # Number of ratings per other books in dataset
    number_of_rating_per_book = merged_dataset_ratings_and_books_lowercase.groupby(['book_title']).agg('count').reset_index()

    # select only books which have actually higher number of ratings than threshold
    books_to_compare = number_of_rating_per_book['book_title'][number_of_rating_per_book['user_id'] >= 8]
    books_to_compare = books_to_compare.tolist()

    ratings_data_raw = merged_dataset_ratings_and_books_lowercase[['user_id', 'book_rating', 'book_title']][merged_dataset_ratings_and_books_lowercase['book_title'].isin(books_to_compare)]

    # group by User and Book and compute mean
    ratings_data_raw_nodup = ratings_data_raw.groupby(['user_id', 'book_title'])['book_rating'].mean()

    # reset index to see User-ID in every row
    ratings_data_raw_nodup = ratings_data_raw_nodup.to_frame().reset_index()

    dataset_for_corr = ratings_data_raw_nodup.pivot(index='user_id', columns='book_title', values='book_rating')

    result_list = []

    # Take out the selected book from correlation dataframe
    dataset_of_other_books = dataset_for_corr.copy(deep=False)
    dataset_of_other_books.drop([book.book_title.lower()], axis=1, inplace=True)

    # empty lists
    book_titles = []
    correlations = []
    avgrating = []

    # corr computation
    for book_title in list(dataset_of_other_books.columns.values):
        book_titles.append(book_title)
        correlations.append(dataset_for_corr[book.book_title.lower()].corr(dataset_of_other_books[book_title]))
        tab = (ratings_data_raw[ratings_data_raw['book_title'] == book_title].groupby(
            ratings_data_raw['book_title']).mean())
        avgrating.append(tab['book_rating'].min())
    # final dataframe of all correlation of each book
    correlation_dataframe = pd.DataFrame(list(zip(book_titles, correlations, avgrating)), columns=['book', 'corr', 'avg_rating'])

    # top 10 books with highest corr
    result_list.append(correlation_dataframe.sort_values('corr', ascending=False).head(10))
    correlation_table = result_list[0]

    return correlation_table
