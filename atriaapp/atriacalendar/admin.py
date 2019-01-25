from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
import json

from indyconfig.indyutils import create_wallet, delete_wallet, get_org_wallet_name, initialize_and_provision_vcx, create_schema_and_creddef

from .models import *
from indyconfig import models as indy_models


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email',)


class AtriaOrganizationAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if change:
            action = "change"
        else:
            action = "add"
            org_name = form.cleaned_data['org_name']
            raw_password = form.cleaned_data['password']
        obj.password = 'xxx'
        print(" >>> save", obj, obj.password, form.cleaned_data['password'], action)
        super().save_model(request, obj, form, change)
        print(" >>> save success!!!")
        if not change:
            # create an Indy wallet - derive wallet name from email, and re-use raw password
            wallet_name = get_org_wallet_name(org_name)
            print(" >>> create", wallet_name)
            wallet_handle = create_wallet(wallet_name, raw_password)
            
            # save the indy wallet first
            wallet = indy_models.IndyWallet(wallet_name=wallet_name)
            wallet.save()

            obj.wallet_name = wallet
            super().save_model(request, obj, form, True)

            # provision VCX for this Org/Wallet
            config = initialize_and_provision_vcx(wallet_name, raw_password, org_name)
            wallet.vcx_config = config
            wallet.save()

            # TODO temporary measure - create a schema and cred def and register on the ledger
            (schema, creddef) = create_schema_and_creddef(wallet, json.loads(config), 'schema_' + wallet_name, 'creddef_' + wallet_name)

            super().save_model(request, obj, form, True)
            print(" >>> created wallet", wallet_name)


    def delete_model(self, request, obj):
        print(" >>> delete", obj)
        org_name = obj.org_name
        raw_password = obj.password
        super().delete_model(request, obj)
        print(" >>> delete success!!!")

        # delete an Indy wallet - derive wallet name from email, and re-use raw password
        wallet_name = get_org_wallet_name(org_name)
        print(" >>> delete", wallet_name)
        wallet_handle = delete_wallet(wallet_name, raw_password)
        print(" >>> deleted wallet", wallet_name)


admin.site.register(AtriaEventProgram)
admin.site.register(AtriaEvent)
admin.site.register(AtriaOrganization, AtriaOrganizationAdmin)

