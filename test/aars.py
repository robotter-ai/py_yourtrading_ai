from src.aars import Record, Index
import unittest


class Test(unittest.TestCase):
    class Book(Record):
        title: str
        author: str

    async def test_store_and_index(self):
        Index(Test.Book, 'title')
        new_book = await Test.Book.create(title='Atlas Shrugged', author='Ayn Rand')
        assert new_book == (await Test.Book.query('Atlas Shrugged', 'Book.title'))[0]


if __name__ == '__main__':
    unittest.main()
