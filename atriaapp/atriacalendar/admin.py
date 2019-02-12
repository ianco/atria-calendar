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

            # TODO temporary measure - create schema(s) and cred def(s) and register on the ledger
            if org_role == 'Trustee':
                # create some "default" schemas for use by everyone
                # education transcript (proof of education)
                (schema_json, creddef_template) = create_schema_json('Transcript', random_schema_version(), [
                    'first_name', 
                    'last_name', 
                    'degree', 
                    'status', 
                    'year', 
                    'average', 
                    'ssn',
                    ])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)
                # job transcript (proof of income)
                (schema_json, creddef_template) = create_schema_json('Job-Certificate', random_schema_version(), [
                    'first_name', 
                    'last_name', 
                    'ssn', 
                    'salary', 
                    'employee_status', 
                    'experience',
                    ])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)
                # driver license (proof of age or address)
                (schema_json, creddef_template) = create_schema_json('Driver-License', random_schema_version(), [
                    'last_name', 
                    'first_name', 
                    'middle_name', 
                    'dl_number', 
                    'dl_class', 
                    'issued_date', 
                    'expire_date', 
                    'birth_date', 
                    'height', 
                    'weight', 
                    'sex', 
                    'eyes', 
                    'hair', 
                    'address',
                    ])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)
                # passport (proof of age or citizenship)
                (schema_json, creddef_template) = create_schema_json('Passport', random_schema_version(), [
                    'last_name', 
                    'first_name', 
                    'middle_name', 
                    'passport_no', 
                    'ppt_type', 
                    'issued_date', 
                    'issued_location',
                    'expire_date', 
                    'nationality',
                    'birth_date', 
                    'issuing_country',
                    'issuing_authority',
                    ])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)

                # Trustee can issue Passport and Driver License
                schemas = IndySchema.objects.filter(schema_name='Driver-License').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)
                schemas = IndySchema.objects.filter(schema_name='Passport').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)

                # schemas for the MYco business processes
                # Health Certificate Credential
                (schema_json, creddef_template) = create_schema_json('Health-Certificate', random_schema_version(), [
                    'myco_id', 
                    'level', 
                    'name', 
                    'short_name', 
                    'type', 
                    'category', 
                    'superclass', 
                    'output_type', 
                    'ref_unit', 
                    'ref_unit_timestamp',
                    'range', 
                    'concentration', 
                    'unit',
                    ])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)
                # Research Project Credential
                (schema_json, creddef_template) = create_schema_json('Research-Project', random_schema_version(), [
                    'project_name', 
                    'PI_last_name', 
                    'PI_first_name', 
                    'institutional_affiliation',
                    'project_description', 
                    'myco_id', 
                    'level', 
                    'name', 
                    'short_name', 
                    'type', 
                    'category', 
                    'superclass', 
                    'output_type', 
                    'range', 
                    ])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)
                # Consent Credential
                (schema_json, creddef_template) = create_schema_json('Consent', random_schema_version(), [
                    'jurisdiction', 
                    'iat', 
                    'moc', 
                    'iss', 
                    'jti', 
                    'sub', 
                    'data_controller', #{This is an object containing the following array of strings: "on_behalf": true, "contact": "Dave Controller", "company": "Data Controller Inc.", "address": "123 St., Place", "email": "dave@datacontroller.com", "phone": "00-123-341-2351"}, 
                    'policy_url', 
                    'purpose', 
                    'sensitive', 
                    'sharing', #{This is an object containing the following array of strings: “party_name”: "3rd Party Name or/3rd Party Category"}, 
                    'notice', 
                    'scopes', 
                    ])
                schema = create_schema(wallet, json.loads(config), schema_json, creddef_template)

                # standard proofs for the MYco business processes
                # Proof of Ethics (to perform research)
                create_proof_request('Proof of Ethics', 'Proof that a Researcher has been audited and is certified to follow the terms of their research study',
                    [{'name':'project_name', 'restrictions':[{'issuer_did': '$IRB_DID'}]},
                     {'name':'myco_id', 'restrictions':[{'issuer_did': '$IRB_DID'}]},
                     {'name':'level', 'restrictions':[{'issuer_did': '$IRB_DID'}]}, 
                     {'name':'name', 'restrictions':[{'issuer_did': '$IRB_DID'}]}],
                    [{'name': 'type','p_type': '>=','p_value': '$VALUE'}]
                    )
                # Proof of Suitability (to participate in study)
                create_proof_request('Proof of Suitability', 'Proof that a MYco Client is suitable according to the terms of the study',
                    [{'name':'short_name', 'restrictions':[{'issuer_did': '$MYCO_DID'}]},
                     {'name':'myco_id', 'restrictions':[{'issuer_did': '$MYCO_DID'}]}],
                    [{'name': 'type','p_type': '>=','p_value': '$VALUE'},
                     {'name': 'category','p_type': '>=','p_value': '$VALUE'},
                     {'name': 'superclass','p_type': '>=','p_value': '$VALUE'}]
                    )
                # Proof of Consent (to use data for study)
                create_proof_request('Proof of Consent', 'Proof that a MYco Client has consented to participate in study',
                    [{'name':'data_controller', 'restrictions':[{'issuer_did': '$ISSUER_DID'}]},
                     {'name':'policy_url', 'restrictions':[{'issuer_did': '$ISSUER_DID'}]},
                     {'name':'sensitive', 'restrictions':[{'issuer_did': '$ISSUER_DID'}]},
                     {'name':'sharing', 'restrictions':[{'issuer_did': '$ISSUER_DID'}]}],
                    []
                    )

            elif org_role == 'MYco':
                # cred def to issue Health Certificate Credential
                schemas = IndySchema.objects.filter(schema_name='Health-Certificate').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)

            #elif org_role == 'Client':  # TODO - this is really not an "org"
                # TBD - receives Health Certificate, issues Consent Credential (?)
                # not an org, will be an Individual

            elif org_role == 'IRB':
                # cred def to issue Research Project Credential
                schemas = IndySchema.objects.filter(schema_name='Research-Project').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)

            elif org_role == 'Researcher':  # TODO
                # receives credentials and provides proofs; not sure if they are an issuer
                # TODO for now add a cred def to issue a Consent Credential to MYco Client (?)
                schemas = IndySchema.objects.filter(schema_name='Consent').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)

            else:
                trustees = AtriaOrganization.objects.filter(org_role='Trustee').all()
                if 0 < len(trustees):
                    trustee = trustees[0]
                    trustee_wallet = trustee.wallet_name
                    trustee_config = trustee_wallet.vcx_config
                else:
                    # if there is no Trustee available just use the current org
                    trustee_config = config
                
                # create a "dummy" schema/cred-def that is unique to this org (matches the Alice/Faber demo schema)
                (schema_json, creddef_template) = create_schema_json('schema_' + wallet_name, random_schema_version(), [
                    'name', 'date', 'degree', 'age',
                    ])
                schema = create_schema(wallet, json.loads(trustee_config), schema_json, creddef_template)
                creddef = create_creddef(wallet, json.loads(config), schema, 'creddef_' + wallet_name, creddef_template)

                # create cred defs for the "default" schemas
                schemas = IndySchema.objects.filter(schema_name='Transcript').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)
                schemas = IndySchema.objects.filter(schema_name='Job-Certificate').all()
                schema = schemas[0]
                creddef = create_creddef(wallet, json.loads(config), schema, schema.schema_name + '-' + wallet_name, schema.schema_template)

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

