from typing import Type, Optional

import aleph_client.asynchronous as client
from aleph_client.vm.cache import VmCache

from dacite import from_dict

from core.model import Coin, Source, Dataseries, DataseriesDesc, AlephObject, Index

STD_CHANNEL = 'YOURTRADING_AI'
cache = VmCache()


# noinspection PyArgumentList
async def post_objects_in_index(account, objs: [AlephObject], channel: str = STD_CHANNEL) -> Optional[Index]:
    if len(objs) == 0:
        return None

    name = type(objs[0]).__name__
    index = from_dict(Index, await cache.get(f'Index({name})'))
    if index is None:
        index = Index(items=[])
    for obj in objs:
        await post_or_amend_object(account, obj, channel)
        index.refs = {obj.id: obj.ref}
    resp = await client.create_post(account, index, post_type=f'Index({name})', channel=channel, ref=index.ref)
    index.ref = resp['item_hash']
    await cache.set(f'Index({name})', str(index.__dict__))
    return index.ref


async def post_or_amend_object(account, obj: AlephObject, channel: str = STD_CHANNEL) -> AlephObject:
    name = type(obj).__name__
    resp = await client.create_post(account, obj.__dict__, post_type=name, channel=channel, ref=obj.ref)
    obj.ref = resp['item_hash']
    return obj


async def get_all_objects_from_lookup(datatype: Type[T], channel: str = STD_CHANNEL) -> [AlephObject]:
    """
    Implements a caching and retrieval mechanism for objects stored on the Aleph chain,
    whose item hashes (refs) were bundled in an according Index message. A Index is a dict
    containing a describing and unique key, with a ref hash as value.
    :param datatype:
    :param channel:
    :return:
    """
    name = datatype.__name__
    objects = from_dict(datatype, await cache.get(name))
    if objects is None:
        lookup_resp = await client.get_posts(channels=[channel], types=[f'Index({name})'])
        refs = lookup_resp['posts'][0]['content'].values()
        objects_resp = await client.get_posts(refs=refs)
        objects = [from_dict(datatype, post['content']) for post in objects_resp]
        await cache.set(name, str(objects.__dict__))
    else:
        objects = [from_dict(datatype, data) for data in objects]

    return objects


async def get_objects(datatype: Type[AlephObject], refs: [str], channel: str = STD_CHANNEL):
    objects_resp = await client.get_posts(refs=refs, channels=[channel])
    objects = [from_dict(datatype, post['content']) for post in objects_resp]
    return objects


async def get_sources() -> [Source]:
    return get_all_objects_from_lookup(Source)


async def get_coins() -> [Coin]:
    return get_all_objects_from_lookup(Coin)


async def get_dataseries_descs(coin: Coin) -> [DataseriesDesc]:
    if coin:
        objects_resp = await client.get_posts(refs=coin.dataseriesDesc_ids)
        objects = [from_dict(DataseriesDesc, post['content']) for post in objects_resp]
        return objects
