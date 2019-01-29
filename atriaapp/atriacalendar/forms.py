from django import forms
from modeltranslation.forms import TranslationModelForm
from django.contrib.auth.forms import UserCreationForm

from swingtime import models as swingtime_models
from swingtime import forms as swingtime_forms

from .models import *
import indyconfig.models as indy_models


# class EventForm(TranslationModelForm):
#    """
#    A simple form for adding and updating Event attributes.
#    """
#
#    class Meta:
#        model = Event
#        fields = "__all__"
#
#    def __init__(self, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        self.fields['description'].required = False

class AtriaEventForm(swingtime_forms.EventForm, TranslationModelForm):
    """
    A simple form for adding and updating Event attributes.
    """

    class Meta:
        model = AtriaEvent
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['program'].required = False
        # self.fields['location'].required = False


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False,
                                 help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False,
                                help_text='Optional.')
    email = forms.EmailField(
        max_length=254, help_text='Required. Inform a valid email address.')

    def save(self):
        if Group.objects.filter(name='Attendee').exists():
            user = super().save()

            user.groups.add(Group.objects.get(name='Attendee'))

            return user

        return super().save()

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')


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
        super(SendConnectionResponseForm, self).__init__(*args, **kwargs)
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


class SendCredentialOfferForm(WalletLoginForm):
    connection_id = forms.IntegerField(label="Connection Id")
    credential_tag = forms.CharField(label='Credential Tag', max_length=40)
    cred_def = forms.ModelChoiceField(label='Cred Def', queryset=indy_models.IndyCredentialDefinition.objects.all().order_by('wallet_name'))
    schema_attrs = forms.CharField(label='Credential Attrs', max_length=4000, widget=forms.Textarea)
    credential_name = forms.CharField(label='Credential Name', max_length=40)

    def __init__(self, *args, **kwargs):
        super(SendCredentialOfferForm, self).__init__(*args, **kwargs)
        self.fields['wallet_name'].widget.attrs['readonly'] = True


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

