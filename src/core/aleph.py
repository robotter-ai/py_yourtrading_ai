from dataclasses import dataclass, field
from typing import Type, Optional, TypeVar, Set, Union, Dict, ClassVar

import aleph_client.asynchronous as client
from aleph_client.chains.ethereum import get_fallback_account
from aleph_client.vm.cache import VmCache

import dacite
import dacite.dataclasses

from core.exceptions import PostTypeIsNoClassError

STD_CHANNEL = 'CRYPTODATADOWNLOAD'
cache = VmCache()
FALLBACK_ACCOUNT = get_fallback_account()


T = TypeVar('T', bound='AlephRecord')


@dataclass
class AlephRef:
    item_hash: str

    async def fetch(self) -> Dict:
        return await client.get_posts(refs=[self.item_hash])


@dataclass()
class AlephRecord:
    id: Union[str, int] = field(init=False)
    _ref: 'AlephRef' = field(init=False, default=None)
    indices: ClassVar[Dict[str, 'AlephIndex']] = {}

    @property
    def ref(self) -> 'AlephRef':
        return self._ref

    @ref.setter
    def ref(self, aleph_ref):
        if isinstance(aleph_ref, str):
            self._ref = AlephRef(aleph_ref)
        else:
            self._ref = aleph_ref

    async def refresh(self: T, ref=None) -> T:
        if ref:
            self.ref = ref
        self.__dict__.update((await self.ref.fetch()).__dict__)
        return self

    async def upsert(self) -> T:
        return await post_or_amend_object(self)

    def as_dict(self) -> Dict:
        d = vars(self)
        del d['_ref']
        del d['indices']
        return d

    @classmethod
    def from_dict(cls: Type[T], d) -> T:
        return dacite.from_dict(cls, d)

    @classmethod
    def get_by_index(cls, index_name: str, index_value: str) -> T:
        return cls.indices[index_name].get_by_key(index_value)


@dataclass()
class AARSSchema(AlephRecord):
    channel: str
    owner: str
    types: Set[Type[AlephRecord]]
    version: int = 1

    @classmethod
    async def fetch_schema(cls, channel: str, owner: str, version: int = None) -> 'AARSSchema':
        """
        Fetches a schema from Aleph, which can be used to access active records.
        :param channel: The channel to fetch from
        :param owner: Address of the owner of the schema. It must be supplemented, as anyone can upload a schema for your channel.
        :param version: The version of the schema to fetch. If None, will fetch the latest
        :return: Instance of AARSSchema
        """
        schemas = (await fetch_records(datatype=cls, channel=channel, owner=owner))
        if version is None:
            schemas.sort(key=lambda x: x.version)
            return schemas[-1]
        else:
            return next(filter(lambda x: x.version == version, schemas), None)

    async def upgrade(self):
        """
        Upgrades and uploads the schema to the next version.
        :return:
        """
        self.version = (await self.fetch_schema(channel=self.channel, owner=self.owner)).version + 1
        await post_or_amend_object(self, account=self.owner, channel=self.channel)


@dataclass
class AlephIndex(AlephRecord):
    datatype: Type[AlephRecord]
    refs: Dict[str, AlephRef] = field(init=False, default_factory=dict)

    @property
    async def items(self) -> {str: AlephRecord}:
        return await fetch_records(self.datatype, self.refs.values())

    async def get_by_key(self, value: str) -> AlephRecord:
        return self.datatype.from_dict(await self.refs[value].fetch())


async def post_objects_in_index(account, objs: [T], channel: str = STD_CHANNEL) -> Optional[AlephIndex]:
    if len(objs) == 0:
        return None

    name = type(objs[0]).__name__
    index = dacite.from_dict(AlephIndex, await cache.get(f'Index({name})'))
    if index is None:
        index = AlephIndex(keys=objs[0], refs={}, datatype=objs[0].__class__)
    for obj in objs:
        await post_or_amend_object(account, obj, channel)
        index.refs = {obj.id: obj.ref}
    resp = await client.create_post(account, index, post_type=f'Index({name})', channel=channel, ref=index.ref)
    index.ref = resp['item_hash']
    await cache.set(f'Index({name})', str(dict(index)))
    return index.ref


async def post_or_amend_object(obj: T, account=None, channel: str = STD_CHANNEL) -> T:
    """
    Posts or amends an object to Aleph. If the object is already posted, it's ref is updated.
    :param obj:
    :param account:
    :param channel:
    :return:
    """
    if account is None:
        account = FALLBACK_ACCOUNT
    name = type(obj).__name__
    resp = await client.create_post(account, obj.__dict__, post_type=name, channel=channel, ref=obj.ref)
    obj.ref = resp['item_hash']
    return obj


async def get_all_objects_from_lookup(datatype: Type[T], channel: str = STD_CHANNEL) -> [T]:
    """
    Implements a caching and retrieval mechanism for objects stored on the Aleph chain,
    whose item hashes (refs) were bundled in an according Index message. An Index is a dict
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
        objects = [datatype.from_dict(data) for data in objects]

    return objects


async def fetch_record(ref: str, channel: str = None, owner: str = None) -> T:
    """Retrieves a single object by its aleph item_hash.
    :param ref: Aleph item_hash
    :param channel: Channel in which to look for it.
    :param owner: Account that owns the object."""
    channels = None if channel is None else [channel]
    owners = None if owner is None else [owner]
    resp = await client.get_posts(hashes=[ref], channels=channels, addresses=owners)
    post = resp['posts'][0]
    try:
        print(globals())
        return dacite.from_dict(globals()[post['type']], post['content'])
    except KeyError:
        print(post)
        raise PostTypeIsNoClassError(post['content'])


async def fetch_records(
        datatype: Type[T],
        refs: [str] = None,
        channel: str = None,
        owner: str = None
) -> [T]:
    channels = None if channel is None else [channel]
    owners = None if owner is None else [owner]
    objects_resp = await client.get_posts(refs=refs, channels=channels, types=[datatype.__name__], addresses=owners)
    objects = [dacite.from_dict(datatype, post['content']['content']) for post in objects_resp]
    return objects
