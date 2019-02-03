from django import forms
import json

from .models import *


# Indy-related forms
class WalletLoginForm(forms.Form):
    wallet_name = forms.CharField(label='Wallet Name', max_length=20)
    raw_password = forms.CharField(label='Password', max_length=20, widget=forms.PasswordInput)


class SendConnectionInvitationForm(WalletLoginForm):
    partner_name = forms.CharField(label='Partner Name', max_length=20)

    def __init__(self, *args, **kwargs):
        super(SendConnectionInvitationForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True


class SendConnectionResponseForm(SendConnectionInvitationForm):
    connection_id = forms.IntegerField(label="Id")
    invitation_details = forms.CharField(label='Invitation', max_length=4000, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(SendConnectionResponseForm, self).__init__(*args, **kwargs)
        self.fields['connection_id'].widget.attrs['readonly'] = True
        self.fields['invitation_details'].widget.attrs['readonly'] = True


class PollConnectionStatusForm(WalletLoginForm):
    connection_id = forms.IntegerField(label="Id")

    def __init__(self, *args, **kwargs):
        super(PollConnectionStatusForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True
        self.fields['connection_id'].widget.attrs['readonly'] = True


class SendConversationResponseForm(WalletLoginForm):
    conversation_id = forms.IntegerField(label="Id")

    def __init__(self, *args, **kwargs):
        super(SendConversationResponseForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True
        self.fields['conversation_id'].widget.attrs['readonly'] = True


class PollConversationStatusForm(WalletLoginForm):
    conversation_id = forms.IntegerField(label="Id")

    def __init__(self, *args, **kwargs):
        super(PollConversationStatusForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True
        selffields['conversation_id'].widget.attrs['readonly'] = True


class SelectCredentialOfferForm(WalletLoginForm):
    connection_id = forms.IntegerField(label="Connection Id")
    cred_def = forms.ModelChoiceField(label='Cred Def', queryset=IndyCredentialDefinition.objects.all())

    def __init__(self, *args, **kwargs):
        super(SelectCredentialOfferForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True
        self.fields['connection_id'].widget.attrs['readonly'] = True
        initial = kwargs.get('initial')
        if initial:
            wallet_name = initial.get('wallet_name')
            self.fields['cred_def'].queryset = IndyCredentialDefinition.objects.filter(wallet_name__wallet_name=wallet_name).all()


class SendCredentialOfferForm(WalletLoginForm):
    connection_id = forms.IntegerField(label="Connection Id")
    credential_tag = forms.CharField(label='Credential Tag', max_length=40)
    cred_def = forms.CharField(label='Cred Def', max_length=80)
    schema_attrs = forms.CharField(label='Credential Attrs', max_length=4000, widget=forms.Textarea)
    credential_name = forms.CharField(label='Credential Name', max_length=40)

    def __init__(self, *args, **kwargs):
        super(SendCredentialOfferForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True
        self.fields['connection_id'].widget.attrs['readonly'] = True
        self.fields['cred_def'].widget.attrs['readonly'] = True


class SendCredentialResponseForm(SendConversationResponseForm):
    # a bunch of fields that are read-only to present to the user
    from_partner_name = forms.CharField(label='Partner Name', max_length=20)
    claim_id = forms.CharField(label='Credential Id', max_length=40)
    claim_name = forms.CharField(label='Credential Name', max_length=40)
    credential_attrs = forms.CharField(label='Credential Attrs', max_length=4000, widget=forms.Textarea)
    libindy_offer_schema_id = forms.CharField(label='Schema Id', max_length=80, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(SendCredentialResponseForm, self).__init__(*args, **kwargs)
        self.fields['from_partner_name'].widget.attrs['readonly'] = True
        self.fields['claim_id'].widget.attrs['readonly'] = True
        self.fields['claim_name'].widget.attrs['readonly'] = True
        self.fields['credential_attrs'].widget.attrs['readonly'] = True
        self.fields['libindy_offer_schema_id'].widget.attrs['readonly'] = True


class SendProofRequestForm(WalletLoginForm):
    connection_id = forms.IntegerField(label="Connection Id")
    proof_uuid = forms.CharField(label='Proof UUID', max_length=40)
    proof_name = forms.CharField(label='Proof Name', max_length=40)
    proof_attrs = forms.CharField(label='Proof Attrs', max_length=4000, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(SendProofRequestForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True
        self.fields['connection_id'].widget.attrs['readonly'] = True


class SendProofReqResponseForm(SendConversationResponseForm):
    # a bunch of fields that are read-only to present to the user
    from_partner_name = forms.CharField(label='Partner Name', max_length=20)
    proof_req_name = forms.CharField(label='Proof Request Name', max_length=40)
    requested_attrs = forms.CharField(label='Requested Attrs', max_length=4000, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super(SendProofReqResponseForm, self).__init__(*args, **kwargs)
        self.fields['from_partner_name'].widget.attrs['readonly'] = True
        self.fields['proof_req_name'].widget.attrs['readonly'] = True
        self.fields['requested_attrs'].widget.attrs['readonly'] = True


class SelectProofReqClaimsForm(SendProofReqResponseForm):

    def __init__(self, *args, **kwargs):
        super(SelectProofReqClaimsForm, self).__init__(*args, **kwargs)
        initial = kwargs.get('initial')
        if initial:
            field_attrs = json.loads(initial.get('requested_attrs', '{}'))
            for attr in field_attrs[0]['attrs']:
                field_name = 'proof_req_attr_' + attr
                choices = []
                claim_no = 0
                for claim in field_attrs[0]['attrs'][attr]:
                    choices.append((claim_no, json.dumps(claim)))
                    claim_no = claim_no + 1
                self.fields[field_name] = forms.ChoiceField(label='Select claim for '+attr, choices=tuple(choices), widget=forms.RadioSelect())
