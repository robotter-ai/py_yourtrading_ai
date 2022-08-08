from pydantic import BaseModel
from typing import Type, Optional, TypeVar, Set, Union, Dict, ClassVar, List

import aleph_client.asynchronous as client
from aleph_client.chains.ethereum import get_fallback_account

from core.exceptions import PostTypeIsNoClassError

FALLBACK_ACCOUNT = get_fallback_account()

T = TypeVar('T', bound='AlephRecord')


class AlephRecord(BaseModel):
    id: Union[str, int] = None
    item_hash: str = None
    current_revision: str = None
    revs: [str] = None
    indices: ClassVar[Dict[str, 'AlephIndex']] = {}

    async def refresh(self: T, rev: int = None) -> T:
        if rev:
            if rev == 0:
                if self.current_revision == self.item_hash:
                    return self
                else:
                    self.__dict__.update((await fetch_records(type(self), [self.item_hash]))[0].__dict__)
            if rev > len(self.revs):
                self.revs = [post['item_hash'] for post in (await client.get_posts(refs=[self.item_hash]))['posts']]
            try:
                self.item_hash = self.revs[-rev]
            except IndexError:
                raise IndexError(f'No revision {rev} found for {self.item_hash}')
            self.current_revision = self.revs[]
        self.__dict__.update((await self.ref.fetch()).__dict__)
        return self

    async def upsert(self) -> T:
        return await post_or_amend_object(self)

    def as_record(self) -> Dict:
        """
        :return: a data dictionary of the object, as it is to be stored on Aleph.
        """
        d = vars(self)
        del d['_ref']
        del d['indices']
        return d

    @classmethod
    def as_schema(cls) -> Dict:
        """
        :return: a dictionary representation of the type.
        """
        return vars(cls)

    @classmethod
    def get_by_index(cls: Type[T], index: str, key: str) -> T:
        return cls.indices[index].get_by_key(key)


class DatabaseSchema(AlephRecord):
    channel: str
    owner: str
    types: Set[Type[AlephRecord]]
    version: int = 1

    @classmethod
    async def fetch_schema(cls, channel: str, owner: str, version: int = None) -> 'DatabaseSchema':
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

    async def upsert(self: T) -> T:
        """Upgrades and uploads the schema to the next version."""
        schema = await self.fetch_schema(channel=self.channel, owner=self.owner)
        if schema is not None:
            self.version = schema.version + 1
        return await post_or_amend_object(self, account=self.owner, channel=self.channel)

    def add_type(self, type_: Type[AlephRecord]):
        if type_ in self.types():
            return
        self.types[type_.__name__] = type_
        name = type_.__name__ + '_id'
        self.indices[name] = AlephIndex(datatype=type_, name=name)


class AlephIndex(AlephRecord):
    datatype: Type[AlephRecord]
    name: str
    hashmap: Dict[str, str] = {}

    @property
    async def items(self) -> List[AlephRecord]:
        return await fetch_records(self.datatype, list(self.hashmap.values()))

    async def get_by_key(self, value: str) -> AlephRecord:
        return (await fetch_records(self.datatype, [self.hashmap[value]]))[0]

    def add_item(self, key: str, item_hash: str):
        self.hashmap[key] = item_hash


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


async def fetch_records(datatype: Type[T],
                        item_hashes: List[str] = None,
                        channel: str = None,
                        owner: str = None) -> List[T]:
    """Retrieves posts as objects by its aleph item_hash.
    :param datatype: The type of the objects to retrieve.
    :param item_hashes: Aleph item_hashes of the objects to fetch.
    :param channel: Channel in which to look for it.
    :param owner: Account that owns the object."""
    channels = None if channel is None else [channel]
    owners = None if owner is None else [owner]
    if item_hashes is None and channels is None and owners is None:
        raise ValueError('At least one of item_hashes, channel, or owner must be specified')
    objects_resp = await client.get_posts(hashes=item_hashes, channels=channels, types=[datatype.__name__],
                                          addresses=owners)
    objects = [datatype(**post['content']['content']) for post in objects_resp]
    return objects
