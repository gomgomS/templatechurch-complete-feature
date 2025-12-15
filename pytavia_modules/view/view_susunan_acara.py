import sys
import calendar
from datetime import date, timedelta

sys.path.append("pytavia_core")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_storage")
sys.path.append("pytavia_modules/view")

from flask import render_template, request, redirect, url_for, session

from pytavia_core import database, config
from pytavia_stdlib import sanitize

from participant import participant_proc
from participant import participant_static_proc


class view_susunan_acara:
    def __init__(self, app):
        self.app = app

    def html_dynamic(self):
        today = date.today()
        year = request.args.get("year", type=int) or today.year
        quarter = request.args.get("quarter", type=int) or 4
        q = quarter if quarter in (1, 2, 3, 4) else 4

        weeks = self._build_weeks(year, q)
        selected_week = request.args.get("week", type=int) or 0
        if selected_week < 0 or selected_week >= len(weeks):
            selected_week = 0

        active_tab = (request.args.get("tab") or "khotbah").lower()
        if active_tab not in ("khotbah", "ss", "rabu", "vesper"):
            active_tab = "khotbah"
        active_key = {"khotbah": "khotbah", "ss": "sekolah_sabat", "rabu": "rabu_malam", "vesper": "vesper"}[active_tab]

        sched = None
        try:
            mgd = database.get_db_conn(config.mainDB)
            week_index = selected_week + 1
            sched = mgd.db_participant_schedule.find_one(
                {"year": int(year), "quarter": int(q), "week_index": int(week_index)},
                {"_id": 0},
            )
        except Exception as e:
            try:
                print("[view_susunan_acara.html_dynamic] fetch sched error:", str(e))
            except Exception:
                pass

        years_options = list(range(today.year - 2, today.year + 4))

        return render_template(
            "admin/susunan_acara.html",
            year=year,
            quarter=q,
            active_tab=active_tab,
            weeks=weeks,
            selected_week=selected_week,
            selected_range_label=(weeks[selected_week]["label_range"] if weeks else ""),
            selected_saturday_label=(weeks[selected_week]["label_sat"] if weeks else ""),
            selected_wednesday_label=(weeks[selected_week]["label_wed"] if weeks else ""),
            selected_friday_label=(weeks[selected_week]["label_fri"] if weeks else ""),
            years_options=years_options,
            sched=sched or {},
            active_key=active_key,
        )

    def save_dynamic(self):
        params = sanitize.clean_html_dic(request.form.to_dict())
        print("[susunan_acara_save] raw_form:", dict(request.form))
        print("[susunan_acara_save] sanitized_params:", params)

        params["user_id"] = session.get("user_id")
        token = session.pop("_csrf_token", None)
        print("[susunan_acara_save] session _csrf_token popped:", token is not None)

        proc = participant_proc.participant_proc(self.app)
        result = proc.update(params)
        print("[susunan_acara_save] upsert_result:", result)

        tab = params.get("tab", "khotbah")
        year = params.get("year", "")
        quarter = params.get("quarter", "")
        try:
            week_param = int(params.get("week_index", 1)) - 1
        except Exception:
            week_param = 0
        return redirect(url_for("admin_susunan_acara", **{
            "tab": tab,
            "year": year,
            "quarter": quarter,
            "week": week_param,
        }))

    def html_static(self):
        proc = participant_static_proc.participant_static_proc()
        active_tab = (request.args.get("tab") or "khotbah").lower()
        tab_key = proc.normalize_tab(active_tab)
        cur = proc.load(tab_key)

        return render_template(
            "admin/susunan_acara_static.html",
            active_tab=active_tab,
            active_key=tab_key,
            cur=cur or {},
        )

    def save_static(self):
        params = sanitize.clean_html_dic(request.form.to_dict())
        print("[susunan_acara_static_save] raw_form:", dict(request.form))
        print("[susunan_acara_static_save] sanitized_params:", params)

        proc = participant_static_proc.participant_static_proc()
        tab_in = (params.get("tab") or "khotbah").lower()
        tab_key = proc.normalize_tab(tab_in)
        payload = proc.build_payload(tab_key, params)
        proc.save(tab_key, payload)

        return redirect(url_for("admin_susunan_acara_static", tab=tab_in))
    # end def

    def _build_weeks(self, year: int, quarter: int):
        """Return list of 13 week dicts (Sunday–Saturday) for the given quarter."""
        q = quarter if quarter in (1, 2, 3, 4) else 4
        first_month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
        start_date = date(year, first_month, 1)
        end_month = first_month + 2
        last_day = calendar.monthrange(year, end_month)[1]
        end_date = date(year, end_month, last_day)

        cur = start_date
        while cur.weekday() != 5 and cur <= end_date:
            cur += timedelta(days=1)

        saturdays = []
        while len(saturdays) < 13:
            if cur > end_date and not saturdays:
                tmp = start_date
                while tmp.weekday() != 5:
                    tmp += timedelta(days=1)
                cur = tmp
            saturdays.append(cur)
            cur = cur + timedelta(days=7)

        month_short = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        weeks = []
        for sat in saturdays:
            sun = sat - timedelta(days=6)
            wed = sat - timedelta(days=3)
            fri = sat - timedelta(days=1)
            weeks.append(
                {
                    "sun": sun,
                    "sat": sat,
                    "wed": wed,
                    "fri": fri,
                    "label_range": f"{sun.day}–{sat.day} {month_short[sat.month - 1]} {sat.year}",
                    "label_sat": f"{sat.day} {month_short[sat.month - 1]}",
                    "label_wed": f"{wed.day} {month_short[wed.month - 1]}",
                    "label_fri": f"{fri.day} {month_short[fri.month - 1]}",
                }
            )
        return weeks
# end class
