import asyncio
import json
from os import environ
from pathlib import Path
from tempfile import gettempdir
from django.conf import settings

from indy import anoncreds, crypto, did, ledger, pool, wallet
from indy.error import ErrorCode, IndyError
from vcx.api.utils import vcx_agent_provision
from vcx.api.vcx_init import vcx_init_with_config


PROTOCOL_VERSION = 2


def path_home() -> Path:
    return Path.home().joinpath(".indy_client")


def get_pool_genesis_txn_path(pool_name):
    path_temp = Path(gettempdir()).joinpath("indy")
    path = path_temp.joinpath("{}.txn".format(pool_name))
    save_pool_genesis_txn_file(path)
    return path


# this is the genesis that connects to the default indy-sdk ledger, checkout indy-sdk and run:
#    docker build -f ci/indy-pool.dockerfile -t indy_pool .
#    docker run -itd -p 9701-9708:9701-9708 indy_pool
def pool_genesis_txn_data():
    pool_ip = environ.get("TEST_POOL_IP", "127.0.0.1")

    genesis_txn = "\n".join([
        '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node1","blskey":"4N8aUNHSgjQVgkpm8nhNEfDf6txHznoYREg9kirmJrkivgL4oSEimFF6nsQ6M41QvhM2Z33nves5vfSn9n1UwNFJBYtWVnHYMATn76vLuL3zU88KyeAYcHfsih3He6UHcXDxcaecHVz6jhCYz1P2UZn2bDVruL5wXpehgBfBaLKm3Ba","blskey_pop":"RahHYiCvoNCtPTrVtP7nMC5eTYrsUA8WjXbdhNc8debh1agE9bGiJxWBXYNFbnJXoXhWFMvyqhqhRoq737YQemH5ik9oL7R4NTTCz2LEZhkgLJzB3QRQqJyBNyv7acbdHrAT8nQ9UkLbaVL9NBpnWXBTw4LEMePaSHEw66RzPNdAX1","client_ip":"{}","client_port":9702,"node_ip":"{}","node_port":9701,"services":["VALIDATOR"]}},"dest":"Gw6pDLhcBcoQesN72qfotTgFa7cbuqZpkX3Xo6pLhPhv"}},"metadata":{{"from":"Th7MpTaRZVRYnPiabds81Y"}},"type":"0"}},"txnMetadata":{{"seqNo":1,"txnId":"fea82e10e894419fe2bea7d96296a6d46f50f93f9eeda954ec461b2ed2950b62"}},"ver":"1"}}'.format(
            pool_ip, pool_ip),
        '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node2","blskey":"37rAPpXVoxzKhz7d9gkUe52XuXryuLXoM6P6LbWDB7LSbG62Lsb33sfG7zqS8TK1MXwuCHj1FKNzVpsnafmqLG1vXN88rt38mNFs9TENzm4QHdBzsvCuoBnPH7rpYYDo9DZNJePaDvRvqJKByCabubJz3XXKbEeshzpz4Ma5QYpJqjk","blskey_pop":"Qr658mWZ2YC8JXGXwMDQTzuZCWF7NK9EwxphGmcBvCh6ybUuLxbG65nsX4JvD4SPNtkJ2w9ug1yLTj6fgmuDg41TgECXjLCij3RMsV8CwewBVgVN67wsA45DFWvqvLtu4rjNnE9JbdFTc1Z4WCPA3Xan44K1HoHAq9EVeaRYs8zoF5","client_ip":"{}","client_port":9704,"node_ip":"{}","node_port":9703,"services":["VALIDATOR"]}},"dest":"8ECVSk179mjsjKRLWiQtssMLgp6EPhWXtaYyStWPSGAb"}},"metadata":{{"from":"EbP4aYNeTHL6q385GuVpRV"}},"type":"0"}},"txnMetadata":{{"seqNo":2,"txnId":"1ac8aece2a18ced660fef8694b61aac3af08ba875ce3026a160acbc3a3af35fc"}},"ver":"1"}}'.format(
            pool_ip, pool_ip),
        '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node3","blskey":"3WFpdbg7C5cnLYZwFZevJqhubkFALBfCBBok15GdrKMUhUjGsk3jV6QKj6MZgEubF7oqCafxNdkm7eswgA4sdKTRc82tLGzZBd6vNqU8dupzup6uYUf32KTHTPQbuUM8Yk4QFXjEf2Usu2TJcNkdgpyeUSX42u5LqdDDpNSWUK5deC5","blskey_pop":"QwDeb2CkNSx6r8QC8vGQK3GRv7Yndn84TGNijX8YXHPiagXajyfTjoR87rXUu4G4QLk2cF8NNyqWiYMus1623dELWwx57rLCFqGh7N4ZRbGDRP4fnVcaKg1BcUxQ866Ven4gw8y4N56S5HzxXNBZtLYmhGHvDtk6PFkFwCvxYrNYjh","client_ip":"{}","client_port":9706,"node_ip":"{}","node_port":9705,"services":["VALIDATOR"]}},"dest":"DKVxG2fXXTU8yT5N7hGEbXB3dfdAnYv1JczDUHpmDxya"}},"metadata":{{"from":"4cU41vWW82ArfxJxHkzXPG"}},"type":"0"}},"txnMetadata":{{"seqNo":3,"txnId":"7e9f355dffa78ed24668f0e0e369fd8c224076571c51e2ea8be5f26479edebe4"}},"ver":"1"}}'.format(
            pool_ip, pool_ip),
        '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node4","blskey":"2zN3bHM1m4rLz54MJHYSwvqzPchYp8jkHswveCLAEJVcX6Mm1wHQD1SkPYMzUDTZvWvhuE6VNAkK3KxVeEmsanSmvjVkReDeBEMxeDaayjcZjFGPydyey1qxBHmTvAnBKoPydvuTAqx5f7YNNRAdeLmUi99gERUU7TD8KfAa6MpQ9bw","blskey_pop":"RPLagxaR5xdimFzwmzYnz4ZhWtYQEj8iR5ZU53T2gitPCyCHQneUn2Huc4oeLd2B2HzkGnjAff4hWTJT6C7qHYB1Mv2wU5iHHGFWkhnTX9WsEAbunJCV2qcaXScKj4tTfvdDKfLiVuU2av6hbsMztirRze7LvYBkRHV3tGwyCptsrP","client_ip":"{}","client_port":9708,"node_ip":"{}","node_port":9707,"services":["VALIDATOR"]}},"dest":"4PS3EDQ3dW1tci1Bp6543CfuuebjFrg36kLAUcskGfaA"}},"metadata":{{"from":"TWwCRQRZ2ZHMJFn9TzLp7W"}},"type":"0"}},"txnMetadata":{{"seqNo":4,"txnId":"aa5e817d7cc626170eca175822029339a444eb0ee8f0bd20d3b0b76e566fb008"}},"ver":"1"}}'.format(
            pool_ip, pool_ip)
    ])

    f = open("/tmp/atria-genesis.txt", "w+")
    f.write(genesis_txn)
    f.close()

    return genesis_txn


def save_pool_genesis_txn_file(path):
    data = pool_genesis_txn_data()

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(path), "w+") as f:
        f.writelines(data)


def initialize_and_provision_vcx(wallet_name, raw_password, institution_name, institution_logo_url='http://robohash.org/456'):
    provisionConfig = {
        'agency_url': settings.INDY_CONFIG['vcx_agency_url'],
        'agency_did': settings.INDY_CONFIG['vcx_agency_did'],
        'agency_verkey': settings.INDY_CONFIG['vcx_agency_verkey'],
        'wallet_type': 'postgres_storage',
        'wallet_name': wallet_name,
        'wallet_key': raw_password,
        'storage_config': json.dumps(settings.INDY_CONFIG['storage_config']),
        'storage_credentials': json.dumps(settings.INDY_CONFIG['storage_credentials']),
        'payment_method': settings.INDY_CONFIG['vcx_payment_method'],
        'enterprise_seed': settings.INDY_CONFIG['vcx_enterprise_seed']
    }
    
    print(" >>> Provision an agent and wallet, get back configuration details")
    try:
        provisionConfig_json = json.dumps(provisionConfig)
        print(provisionConfig_json)
        config = run_coroutine_with_args(vcx_agent_provision, provisionConfig_json)
    except:
        raise

    config = json.loads(config)

    # Set some additional configuration options specific to alice
    config['institution_name'] = institution_name
    config['institution_logo_url'] = institution_logo_url
    config['genesis_path'] = settings.INDY_CONFIG['vcx_genesis_path']

    print(" >>> Initialize libvcx with new configuration for", institution_name)
    try:
        config_json = json.dumps(config)
        print(config_json)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    print(" >>> Done!!!")


def create_wallet(wallet_name, raw_password):
    wallet_config_json = wallet_config(wallet_name)
    wallet_credentials_json = wallet_credentials(raw_password)
    try:
        run_coroutine_with_args(wallet.create_wallet, wallet_config_json, wallet_credentials_json)
    except IndyError as ex:
        if ex.error_code == ErrorCode.WalletAlreadyExistsError:
            pass


def delete_wallet(wallet_name, raw_password):
    # TODO
    pass


def open_wallet(wallet_name, raw_password):
    wallet_config_json = wallet_config(wallet_name)
    wallet_credentials_json = wallet_credentials(raw_password)
    wallet_handle = run_coroutine_with_args(wallet.open_wallet, wallet_config_json, wallet_credentials_json)
    return wallet_handle


def close_wallet(wallet_handle):
    wallet_handle = run_coroutine_with_args(wallet.close_wallet, wallet_handle)


def get_wallet_name(username):
    wallet_name = username.replace("@", "_")
    wallet_name = wallet_name.replace(".", "_")
    return 'i_{}'.format(wallet_name).lower()


# assume org name is something like an email
def get_org_wallet_name(orgname):
    wallet_name = orgname.replace("@", "_")
    wallet_name = wallet_name.replace(".", "_")
    wallet_name = wallet_name.replace(" ", "_")
    return 'o_{}'.format(wallet_name).lower()


def wallet_config(wallet_name):
    storage_config = settings.INDY_CONFIG['storage_config']
    wallet_config = settings.INDY_CONFIG['wallet_config']
    wallet_config['id'] = wallet_name
    wallet_config['storage_config'] = storage_config
    wallet_config_json = json.dumps(wallet_config)
    return wallet_config_json


def wallet_credentials(raw_password):
    storage_credentials = settings.INDY_CONFIG['storage_credentials']
    wallet_credentials = settings.INDY_CONFIG['wallet_credentials']
    wallet_credentials['key'] = raw_password
    wallet_credentials['storage_credentials'] = storage_credentials
    wallet_credentials_json = json.dumps(wallet_credentials)
    return wallet_credentials_json


def run_coroutine(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coroutine())
    finally:
        loop.close()


def run_coroutine_with_args(coroutine, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args))
    finally:
        loop.close()

