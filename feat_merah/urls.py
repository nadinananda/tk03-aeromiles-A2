from django.urls import path
from .views import (
    manage_rewards_view, manage_partners_view, member_redeem_view,
    approve_claim_missing_miles_view
)

app_name = 'feat_merah'

urlpatterns = [
    path('manage-rewards/', manage_rewards_view, name='manage_rewards'),
    path('manage-partners/', manage_partners_view, name='manage_partners'),
    path('redeem/', member_redeem_view, name='member_redeem'),
    path('approve-claims/', approve_claim_missing_miles_view, name='approve_claims'),
]