from datetime import date
from django.shortcuts import redirect, render
from django.db import connection

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
    if 'email' not in request.session:
        return redirect('main:login')
    return None


def _require_role(request, role):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect
    
    if request.session.get('role') != role:
        return redirect('main:dashboard')
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
    role_redirect = _require_role(request, 'Staf')
    if role_redirect:
        return role_redirect

    email_user = request.session.get('email')
    
    with connection.cursor() as cursor:
        # Ambil semua hadiah dengan info penyedia
        cursor.execute("""
            SELECT h.kode_hadiah, h.nama, h.miles, h.deskripsi, 
                   h.valid_start_date, h.program_end, m.nama_mitra
            FROM HADIAH h
            LEFT JOIN PENYEDIA p ON h.id_penyedia = p.id
            LEFT JOIN MITRA m ON p.id = m.id_penyedia
            ORDER BY h.program_end DESC
        """)
        hadiah_list = cursor.fetchall()
        
        hadiah_data = [
            {
                'kode': h[0],
                'nama': h[1],
                'miles': h[2],
                'deskripsi': h[3],
                'valid_start': h[4],
                'program_end': h[5],
                'penyedia': h[6] or '-'
            }
            for h in hadiah_list
        ]
    
    context = {
        'hadiah_list': hadiah_data,
        'today': date.today().isoformat()
    }
    return render(request, 'feat_merah/manage_rewards.html', context)


def manage_partners_view(request):
    role_redirect = _require_role(request, 'Staf')
    if role_redirect:
        return role_redirect

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT email_mitra, nama_mitra, tanggal_kerja_sama
            FROM MITRA
            ORDER BY tanggal_kerja_sama DESC
        """)
        partners = cursor.fetchall()
        
        partners_data = [
            {
                'email': p[0],
                'nama': p[1],
                'tanggal_kerja_sama': p[2]
            }
            for p in partners
        ]
    
    context = {'partners': partners_data}
    return render(request, 'feat_merah/manage_partners.html', context)
