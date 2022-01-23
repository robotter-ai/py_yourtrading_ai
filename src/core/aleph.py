from dataclasses import dataclass, field, InitVar
from typing import Type, Optional, Union

import aleph_client.asynchronous as client
from aleph_client.chains.ethereum import get_fallback_account
from aleph_client.vm.cache import VmCache

import dacite
import dacite.dataclasses

from core.exceptions import PostTypeIsNoClassError, InvalidMessageTypeError

STD_CHANNEL = 'YOURTRADING_AI'
cache = VmCache()
FALLBACK_ACCOUNT = get_fallback_account()


@dataclass()
class AlephObject(object):
    id: str
    _ref: 'AlephRef' = field(init=False, default=None)

    @property
    def ref(self):
        return self._ref

    @ref.setter
    def ref(self, aleph_ref):
        if isinstance(aleph_ref, str):
            self._ref = AlephRef(aleph_ref)
        else:
            self._ref = aleph_ref

    async def refresh(self, ref=None):
        if ref:
            self.ref = ref
        self.__dict__.update((await self.ref.get()).__dict__)

    def as_dict(self):
        d = vars(self)
        del d['_ref']
        return d


@dataclass
class AlephRef:
    item_hash: str

    async def get(self) -> dict:
        return await client.get_posts(refs=[self.item_hash])


@dataclass
class Index(AlephObject):
    refs: dict
    datatype: Type[AlephObject]

    @property
    def items(self) -> {str: AlephObject}:
        return get_objects(self.datatype, self.refs.values())

    @property
    def is_root(self) -> bool:
        return self.datatype == type(self)


# noinspection PyArgumentList
async def post_objects_in_index(account, objs: [AlephObject], channel: str = STD_CHANNEL) -> Optional[Index]:
    if len(objs) == 0:
        return None

    name = type(objs[0]).__name__
    index = dacite.from_dict(Index, await cache.get(f'Index({name})'))
    if index is None:
        index = Index(items=[])
    for obj in objs:
        await post_or_amend_object(account, obj, channel)
        index.refs = {obj.id: obj.ref}
    resp = await client.create_post(account, index, post_type=f'Index({name})', channel=channel, ref=index.ref)
    index.ref = resp['item_hash']
    await cache.set(f'Index({name})', str(dict(index)))
    return index.ref


async def post_or_amend_object(obj: AlephObject, account=None, channel: str = STD_CHANNEL) -> AlephObject:
    if account is None:
        account = FALLBACK_ACCOUNT
    name = type(obj).__name__
    resp = await client.create_post(account, obj.__dict__, post_type=name, channel=channel, ref=obj.ref)
    obj.ref = resp['item_hash']
    return obj


async def get_all_objects_from_lookup(datatype: Type[AlephObject], channel: str = STD_CHANNEL) -> [AlephObject]:
    """
    Implements a caching and retrieval mechanism for objects stored on the Aleph chain,
    whose item hashes (refs) were bundled in an according Index message. A Index is a dict
    containing a describing and unique key, with a ref hash as value.
    :param datatype:
    :param channel:
    :return:
    """
    name = datatype.__name__
    objects = dacite.from_dict(datatype, await cache.get(name))
    if objects is None:
        lookup_resp = await client.get_posts(channels=[channel], types=[f'Index({name})'])
        refs = lookup_resp['posts'][0]['content'].values()
        objects_resp = await client.get_posts(refs=refs)
        objects = [dacite.from_dict(datatype, post['content']) for post in objects_resp]
        await cache.set(name, str(objects.__dict__))
    else:
        objects = [dacite.from_dict(datatype, data) for data in objects]

    return objects


async def get_object(ref: str, channel: str = None):
    """Retrieves a single object by its aleph item_hash.
    :param ref: Aleph item_hash
    :param channel: Channel in which to look for it."""
    channels = None if channel is None else [channel]
    resp = await client.get_posts(hashes=[ref], channels=channels)
    post = resp['posts'][0]
    try:
        print(globals())
        return dacite.from_dict(globals()[post['type']], post['content'])
    except KeyError:
        print(post)
        raise PostTypeIsNoClassError(post['content'])


async def get_objects(datatype: Type[AlephObject], refs: [str], channel: str = STD_CHANNEL) -> [AlephObject]:
    objects_resp = await client.get_posts(refs=refs, channels=[channel])
    objects = [dacite.from_dict(datatype, post['content']['content']) for post in objects_resp]
    return objects
