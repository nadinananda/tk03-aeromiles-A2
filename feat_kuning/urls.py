from django.urls import path
from .views import kelola_member_view, identitas_member_view

app_name = 'kuning'

urlpatterns = [
    path('identitas/', identitas_member_view, name='identitas_member'),
    path('kelola_member/', kelola_member_view, name='kelola_member'),
]