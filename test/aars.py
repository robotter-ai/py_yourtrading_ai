from src.aars import Record, Index
import pytest


class Book(Record):
    title: str
    author: str


@pytest.mark.asyncio
async def test_store_and_index():
    Index(Book, 'title')
    new_book = await Book.create(title='Atlas Shrugged', author='Ayn Rand')
    print(new_book)
    fetched_book = (await Book.query('Atlas Shrugged', 'Book.title'))[0]
    print(fetched_book)
    assert new_book == fetched_book


@pytest.mark.asyncio
async def test_fetch_all():
    books = await Book.fetch_all()
    assert len(books) > 0
