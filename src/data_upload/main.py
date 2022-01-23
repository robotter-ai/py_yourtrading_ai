import asyncio
import ssl
import json
from typing import Union

import certifi
import pandas as pd

import aleph_client
import aleph_client.asynchronous
from aleph_client.chains.ethereum import get_fallback_account

from data_upload.batch import post_all_to_aleph_async
from data_upload.data_utils import save_to_file


def create_ssl_context(*args, **kwargs):
    kwargs['cafile'] = certifi.where()
    return ssl.create_default_context(*args, **kwargs)


pd.set_option('display.max_columns', None)

ssl._create_default_https_context = create_ssl_context

account = get_fallback_account()

currencies = ["BTC", "ETH", "LTC", "NEO", "BNB", "XRP", "LINK",
              "EOS", "TRX", "ETC", "XLM", "ZEC", "ADA", "QTUM",
              "DASH", "XMR", "BAT", "BTT", "ZEC", "USDC", "TUSD",
              "MATIC", "PAX", "CELR", "ONE", "DOT", "UNI", "ICP",
              "SOL", "VET", "FIL", "AAVE", "DAI", "MKR", "ICX",
              "CVC", "SC", "LRC"]


def get_lookup() -> Union[None, dict]:
    try:
        with open('lookup.txt', "r") as file:
            lookup_dict = json.loads(file.read())
    except OSError:
        return None

    return lookup_dict


def main():
    responses = asyncio.get_event_loop().run_until_complete(post_all_to_aleph_async(account, currencies))
    hashes = [resp['item_hash'] for resp in responses]
    save_to_file("aleph-response.txt", hashes)

    resp = aleph_client.create_post(account=account, post_content=hashes, post_type="lookup", channel="TEST-CRYPTODATADOWNLOAD")
    try:
        lookup_hash = {'lookup_hash': resp['item_hash'], 'post_type': json.loads(resp['item_content'])['type'],
                       'channel': resp['channel']}
        save_to_file("lookup_hash.txt", lookup_hash)
    except Exception:
        save_to_file("lookup.txt", resp)
    print(hashes)


if __name__ == '__main__':
    main()

