from django.urls import path
from .views import (
    redeem_hadiah_view,
    beli_package_view,
    info_tier_view,
    laporan_transaksi_view
)

app_name = 'feat_biru'

urlpatterns = [
    path('redeem-hadiah/', redeem_hadiah_view, name='redeem_hadiah'),
    path('beli-package/', beli_package_view, name='beli_package'),
    path('info-tier/', info_tier_view, name='info_tier'),
    path('laporan-transaksi/', laporan_transaksi_view, name='laporan_transaksi'),
]