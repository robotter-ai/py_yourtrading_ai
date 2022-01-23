import asyncio

import core.aleph as al
import core.model as model


CHAN = 'DB_TEST'


def wrap_async(func):
    def func_caller(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))

    return func_caller


async def test_get_object():
    obj = model.Source("test", url="http://test.club")
    await al.post_or_amend_object(obj)
    assert obj.ref

    fetched = await al.get_object(obj.ref.item_hash)
    assert obj == fetched
    print(obj)
    print(vars(obj))
    return obj

test = wrap_async(test_get_object)

test()