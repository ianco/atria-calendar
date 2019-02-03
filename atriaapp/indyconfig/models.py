from django.conf import settings
from django.db import models
from django.contrib.sessions.models import Session


# track user session and attached wallet for background agents
class IndySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    wallet_name = models.CharField(max_length=30, blank=True, null=True)


# base class for vcx connections
class IndyWallet(models.Model):
    wallet_name = models.CharField(max_length=30, unique=True)
    vcx_config = models.TextField(max_length=4000, blank=True)

    def __str__(self):
        return self.wallet_name


# reference to a schema on the ledger
class IndySchema(models.Model):
    ledger_schema_id = models.CharField(max_length=40, unique=True)
    schema_name = models.CharField(max_length=40)
    schema_version = models.CharField(max_length=40)
    schema = models.TextField(max_length=4000)
    schema_template = models.TextField(max_length=4000)
    schema_data = models.TextField(max_length=4000)

    def __str__(self):
        return self.schema_name


# reference to a credential definition on the ledger
class IndyCredentialDefinition(models.Model):
    ledger_creddef_id = models.CharField(max_length=40, unique=True)
    ledger_schema = models.ForeignKey(IndySchema, on_delete=models.CASCADE)
    wallet_name = models.ForeignKey(IndyWallet, to_field="wallet_name", on_delete=models.CASCADE)
    creddef_name = models.CharField(max_length=40)
    creddef_handle = models.CharField(max_length=40)
    creddef_template = models.TextField(max_length=4000)
    creddef_data = models.TextField(max_length=4000)

    def __str__(self):
        return self.ledger_schema.schema_name + ":" + self.wallet_name.wallet_name + ":" + self.creddef_name


# base class for vcx connections
class VcxConnection(models.Model):
    wallet_name = models.ForeignKey(IndyWallet, to_field="wallet_name", on_delete=models.CASCADE)
    partner_name = models.CharField(max_length=30)
    invitation = models.TextField(max_length=4000, blank=True)
    status = models.CharField(max_length=20)
    connection_type = models.CharField(max_length=20)
    connection_data = models.TextField(max_length=4000, blank=True)

    def __str__(self):
        return self.wallet_name.wallet_name + ":" + self.partner_name + ", " +  self.status


# base class for vcx conversations - issue/receive credential and request/provide proof
class VcxConversation(models.Model):
    wallet_name = models.ForeignKey(IndyWallet, to_field="wallet_name", on_delete=models.CASCADE)
    connection_partner_name = models.CharField(max_length=30)
    conversation_type = models.CharField(max_length=30)
    message_id = models.CharField(max_length=30)
    status = models.CharField(max_length=20)
    proof_state = models.CharField(max_length=20, blank=True)
    conversation_data = models.TextField(max_length=4000, blank=True)

    def __str__(self):
        return self.wallet_name.wallet_name + ":" + self.connection_partner_name + ":" + self.message_id + ", " +  self.conversation_type + " " + self.status

