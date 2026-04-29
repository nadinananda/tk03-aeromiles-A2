from django.urls import path
from . import views

app_name = 'feat_hijau'

urlpatterns = [
    # Fitur 5: Pengaturan Profil
    path('profil/', views.pengaturan_profil, name='pengaturan_profil'),

    # Fitur 8: Klaim Miles (Member)
    path('klaim/', views.klaim_miles, name='klaim_miles'),
    path('klaim/baru/', views.klaim_baru, name='klaim_baru'),
    path('klaim/edit/<int:klaim_id>/', views.klaim_edit, name='klaim_edit'),
    path('klaim/hapus/<int:klaim_id>/', views.klaim_hapus, name='klaim_hapus'),
    path('klaim/detail/<int:klaim_id>/', views.klaim_detail_json, name='klaim_detail_json'),

    # Fitur 9: Kelola Klaim (Staf)
    path('kelola-klaim/', views.kelola_klaim, name='kelola_klaim'),
    path('kelola-klaim/update/<int:klaim_id>/', views.update_status_klaim, name='update_status_klaim'),

    # Fitur 10: Transfer Miles (Member)
    path('transfer/', views.transfer_miles, name='transfer_miles'),
    path('transfer/baru/', views.transfer_baru, name='transfer_baru'),
]