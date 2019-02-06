import asyncio
import aiohttp
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


def wallet_seed(wallet_name, org_role=''):
    if org_role == 'Trustee':
        return settings.INDY_CONFIG['vcx_enterprise_seed']
    else:
        return (settings.INDY_CONFIG['vcx_institution_seed'] + wallet_name)[-32:]

def vcx_provision_config(wallet_name, raw_password, institution_name, org_role='', institution_logo_url='http://robohash.org/456'):
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
    }

    # role-dependant did seed
    provisionConfig['enterprise_seed'] = wallet_seed(wallet_name, org_role)

    provisionConfig['institution_name'] = institution_name
    provisionConfig['institution_logo_url'] = institution_logo_url
    provisionConfig['genesis_path'] = settings.INDY_CONFIG['vcx_genesis_path']
    provisionConfig['pool_name'] = 'pool_' + wallet_name

    return provisionConfig


async def register_did_on_ledger(ledger_url, alias, seed):
    try:
        async with aiohttp.ClientSession() as client:
            response = await client.post(
                "{}/register".format(ledger_url),
                json={"alias": alias, "seed": seed, "role": "TRUST_ANCHOR"},
            )
            nym_info = await response.json()
            print(nym_info)
    except Exception as e:
        raise Exception(str(e)) from None
    if not nym_info or not nym_info["did"]:
        raise Exception(
            "DID registration failed: {}".format(nym_info)
        )
    return nym_info


def create_and_register_did(wallet_name, org_role):
    if org_role == 'Trustee':
        # don't register Trustee role
        return

    if not settings.INDY_CONFIG['register_dids']:
        return

    enterprise_seed = wallet_seed(wallet_name, org_role)
    ledger_url = settings.INDY_CONFIG['ledger_url']
    nym_info = run_coroutine_with_args(register_did_on_ledger, ledger_url, wallet_name, enterprise_seed)

    return nym_info


def initialize_and_provision_vcx(wallet_name, raw_password, institution_name, org_role='', institution_logo_url='http://robohash.org/456'):
    provisionConfig = vcx_provision_config(wallet_name, raw_password, institution_name, org_role, institution_logo_url)

    print(" >>> Provision an agent and wallet, get back configuration details")
    try:
        provisionConfig_json = json.dumps(provisionConfig)
        config = run_coroutine_with_args(vcx_agent_provision, provisionConfig_json)
        print("config", config)
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
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise
    finally:
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
    finally:
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
    finally:
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
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")
    return connection_data, return_state


def random_schema_version():
    version = format("%d.%d.%d" % (random.randint(1, 101), random.randint(1, 101), random.randint(1, 101)))
    return version


def create_schema_json(schema_name, schema_version, schema_attrs):
    schema = {
        'name': schema_name,
        'version': schema_version,
        'attributes': schema_attrs
    }
    creddef_template = {}
    for attr in schema_attrs:
        creddef_template[attr] = ''
    return (json.dumps(schema), json.dumps(creddef_template))


# TODO for now just create a random schema and creddef
def create_schema(wallet, config, schema_json, schema_template):
    # generic config for creating schemas
    print(" >>> Initialize libvcx with trustee configuration")
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    try:
        schema = json.loads(schema_json)
        vcxschema = run_coroutine_with_args(Schema.create, 'schema_uuid', schema['name'], schema['version'], schema['attributes'], 0)
        schema_id = run_coroutine(vcxschema.get_schema_id)
        schema_data = run_coroutine(vcxschema.serialize)

        indy_schema = IndySchema(
                            ledger_schema_id = schema_id,
                            schema_name = schema['name'],
                            schema_version = schema['version'],
                            schema = schema_data,
                            schema_template = schema_template,
                            schema_data = json.dumps(schema_data)
                            )
        indy_schema.save()

    except:
        raise
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    return indy_schema


# TODO for now just create a random schema and creddef
def create_creddef(wallet, config, indy_schema, creddef_name, creddef_template):
    # wallet specific-configuration for creatig the cred def
    print(" >>> Initialize libvcx with wallet-specific configuration")
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    try:
        cred_def = run_coroutine_with_args(CredentialDef.create, 'credef_uuid', creddef_name, indy_schema.ledger_schema_id, 0)
        cred_def_handle = cred_def.handle
        cred_def_id = run_coroutine(cred_def.get_cred_def_id)
        creddef_data = run_coroutine(cred_def.serialize)

        indy_creddef = IndyCredentialDefinition(
                            ledger_creddef_id = cred_def_id,
                            ledger_schema = indy_schema,
                            wallet_name = wallet,
                            creddef_name = creddef_name,
                            creddef_handle = cred_def_handle,
                            creddef_template = creddef_template,
                            creddef_data = json.dumps(creddef_data)
                            )
        indy_creddef.save()

    except:
        raise
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")

    return indy_creddef


def send_credential_offer(wallet, config, connection_data, partner_name, credential_tag, schema_attrs, cred_def, credential_name):
    print(" >>> Initialize libvcx with new configuration for a cred offer to", partner_name)
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and generate invitation
    try:
        my_connection = run_coroutine_with_args(Connection.deserialize, connection_data)
        my_cred_def = run_coroutine_with_args(CredentialDef.deserialize, json.loads(cred_def.creddef_data))
        cred_def_handle = my_cred_def.handle

        # create a credential (the last '0' is the 'price')
        credential = run_coroutine_with_args(IssuerCredential.create, credential_tag, json.loads(schema_attrs), int(cred_def_handle), credential_name, '0')

        print("Issue credential offer to", partner_name)
        run_coroutine_with_args(credential.send_offer, my_connection)

        # serialize/deserialize credential - waiting for Alice to rspond with Credential Request
        credential_data = run_coroutine(credential.serialize)
    except:
        raise
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")
    return credential_data
    

def send_credential_request(wallet, config, connection_data, partner_name, my_conversation):
    print(" >>> Initialize libvcx with new configuration for a cred offer to", partner_name)
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and generate invitation
    try:
        my_connection = run_coroutine_with_args(Connection.deserialize, connection_data)
        #my_offer = run_coroutine_with_args()
    
        print("Create a credential object from the credential offer")
        offer_json = [json.loads(my_conversation.conversation_data),]
        credential = run_coroutine_with_args(Credential.create, 'credential', offer_json)

        print("After receiving credential offer, send credential request")
        run_coroutine_with_args(credential.send_request, my_connection, 0)

        # serialize/deserialize credential - wait for Faber to send credential
        credential_data = run_coroutine(credential.serialize)
    except:
        raise
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")
    return credential_data


def send_proof_request(wallet, config, connection_data, partner_name, proof_uuid, proof_name, proof_attrs, proof_predicates):
    print(" >>> Initialize libvcx with new configuration for a cred offer to", partner_name)
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and generate invitation
    try:
        my_connection = run_coroutine_with_args(Connection.deserialize, connection_data)

        # create a proof request
        proof = run_coroutine_with_kwargs(Proof.create, proof_uuid, proof_name, json.loads(proof_attrs), {}, requested_predicates=json.loads(proof_predicates))

        run_coroutine_with_args(proof.request_proof, my_connection)

        # serialize/deserialize credential - waiting for Alice to rspond with Credential Request
        proof_data = run_coroutine(proof.serialize)
    except:
        raise
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")
    return proof_data


def get_claims_for_proof_request(wallet, config, connection_data, partner_name, my_conversation):
    print(" >>> Initialize libvcx with new configuration for a cred offer to", partner_name)
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and generate invitation
    try:
        my_connection = run_coroutine_with_args(Connection.deserialize, connection_data)

        # create a proof request
        proof = run_coroutine_with_args(DisclosedProof.create, 'proof', json.loads(my_conversation.conversation_data))

        creds_for_proof = run_coroutine(proof.get_creds)

        # serialize/deserialize proof 
        proof_data = run_coroutine(proof.serialize)

    except:
        raise
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")
    return (creds_for_proof, proof_data)


def send_claims_for_proof_request(wallet, config, connection_data, partner_name, my_conversation, credential_attrs):
    print(" >>> Initialize libvcx with new configuration for a cred offer to", partner_name)
    try:
        config_json = json.dumps(config)
        run_coroutine_with_args(vcx_init_with_config, config_json)
    except:
        raise

    # create connection and generate invitation
    try:
        my_connection = run_coroutine_with_args(Connection.deserialize, connection_data)

        # load proof request
        proof = run_coroutine_with_args(DisclosedProof.create, 'proof', json.loads(my_conversation.conversation_data))
        creds_for_proof = run_coroutine(proof.get_creds)

        for attr in creds_for_proof['attrs']:
            selected = credential_attrs[attr]
            creds_for_proof['attrs'][attr] = {
                'credential': creds_for_proof['attrs'][attr][selected]
            }

        # generate and send proof
        run_coroutine_with_args(proof.generate_proof, creds_for_proof, {})
        run_coroutine_with_args(proof.send_proof, my_connection)

        # serialize/deserialize proof 
        proof_data = run_coroutine(proof.serialize)

    except:
        raise
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")
    return proof_data


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
        # TODO ignore polling errors for now ...
        #raise
        print("Error polling offers and proof requests")
        pass
    finally:
        print(" >>> Shutdown vcx (for now)")
        try:
            shutdown(False)
        except:
            raise

    print(" >>> Done!!!")

    return handled_count


def poll_message_conversation(my_wallet, config, my_connection, message, initialize_vcx=True):
    if initialize_vcx:
        print(" >>> Initialize libvcx with configuration")
        try:
            config_json = json.dumps(config)
            run_coroutine_with_args(vcx_init_with_config, config_json)
        except:
            raise

    try:
        print(" ... Checking message", message.message_id, message.conversation_type)

        connection = run_coroutine_with_args(Connection.deserialize, json.loads(my_connection.connection_data))

        polled_count = 0

        # handle based on message type and status:
        if message.conversation_type == 'CredentialOffer':
            # offer sent from issuer to individual
            # de-serialize message content
            credential = run_coroutine_with_args(IssuerCredential.deserialize, json.loads(message.conversation_data))

            run_coroutine(credential.update_state)
            credential_state = run_coroutine(credential.get_state)
            print("Updated status = ", credential_state)

            if credential_state == State.RequestReceived:
                print("Sending credential")
                run_coroutine_with_args(credential.send_credential, connection)
                message.conversation_type = 'IssueCredential'
            elif credential_state == State.Accepted:
                message.status = 'Accepted'

            # serialize/deserialize credential - wait for Faber to send credential
            print("Saving message with a status of ", message.message_id, message.conversation_type, message.status)
            credential_data = run_coroutine(credential.serialize)
            message.conversation_data = json.dumps(credential_data)
            message.save()
        
        elif message.conversation_type == 'CredentialRequest':
            # cred request sent from individual to offerer
            conversation_data_json = json.loads(message.conversation_data)
            credential = run_coroutine_with_args(Credential.deserialize, conversation_data_json)

            run_coroutine(credential.update_state)
            credential_state = run_coroutine(credential.get_state)
            print("Updated status = ", credential_state)

            if credential_state == State.Accepted:
                message.status = 'Accepted'

            print("Saving message with a status of ", message.message_id, message.conversation_type, message.status)
            credential_data = run_coroutine(credential.serialize)
            message.conversation_data = json.dumps(credential_data)
            message.save()

        elif message.conversation_type == 'IssueCredential':
            # credential sent, waiting for acceptance
            # de-serialize message content
            credential = run_coroutine_with_args(IssuerCredential.deserialize, json.loads(message.conversation_data))

            run_coroutine(credential.update_state)
            credential_state = run_coroutine(credential.get_state)
            print("Updated status = ", credential_state)

            if credential_state == State.Accepted:
                message.status = 'Accepted'

            # serialize/deserialize credential - wait for Faber to send credential
            print("Saving message with a status of ", message.message_id, message.conversation_type, message.status)
            credential_data = run_coroutine(credential.serialize)
            message.conversation_data = json.dumps(credential_data)
            message.save()
        
        elif message.conversation_type == 'ProofRequest':
            # proof request send, waiting for proof offer
            # de-serialize message content
            proof = run_coroutine_with_args(Proof.deserialize, json.loads(message.conversation_data))

            run_coroutine(proof.update_state)
            proof_state = run_coroutine(proof.get_state)
            print("Updated status = ", proof_state)

            if proof_state == State.Accepted:
                message.status = 'Accepted'
                run_coroutine_with_args(proof.get_proof, connection)

                if proof.proof_state == ProofState.Verified:
                    print("proof is verified!!")
                    message.proof_state = 'Verified'
                else:
                    print("could not verify proof :(")
                    message.proof_state = 'Not Verified'

            # serialize/deserialize credential - wait for Faber to send credential
            print("Saving message with a status of ", message.message_id, message.conversation_type, message.status)
            proof_data = run_coroutine(proof.serialize)
            message.conversation_data = json.dumps(proof_data)
            message.save()

        else:
            print("Error unknown conversation type", message.message_id, message.conversation_type)

        polled_count = polled_count + 1

        pass
    except:
        raise
    finally:
        if initialize_vcx:
            print(" >>> Shutdown vcx (for now)")
            try:
                shutdown(False)
            except:
                raise

    print(" >>> Done!!!")

    return polled_count


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

        for message in messages:
            count = poll_message_conversation(my_wallet, config, my_connection, message, initialize_vcx=False)
            polled_count = polled_count + count
            pass
    except:
        raise
    finally:
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


def run_coroutine_with_kwargs(coroutine, *args, **kwargs):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args, **kwargs))
    finally:
        loop.close()

