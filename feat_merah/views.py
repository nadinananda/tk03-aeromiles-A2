from datetime import date

from django.shortcuts import redirect, render


DEMO_ACCOUNTS = {
    "member@aeromiles.com": {
        "password": "12345",
        "role": "Member",
        "name": "Mr. John Doe",
        "award_miles": 32000,
        "total_miles": 45000,
        "tier": "Gold",
        "member_number": "M9999",
    },
    "staf@aeromiles.com": {
        "password": "12345",
        "role": "Staf",
        "name": "Mr. Admin Aero",
        "staff_number": "S9999",
        "airline": "Garuda Indonesia",
    },
}

PROVIDERS = [
    {"id": 1, "name": "Garuda Indonesia", "category": "airline"},
    {"id": 2, "name": "TravelokaPartner", "category": "partner"},
    {"id": 3, "name": "Plaza Premium", "category": "partner"},
    {"id": 4, "name": "BlueSky Hotel", "category": "partner"},
    {"id": 5, "name": "AeroShop", "category": "partner"},
]

REWARDS = [
    {
        "code": "RWD-001",
        "name": "Tiket Domestik PP",
        "description": "Tiket pulang-pergi rute domestik Indonesia.",
        "provider_id": 1,
        "miles": 15000,
        "valid_start": "2026-01-01",
        "program_end": "2026-12-31",
    },
    {
        "code": "RWD-002",
        "name": "Upgrade ke Business Class",
        "description": "Upgrade dari economy class ke business class.",
        "provider_id": 1,
        "miles": 25000,
        "valid_start": "2026-01-01",
        "program_end": "2027-01-01",
    },
    {
        "code": "RWD-003",
        "name": "Voucher Hotel Rp 500.000",
        "description": "Voucher hotel jaringan mitra AeroMiles.",
        "provider_id": 2,
        "miles": 8000,
        "valid_start": "2026-02-01",
        "program_end": "2026-09-30",
    },
    {
        "code": "RWD-004",
        "name": "Akses Lounge 1x",
        "description": "Akses lounge sebelum keberangkatan untuk satu orang.",
        "provider_id": 3,
        "miles": 3000,
        "valid_start": "2024-01-01",
        "program_end": "2025-12-31",
    },
    {
        "code": "RWD-005",
        "name": "Extra Baggage 10kg",
        "description": "Tambahan bagasi 10kg untuk penerbangan domestik.",
        "provider_id": 1,
        "miles": 6000,
        "valid_start": "2026-03-01",
        "program_end": "2026-11-30",
    },
]

PARTNERS = [
    {
        "email": "partner@traveloka.com",
        "provider_id": 2,
        "name": "TravelokaPartner",
        "cooperation_date": "2023-01-15",
    },
    {
        "email": "partner@plazapremium.com",
        "provider_id": 3,
        "name": "Plaza Premium",
        "cooperation_date": "2023-06-01",
    },
    {
        "email": "partner@blueskyhotel.com",
        "provider_id": 4,
        "name": "BlueSky Hotel",
        "cooperation_date": "2024-03-12",
    },
]


def _current_user(request):
    email = request.COOKIES.get("aero_email")
    if not email:
        return None

    account = DEMO_ACCOUNTS.get(email, {})
    return {
        "email": email,
        "name": request.COOKIES.get("aero_name", account.get("name", email)),
        "role": request.COOKIES.get("aero_role", account.get("role")),
        **account,
    }


def _require_login(request):
    if not _current_user(request):
        return redirect("feat_merah:login")
    return None


def _require_role(request, role):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    current_user = _current_user(request)
    if current_user["role"] != role:
        return redirect("feat_merah:dashboard")
    return None


def _provider_by_id(provider_id):
    return next((provider for provider in PROVIDERS if provider["id"] == provider_id), None)


def _reward_status(reward):
    today = date.today().isoformat()
    if reward["valid_start"] > today:
        return "Akan Datang"
    if reward["program_end"] < today:
        return "Selesai"
    return "Aktif"


def _enriched_rewards():
    enriched = []
    for reward in REWARDS:
        provider = _provider_by_id(reward["provider_id"])
        enriched.append(
            {
                **reward,
                "provider_name": provider["name"] if provider else "-",
                "provider_category": provider["category"] if provider else "-",
                "status": _reward_status(reward),
            }
        )
    return enriched


def login_view(request):
    if _current_user(request):
        return redirect("feat_merah:dashboard")

    context = {
        "demo_member": "member@aeromiles.com / 12345",
        "demo_staf": "staf@aeromiles.com / 12345",
    }

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        account = DEMO_ACCOUNTS.get(email)

        if account and account["password"] == password:
            response = redirect("feat_merah:dashboard")
            response.set_cookie("aero_email", email, max_age=28800, samesite="Lax")
            response.set_cookie("aero_role", account["role"], max_age=28800, samesite="Lax")
            response.set_cookie("aero_name", account["name"], max_age=28800, samesite="Lax")
            return response

        context.update(
            {
                "error": "Email atau password salah.",
                "email_value": email,
            }
        )

    return render(request, "feat_merah/login.html", context)


def logout_view(request):
    response = redirect("feat_merah:login")
    response.delete_cookie("aero_email")
    response.delete_cookie("aero_role")
    response.delete_cookie("aero_name")
    return response


def dashboard_view(request):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    user = _current_user(request)
    context = {"user": user}

    if user["role"] == "Member":
        context["transactions"] = [
            {"type": "Transfer", "time": "2026-01-15 10:30", "miles": -5000},
            {"type": "Redeem", "time": "2026-01-20 16:00", "miles": -3000},
            {"type": "Package", "time": "2026-03-01 08:00", "miles": 10000},
        ]
    else:
        context["staff_stats"] = [
            {"label": "Klaim Menunggu", "value": 2},
            {"label": "Klaim Disetujui", "value": 1},
            {"label": "Klaim Ditolak", "value": 1},
            {"label": "Hadiah Aktif", "value": 4},
        ]

    return render(request, "feat_merah/dashboard.html", context)


def manage_rewards_view(request):
    role_redirect = _require_role(request, "Staf")
    if role_redirect:
        return role_redirect

    context = {
        "providers": PROVIDERS,
        "rewards": _enriched_rewards(),
        "today": date.today().isoformat(),
    }
    return render(request, "feat_merah/manage_rewards.html", context)


def manage_partners_view(request):
    role_redirect = _require_role(request, "Staf")
    if role_redirect:
        return role_redirect

    context = {
        "partners": PARTNERS,
        "next_provider_id": max(provider["id"] for provider in PROVIDERS) + 1,
    }
    return render(request, "feat_merah/manage_partners.html", context)
