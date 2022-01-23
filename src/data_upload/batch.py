import asyncio
import io
import ssl

import aiohttp
import aleph_client.asynchronous
import certifi
import pandas as pd

from data_upload.data_utils import clean_time_duplicates


def get_download_url(symbol, interval="hourly"):
    if interval == "daily":
        interval = "d"
    elif interval == "hourly":
        interval = "1h"
    elif interval == "minutely":
        interval = "minute"
    return f"https://www.cryptodatadownload.com/cdd/Binance_{symbol}USDT_{interval}.csv"


# Code for all async
# responses = asyncio.get_event_loop().run_until_complete(post_all_to_aleph_async(currencies))
# hashes = [resp['item_hash'] for resp in responses]
async def post_to_aleph_async(account, client, symbol, interval="hourly"):
    url = get_download_url(symbol, interval)
    sslcontext = ssl.create_default_context(cafile=certifi.where())
    async with client.get(url, ssl=sslcontext) as response:
        with io.StringIO(await response.text()) as text_io:
            df = pd.read_csv(text_io, header=1)
            clean_time_duplicates(df)
            print(df.describe())
            return await aleph_client.asynchronous.create_post(account=account,
                                                               post_content=df.to_dict(),
                                                               post_type="ohlcv_timeseries",
                                                               channel="TEST-CRYPTODATADOWNLOAD")


async def post_all_to_aleph_async(account, symbols: list, interval="hourly"):
    async with aiohttp.ClientSession(trust_env=True, connector=aiohttp.TCPConnector(limit_per_host=4)) as client:
        futures = [post_to_aleph_async(account, client, symbol, interval) for symbol in symbols]
        return await asyncio.gather(*futures)


def post_to_aleph(account, url, amend_hash=None):
    df = pd.read_csv(url, header=1)
    print(df.describe())
    post_type = 'ohlcv_timeseries' if amend_hash is None else 'amend'
    return aleph_client.create_post(account=account,
                                    post_content=df.describe().to_dict(),
                                    post_type=post_type,
                                    channel="TEST-CRYPTODATADOWNLOAD",
                                    ref=amend_hash)


def post_all_to_aleph(account, symbols: list, amend_hashes=None, interval="hourly"):
    hashes = {}
    for symbol in symbols:
        url = get_download_url(symbol, interval)
        if amend_hashes:
            resp = post_to_aleph(account, url, amend_hashes[symbol])
            print(f"Amended {symbol}: {amend_hashes[symbol]}")
        else:
            resp = post_to_aleph(account, url)
            print(f"Posted {symbol}: {resp['item_hash']}")
        hashes[symbol] = resp['item_hash']
    return hashes

