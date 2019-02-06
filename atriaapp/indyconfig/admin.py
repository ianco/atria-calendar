from django.contrib import admin

from .models import *


admin.site.register(IndyWallet)
admin.site.register(IndySchema)
admin.site.register(IndyCredentialDefinition)
admin.site.register(IndyProofRequest)
admin.site.register(VcxConnection)
admin.site.register(VcxConversation)

