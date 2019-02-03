from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
import json

from indyconfig.indyutils import *

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
            org_role = form.cleaned_data['org_role']
        obj.password = 'xxx'
        print(" >>> save", obj, obj.password, form.cleaned_data['password'], action)
        super().save_model(request, obj, form, change)
        print(" >>> save success!!!")
        if not change:
            # register did (seed) before creating and provisioning wallet
            wallet_name = get_org_wallet_name(org_name)
            if org_role != 'Trustee':
                # _nym_info is did and verkey, if we need it later (re-computed during agent initialization)
                _nym_info = create_and_register_did(wallet_name, org_role)

            # create an Indy wallet - derive wallet name from email, and re-use raw password
            print(" >>> create", wallet_name)
            wallet_handle = create_wallet(wallet_name, raw_password)
            
            # save the indy wallet first
            wallet = indy_models.IndyWallet(wallet_name=wallet_name)
            wallet.save()

            obj.wallet_name = wallet
            super().save_model(request, obj, form, True)

            # provision VCX for this Org/Wallet
            config = initialize_and_provision_vcx(wallet_name, raw_password, org_name, org_role=org_role)
            wallet.vcx_config = config
            wallet.save()

            # TODO temporary measure - create a schema and cred def and register on the ledger
            if org_role != 'Trustee':
                trustees = AtriaOrganization.objects.filter(org_role='Trustee').all()
                if 0 < len(trustees):
                    trustee = trustees[0]
                    trustee_wallet = trustee.wallet_name
                    trustee_config = trustee_wallet.vcx_config
                else:
                    # if there is no Trustee available just use the current org
                    trustee_config = config
                
                # create a "dummy" schema/cred-def that is unique to this org
                (schema_json, creddef_template) = create_schema_json('schema_' + wallet_name, random_schema_version(), ['name', 'date', 'degree'])
                schema = create_schema(wallet, json.loads(trustee_config), schema_json, creddef_template)
                creddef = create_creddef(wallet, json.loads(config), schema, 'creddef_' + wallet_name, creddef_template)

                # create cred defs for the "default" schemas
                schemas = IndySchema.objects.filter(schema_name='Transcript', schema_version='1.2').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)
                schemas = IndySchema.objects.filter(schema_name='Job-Certificate', schema_version='0.2').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)
            else:
                # create some "default" schemas for use by everyone
                (schema_json, creddef_template) = create_schema_json('Transcript', '1.2', ['first_name', 'last_name', 'degree', 'status', 'year', 'average', 'ssn'])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)
                (schema_json, creddef_template) = create_schema_json('Job-Certificate', '0.2', ['first_name', 'last_name', 'ssn', 'salary', 'employee_status', 'experience'])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)

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

