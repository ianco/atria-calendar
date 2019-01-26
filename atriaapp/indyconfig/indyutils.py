import asyncio
import json
from os import environ
from pathlib import Path
from tempfile import gettempdir
import random

from django.conf import settings

from indy import anoncreds, crypto, did, ledger, pool, wallet
from indy.error import ErrorCode, IndyError

from vcx.api.connection import Connection
from vcx.api.schema import Schema
from vcx.api.credential_def import CredentialDef
from vcx.api.credential import Credential
from vcx.state import State, ProofState
from vcx.api.disclosed_proof import DisclosedProof
from vcx.api.issuer_credential import IssuerCredential
from vcx.api.proof import Proof
from vcx.api.utils import vcx_agent_provision
from vcx.api.vcx_init import vcx_init_with_config
from vcx.common import shutdown

from .models import *


def vcx_provision_config(wallet_name, raw_password, institution_name, institution_logo_url='http://robohash.org/456'):
    provisionConfig = {
        'agency_url': settings.INDY_CONFIG['vcx_agency_url'],
        'agency_did': settings.INDY_CONFIG['vcx_agency_did'],
        'agency_verkey': settings.INDY_CONFIG['vcx_agency_verkey'],
        'pool_name': 'pool_' + wallet_name,
        'wallet_type': 'postgres_storage',
        'wallet_name': wallet_name,
        'wallet_key': raw_password,
        'storage_config': json.dumps(settings.INDY_CONFIG['storage_config']),
        'storage_credentials': json.dumps(settings.INDY_CONFIG['storage_credentials']),
        'payment_method': settings.INDY_CONFIG['vcx_payment_method'],
        'enterprise_seed': settings.INDY_CONFIG['vcx_enterprise_seed'],
    }

    provisionConfig['institution_name'] = institution_name
    provisionConfig['institution_logo_url'] = institution_logo_url
    provisionConfig['genesis_path'] = settings.INDY_CONFIG['vcx_genesis_path']
    provisionConfig['pool_name'] = 'pool_' + wallet_name

    return provisionConfig

def initialize_and_provision_vcx(wallet_name, raw_password, institution_name, institution_logo_url='http://robohash.org/456'):
    provisionConfig = vcx_provision_config(wallet_name, raw_password, institution_name, institution_logo_url)

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
    config['pool_name'] = 'pool_' + wallet_name

    print(" >>> Initialize libvcx with new configuration for", institution_name)
    try:
        config_json = json.dumps(config)
        print(config_json)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    print(" >>> Shutdown vcx (for now)")
    try:
        shutdown(False)
    except:
        raise

    print(" >>> Done!!!")
    return json.dumps(config)


def send_connection_invitation(config, partner_name):
    print(" >>> Initialize libvcx with new configuration for a connection to", partner_name)
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and generate invitation
    try:
        connection_to_ = run_coroutine_with_args(Connection.create, partner_name)
        run_coroutine_with_args(connection_to_.connect, '{"use_public_did": true}')
        run_coroutine(connection_to_.update_state)
        invite_details = run_coroutine_with_args(connection_to_.invite_details, False)

        connection_data = run_coroutine(connection_to_.serialize)
        connection_to_.release()
        connection_to_ = None
    except:
        raise

    print(" >>> Shutdown vcx (for now)")
    try:
        shutdown(False)
    except:
        raise

    print(" >>> Done!!!")
    return connection_data, invite_details


def send_connection_confirmation(config, partner_name, invite_details):
    print(" >>> Initialize libvcx with configuration")
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and generate invitation
    try:
        invite_details_json = json.dumps(invite_details)
        connection_from_ = run_coroutine_with_args(Connection.create_with_details, partner_name, invite_details_json)
        run_coroutine_with_args(connection_from_.connect, '{"use_public_did": true}')
        run_coroutine(connection_from_.update_state)

        connection_data = run_coroutine(connection_from_.serialize)
        connection_from_.release()
        connection_from_ = None
    except:
        raise

    print(" >>> Shutdown vcx (for now)")
    try:
        shutdown(False)
    except:
        raise

    print(" >>> Done!!!")
    return connection_data


def check_connection_status(config, connection_data):
    print(" >>> Initialize libvcx with configuration")
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and check status
    try:
        connection_to_ = run_coroutine_with_args(Connection.deserialize, connection_data)
        run_coroutine(connection_to_.update_state)
        connection_state = run_coroutine(connection_to_.get_state)
        if connection_state == State.Accepted:
            return_state = 'Active'
        else:
            return_state = 'Sent'

        connection_data = run_coroutine(connection_to_.serialize)
        connection_to_.release()
        connection_to_ = None
    except:
        raise

    print(" >>> Shutdown vcx (for now)")
    try:
        shutdown(False)
    except:
        raise

    print(" >>> Done!!!")
    return connection_data, return_state


# TODO for now just create a random schema and creddef
def create_schema_and_creddef(wallet, config, schema_name, creddef_name):
    print(" >>> Initialize libvcx with configuration")
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    try:
        schema_attrs = ['name', 'date', 'degree']
        version = format("%d.%d.%d" % (random.randint(1, 101), random.randint(1, 101), random.randint(1, 101)))
        schema = run_coroutine_with_args(Schema.create, 'schema_uuid', schema_name, version, schema_attrs, 0)
        schema_id = run_coroutine(schema.get_schema_id)
        schema_data = run_coroutine(schema.serialize)

        indy_schema = IndySchema(
                            ledger_schema_id = schema_id,
                            schema_name = schema_name,
                            schema_version = version,
                            schema = schema_data,
                            schema_data = json.dumps(schema_attrs)
                            )
        indy_schema.save()

        creddef_template = {
                    'name': '',
                    'date': '',
                    'degree': '',
                    }
        cred_def = run_coroutine_with_args(CredentialDef.create, 'credef_uuid', creddef_name, schema_id, 0)
        cred_def_handle = cred_def.handle
        cred_def_id = run_coroutine(cred_def.get_cred_def_id)
        creddef_data = run_coroutine(cred_def.serialize)

        indy_creddef = IndyCredentialDefinition(
                            ledger_creddef_id = cred_def_id,
                            ledger_schema = indy_schema,
                            wallet_name = wallet,
                            creddef_name = creddef_name,
                            creddef_handle = cred_def_handle,
                            creddef_template = json.dumps(creddef_template),
                            creddef_data = creddef_data
                            )
        indy_creddef.save()

    except:
        raise

    print(" >>> Shutdown vcx (for now)")
    try:
        shutdown(False)
    except:
        raise

    print(" >>> Done!!!")

    return (indy_schema, indy_creddef)


def handle_inbound_messages(my_wallet, config, my_connection):
    print(" >>> Initialize libvcx with configuration")
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    try:
        handled_count = 0
        connection_data = json.loads(my_connection.connection_data)
        connection_to_ = run_coroutine_with_args(Connection.deserialize, connection_data)

        print("Check for and receive offers")
        offers = run_coroutine_with_args(Credential.get_offers, connection_to_)
        for offer in offers:
            already_handled = VcxConversation.objects.filter(message_id=offer[0]['msg_ref_id']).all()
            if len(already_handled) == 0:
                save_offer = offer[0].copy()
                offer_data = json.dumps(save_offer)
                new_offer = VcxConversation(
                                    wallet_name = my_wallet,
                                    connection_partner_name = my_connection.partner_name,
                                    conversation_type = "CredentialOffer",
                                    message_id = save_offer['msg_ref_id'],
                                    status = 'Pending',
                                    conversation_data = offer_data
                                )
                print("Saving received offer to DB")
                new_offer.save()
                handled_count = handled_count + 1

        print("Check for and handle proof requests")
        requests = run_coroutine_with_args(DisclosedProof.get_requests, connection_to_)
        for request in requests:
            already_handled = VcxConversation.objects.filter(message_id=request['msg_ref_id']).all()
            if len(already_handled) == 0:
                save_request = request.copy()
                request_data = json.dumps(save_request)
                new_request = VcxConversation(
                                    wallet_name = my_wallet,
                                    connection_partner_name = my_connection.partner_name,
                                    conversation_type = "ProofRequest",
                                    message_id = save_request['msg_ref_id'],
                                    status = 'Pending',
                                    conversation_data = request_data
                                )
                print("Saving received proof request to DB")
                new_request.save()
                handled_count = handled_count + 1
    except:
        raise

    print(" >>> Shutdown vcx (for now)")
    try:
        shutdown(False)
    except:
        raise

    print(" >>> Done!!!")

    return handled_count


def poll_message_conversations(my_wallet, config, my_connection):
    print(" >>> Initialize libvcx with configuration")
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    try:
        polled_count = 0

        # Any conversations of status 'Sent' are for bot processing ...
        messages = VcxConversation.objects.filter(wallet_name=my_wallet, connection_partner_name=my_connection.partner_name, status='Sent')

        # TODO the magic goes here ...
        for message in messages:
            print(" ... Checking message", message.message_id)
            # de-serialize message content
            
            # handle per message type
            
            # save updated conversation status

            polled_count = polled_count + 1

            pass
    except:
        raise

    print(" >>> Shutdown vcx (for now)")
    try:
        shutdown(False)
    except:
        raise

    print(" >>> Done!!!")

    return polled_count


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
        return loop.run_until_complete(coroutine())
    finally:
        loop.close()


def run_coroutine_with_args(coroutine, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args))
    finally:
        loop.close()

