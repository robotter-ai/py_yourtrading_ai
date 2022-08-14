# AARS: Aleph Active Record SDK

AARS's goal is to provide simple guardrails for the creation of document databases, based on Aleph's decentralized storage API. It provides tools for modelling, creating and managing decentralized databases, and a set of extensions for the [Aleph Python SDK](https://github.com/aleph-im/aleph-client).

You can create a model of your planned database by using the `AlephRecord` class.

```python
from src.aleph_record import AlephRecord

class Book(AlephRecord):
    title: str
    author: str
```

## TODO
[x]