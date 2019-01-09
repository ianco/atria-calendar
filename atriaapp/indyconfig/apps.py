from django.apps import AppConfig
from ctypes import *

import time

import json

import sys
from ctypes import *

from indy import anoncreds, crypto, did, ledger, pool, wallet
from indy.error import ErrorCode, IndyError

from django.conf import settings

from .indyutils import get_pool_genesis_txn_path, run_coroutine, PROTOCOL_VERSION


class IndyConfig(AppConfig):
    name = 'indyconfig'

    def ready(self):
        pg_dll = settings.INDY_CONFIG['storage_dll']
        pg_entrypoint = settings.INDY_CONFIG['storage_entrypoint']
        print('Loading {}'.format(pg_dll))
        stg_lib = CDLL(pg_dll)
        result = stg_lib[pg_entrypoint]()
        if result != 0:
            print('Error unable to load wallet storage {}'.format(result))
            raise AppError('Error unable to load wallet storage {}'.format(result))

        run_coroutine(run)
        time.sleep(1)  # FIXME waiting for libindy thread complete

        print("App is ready!!!")


async def run():
    print("Getting started -> started")

    pool_ = {
        'name': 'pool1'
    }
    print("Open Pool Ledger: {}".format(pool_['name']))
    pool_['genesis_txn_path'] = get_pool_genesis_txn_path(pool_['name'])
    print(pool_['genesis_txn_path'])
    pool_['config'] = json.dumps({"genesis_txn": str(pool_['genesis_txn_path'])})

    # Set protocol version 2 to work with Indy Node 1.4
    await pool.set_protocol_version(PROTOCOL_VERSION)

    try:
        await pool.create_pool_ledger_config(pool_['name'], pool_['config'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
            pass
    pool_['handle'] = await pool.open_pool_ledger(pool_['name'], None)
    print("Returned pool handle", pool_['handle'])

