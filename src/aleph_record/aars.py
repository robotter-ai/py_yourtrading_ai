from pydantic import BaseModel
from typing import Type, TypeVar, Dict, ClassVar, List

import aleph_client.asynchronous as client
from aleph_client.chains.ethereum import get_fallback_account

FALLBACK_ACCOUNT = get_fallback_account()

T = TypeVar('T', bound='AlephRecord')


class AlephRecord(BaseModel):
    item_hash: str = None
    current_revision: int = None
    revision_hashes: List[str] = None
    indices: ClassVar[Dict[str, 'AlephIndex']] = {}

    def __repr__(self):
        return f'{type(self).__name__}({self.item_hash})'

    @property
    def content(self) -> Dict:
        """
        :return: content dictionary of the object, as it is to be stored on Aleph.
        """
        d = vars(self)
        del d['item_hash']
        del d['current_revision']
        del d['revision_hashes']
        del d['indices']
        return d

    async def update_revision_hashes(self: T):
        posts = await fetch_revisions(type(self), ref=self.item_hash)
        self.revision_hashes = [post['item_hash'] for post in posts]

    async def fetch_revision(self: T, rev_no: int = None, rev_hash: str = None) -> T:
        """
        Fetches a revision of the object by revision number (0 => original) or revision hash.
        :param rev_no: the revision number of the revision to fetch.
        :param rev_hash: the hash of the revision to fetch.
        """
        if rev_no is not None:
            if rev_no < 0:
                rev_no = len(self.revision_hashes) + rev_no
            if self.current_revision == rev_no:
                return self
            elif rev_no > len(self.revision_hashes):
                raise IndexError(f'No revision no. {rev_no} found for {self}')
            else:
                self.current_revision = rev_no
        elif rev_hash is not None:
            try:
                self.current_revision = self.revision_hashes.index(rev_hash)
            except ValueError:
                raise IndexError(f'{rev_hash} is not a revision of {self}')
        else:
            raise ValueError('Either rev or hash must be provided')

        # always fetch from aleph
        self.__dict__.update((await fetch_records(type(self), item_hashes=[self.item_hash]))[0].content)

        return self

    async def upsert(self):
        await post_or_amend_object(self)
        if self.current_revision == 0:
            [index.add_item(self) for index in self.indices.values()]

    async def forget(self):
        await forget_object(self)

    @classmethod
    def create(cls: Type[T], **kwargs) -> T:
        obj = cls(**kwargs)
        return obj.upsert()

    @classmethod
    def query(cls: Type[T], key: str, index: str = 'item_hash') -> List[T]:
        return cls.indices[index].fetch_by_key(key)

    @classmethod
    def add_index(cls: Type[T], index: 'AlephIndex') -> None:
        cls.indices[index.name] = index


class AlephIndex(AlephRecord):
    datatype: Type[AlephRecord]
    name: str
    hashmap: Dict[str, str] = {}

    async def fetch_items(self) -> List[AlephRecord]:
        return await fetch_records(self.datatype, list(set(self.hashmap.values())))

    async def fetch_by_key(self, key: str) -> AlephRecord:
        return (await fetch_records(self.datatype, [self.hashmap[key]]))[0]

    def add_item(self, item_hash: str):
        """
        Adds an item to the index. Intended to be overridden by subclasses.
        """
        self.hashmap[item_hash] = item_hash


async def post_or_amend_object(obj: T, account=None, channel: str = None):
    """
    Posts or amends an object to Aleph. If the object is already posted, it's ref is updated.
    :param obj: The object to post or amend.
    :param account: The account to post the object with. If None, will use the fallback account.
    :param channel: The channel to post the object to. If None, will use the TEST channel of the object.
    :return: The object, as it is now on Aleph.
    """
    if account is None:
        account = FALLBACK_ACCOUNT
    name = type(obj).__name__
    resp = await client.create_post(account, obj.content, post_type=name, channel=channel, ref=obj.item_hash)
    obj.revision_hashes.append(resp['item_hash'])
    obj.current_revision = len(obj.revision_hashes) - 1


async def forget_object(obj: T, account=None, channel: str = None):
    """
    Deletes an object from Aleph.
    :param obj: The object to delete.
    :param account: The account to delete the object with. If None, will use the fallback account.
    :param channel: The channel to delete the object from. If None, will use the TEST channel of the object.
    """
    if account is None:
        account = FALLBACK_ACCOUNT
    hashes = [obj.item_hash] + obj.revision_hashes
    await client.forget(account, hashes, reason=None, channel=channel)


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


async def fetch_revisions(datatype: Type[T],
                          ref: str,
                          channel: str = None,
                          owner: str = None) -> List[Dict]:
    """Retrieves posts of revisions of an object by its item_hash.
    :param datatype: The type of the objects to retrieve.
    :param ref: item_hash of the object, whose revisions to fetch.
    :param channel: Channel in which to look for it.
    :param owner: Account that owns the object."""
    channels = None if channel is None else [channel]
    owners = None if owner is None else [owner]
    return await client.get_posts(refs=[ref], channels=channels, types=[datatype.__name__], addresses=owners)
