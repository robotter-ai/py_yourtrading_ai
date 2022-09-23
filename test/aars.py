import asyncio
from typing import List

from src.aars import Record, Index, AlreadyForgottenError
import pytest


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class Book(Record):
    title: str
    author: str


class Library(Record):
    name: str
    books: List[Book]


@pytest.mark.asyncio
async def test_store_and_index():
    Index(Book, 'title')
    new_book = await Book.create(title='Atlas Shrugged', author='Ayn Rand')
    assert new_book.title == 'Atlas Shrugged'
    assert new_book.author == 'Ayn Rand'
    fetched_book = (await Book.query(title='Atlas Shrugged'))[0]
    assert new_book == fetched_book


@pytest.mark.asyncio
async def test_multi_index():
    Index(Book, ['title', 'author'])
    new_book = await Book.create(title='Lila', author='Robert M. Pirsig')
    fetched_book = (await Book.query(title='Lila', author='Robert M. Pirsig'))[0]
    assert new_book == fetched_book


@pytest.mark.asyncio
async def test_fetch_all():
    books = await Book.fetch_all()
    assert len(books) > 0


@pytest.mark.asyncio
async def test_amending_record():
    book = await Book.create(title='Neurodancer', author='William Gibson')
    book.title = 'Neuromancer'
    book = await book.upsert()
    assert book.title == 'Neuromancer'
    assert len(book.revision_hashes) == 2
    assert book.current_revision == 1
    assert book.revision_hashes[0] == book.item_hash
    assert book.revision_hashes[1] != book.item_hash


@pytest.mark.asyncio
async def test_store_and_index_record_of_records():
    Index(Library, on='name')
    books = await asyncio.gather(
        Book.create(title='Atlas Shrugged', author='Ayn Rand'),
        Book.create(title='The Martian', author='Andy Weir')
    )
    new_library = await Library.create(name='The Library', books=books)
    fetched_library = (await Library.query(name='The Library'))[0]
    assert new_library == fetched_library


@pytest.mark.asyncio
async def test_forget_object():
    forgettable_book = await Book.create(title="The Forgotten Book", author="Mechthild Gläser")  # I'm sorry.
    await forgettable_book.forget()
    assert forgettable_book.forgotten is True
    assert len(await Book.get(forgettable_book.item_hash)) == 0
    with pytest.raises(AlreadyForgottenError):
        await forgettable_book.forget()
