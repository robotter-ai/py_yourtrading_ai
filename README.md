# ARS: Aleph Active Record SDK

AARS's goal is to provide simple guardrails for the creation of document databases, based on Aleph's decentralized storage API. It provides tools for modelling, creating and managing decentralized databases, and a set of extensions for the [Aleph Python SDK](https://github.com/aleph-im/aleph-client).

You can create a model of your planned database by using the `AlephRecord` class.

```python
from src.aars import Record, Index

class Book(Record):
    title: str
    author: str

# create and add an index for the book title
Index(Book, 'title')

# create & upload a book
new_book = await Book.create(title='Atlas Shrugged', author='Ayn Rand')

# assert the index works
assert new_book == (await Book.query(title='Atlas Shrugged'))[0]
```


## ToDo:
- [x] Basic CRUD operations
- [x] Basic indexing operations
  - [x] Single-key indexing 
  - [x] Multi-key indexing
- [ ] (IN PROGRESS) Basic search/filtering operations
- [ ] Handle pagination
- [ ] Encapsulate Aleph SDK as class
- [ ] Local caching
- [ ] (IN PROGRESS) Add tests
- [ ] (IN PROGRESS) Add documentation
