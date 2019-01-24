from django.db import models


# base class for vcx connections
class IndyWallet(models.Model):
    wallet_name = models.CharField(max_length=30, unique=True)
    vcx_config = models.TextField(max_length=4000, blank=True)

    def __str__(self):
        return self.wallet_name


# base class for vcx connections
class VcxConnection(models.Model):
    #wallet_name = models.CharField(max_length=30)
    wallet_name = models.ForeignKey(IndyWallet, to_field="wallet_name", on_delete=models.CASCADE)
    partner_name = models.CharField(max_length=30)
    invitation = models.TextField(max_length=4000, blank=True)
    status = models.CharField(max_length=20)
    connection_data = models.TextField(max_length=4000, blank=True)

    def __str__(self):
        return self.wallet_name + ":" + self.partner_name + ", " +  self.status

