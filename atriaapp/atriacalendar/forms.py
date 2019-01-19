from django import forms
from modeltranslation.forms import TranslationModelForm
from django.contrib.auth.forms import UserCreationForm

from swingtime import models as swingtime_models
from swingtime import forms as swingtime_forms

from .models import *


#class EventForm(TranslationModelForm):
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
        #self.fields['location'].required = False

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2', )


# Indy-related forms

class WalletLoginForm(forms.Form):
    wallet_name = forms.CharField(label='Wallet Name', max_length=20)
    raw_password = forms.CharField(label='Password', max_length=20, widget=forms.PasswordInput)

class SendConnectionInvitationForm(WalletLoginForm):
    partner_name = forms.CharField(label='Partner Name', max_length=20)
    pass

class SendConnectionResponseForm(SendConnectionInvitationForm):
    invitation_details = forms.CharField(label='Invitation', max_length=4000, widget=forms.Textarea)
    pass

class ListConnectionsForm(WalletLoginForm):
    pass

