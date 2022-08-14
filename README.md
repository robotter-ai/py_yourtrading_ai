# AARS: Aleph Active Record SDK

AARS's goal is to provide simple guardrails for the creation of document databases, based on Aleph's decentralized storage API. It provides tools for modelling, creating and managing decentralized databases, and a set of extensions for the [Aleph Python SDK](https://github.com/aleph-im/aleph-client).

You can create a model of your planned database by using the `AlephRecord` class.

```python
from src.aars import Record


class Book(Record):
    title: str
    author: str


new_book = Book.create(title='Atlas Shrugged', author='Ayn Rand')
Book.query()
```

## TODO
[x]