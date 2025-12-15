import sys
import os
import json
import math
from datetime import datetime

sys.path.append("pytavia_core"    )
sys.path.append("pytavia_modules" )
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib"  )
sys.path.append("pytavia_storage" )
sys.path.append("pytavia_modules/view" )

from flask          import render_template


class view_index:

    def __init__(self):
        pass
    # end def

    def _load_pricing(self):
        """
        Load pricing strictly from static/json_file/pricing_armada.json
        (single source of truth).
        """
        path = os.path.join("static", "json_file", "pricing_armada.json")
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fp:
                    return json.load(fp)
        except Exception:
            return []
        return []
    # end def

    def _load_all_content(self):
        """Load all content from single JSON file"""
        path = os.path.join("static", "json_file", "site_content.json")
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fp:
                    return json.load(fp)
        except Exception:
            pass
        return {}
    # end def

    def _load_navigation(self):
        """Load navigation items from JSON"""
        path = os.path.join("static", "json_file", "navigation.json")
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fp:
                    return json.load(fp)
        except Exception:
            pass
        return []
    # end def

    def html(self):
        # Load pricing data and render template with context
        pricing = self._load_pricing()
        
        # Load navigation and content from single file
        navigation = self._load_navigation()
        all_content = self._load_all_content()
        
        # Extract all content and plugins from site_content.json
        # Convert from {"key": {"content": "...", "plugin": {...}}} to separate dicts
        content_data = {}
        plugin_data = {}
        for key, value in all_content.items():
            if isinstance(value, dict):
                if "content" in value:
                    content_data[key] = value["content"]
                if "plugin" in value:
                    plugin_data[key] = value["plugin"]
            elif isinstance(value, str):
                # Handle case where content is directly a string
                content_data[key] = value

        # Debug: Print plugin data to verify it's loaded
        print(f"[view_index] Plugin data loaded: {list(plugin_data.keys())}")
        if "contact" in plugin_data and "maps" in plugin_data["contact"]:
            print(f"[view_index] Contact maps data: {plugin_data['contact']['maps']}")

        return render_template(
            "index.html",
            site_name        = "GMAHK SION",
            hero_title       = "Gereja Masehi Advent Hari Ketujuh",
            hero_subtitle    = "Berdedikasi untuk mengasihi dan melayani dengan sepenuh hati.",
            pricing          = pricing,
            calc             = None,
            navigation       = navigation,
            content_data     = content_data,
            plugin_data      = plugin_data,
            form_values      = {
                "start_datetime": "",
                "end_datetime": "",
                "start_date": "",
                "start_time": "",
                "end_date": "",
                "end_time": "",
            },
        )
    # end def

    def calculate_and_render(self, form_data):
        pricing = self._load_pricing()

        # Normalize inputs
        car_name     = (form_data.get("car_name") or "").strip()
        wd_raw       = form_data.get("with_driver", None)
        with_driver  = False
        if wd_raw is not None:
            wd_str = str(wd_raw).strip().lower()
            with_driver = wd_str in ("1", "on", "true", "yes")
        # end if
        start_datetime = (form_data.get("start_datetime") or "").strip()
        end_datetime   = (form_data.get("end_datetime") or "").strip()
        # Backward-compatible fallback if older fields were sent
        start_date   = (form_data.get("start_date") or "").strip()
        end_date     = (form_data.get("end_date") or "").strip()
        start_time   = (form_data.get("start_time") or "").strip()
        end_time     = (form_data.get("end_time") or "").strip()
        if not start_datetime and (start_date or start_time):
            # Compose ISO-like value expected by datetime-local input (YYYY-MM-DDTHH:MM)
            start_datetime = f"{start_date}T{start_time}" if start_date and start_time else (start_date or "")
        if not end_datetime and (end_date or end_time):
            end_datetime = f"{end_date}T{end_time}" if end_date and end_time else (end_date or "")
        try:
            days = int(str(form_data.get("days", "1")).strip() or "1")
            if days <= 0:
                days = 1
        except Exception:
            days = 1
        # end try

        # Derive billing days from date range (per calendar day, not hours)
        computed_days = None
        def parse_dt(val: str):
            try:
                if val and "T" in val:
                    return datetime.strptime(val[:16], "%Y-%m-%dT%H:%M")
                return None
            except Exception:
                return None
        # end def
        sdt = parse_dt(start_datetime)
        edt = parse_dt(end_datetime)
        if sdt and edt:
            # Billing is per day (date-based), independent of hours.
            start_date_only = sdt.date()
            end_date_only   = edt.date()
            if end_date_only < start_date_only:
                end_date_only = start_date_only
            days_span = (end_date_only - start_date_only).days + 1
            computed_days = max(1, days_span)
        # end if
        def fmt_dt(val: str) -> str:
            try:
                if val and "T" in val:
                    dt = datetime.strptime(val[:16], "%Y-%m-%dT%H:%M")
                    return dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
            return val or "-"
        # end def
        def fmt_dt_id_date(val: str) -> str:
            try:
                if val and "T" in val:
                    dt = datetime.strptime(val[:16], "%Y-%m-%dT%H:%M")
                elif val:
                    dt = datetime.strptime(val[:10], "%Y-%m-%d")
                else:
                    return "-"
                hari = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
                bulan = [
                    "Januari","Februari","Maret","April","Mei","Juni",
                    "Juli","Agustus","September","Oktober","November","Desember"
                ]
                # datetime.weekday(): Monday=0
                dow = hari[dt.weekday()]
                return f"{dow}, {dt.day} {bulan[dt.month-1]} {dt.year}"
            except Exception:
                return val or "-"
        # end def

        # Find selected car
        selected = None
        for item in pricing:
            if item.get("name") == car_name:
                selected = item
                break
        # end for

        calc = None
        if selected is not None:
            mandatory = bool(selected.get("driver_mandatory"))
            final_with_driver = True if mandatory else with_driver

            # Use computed days if available
            billing_days = computed_days if computed_days is not None else days

            # Determine daily price from rent + optional driver fee
            rent_fee = selected.get("rent_fee") or 0
            driver_fee = selected.get("driver_fee") or 0
            daily_price = rent_fee + (driver_fee if final_with_driver else 0)

            # Build totals
            driver_label = "Dengan Supir" if final_with_driver else "Tanpa Supir"
            subtotal = daily_price * billing_days

            calc = {
                "car_name": car_name,
                "with_driver": final_with_driver,
                "days": billing_days,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "start_display": fmt_dt(start_datetime),
                "end_display": fmt_dt(end_datetime),
                "start_display_id": fmt_dt_id_date(start_datetime),
                "end_display_id": fmt_dt_id_date(end_datetime),
                "img": selected.get("img") or "images/image_1.jpg",
                "daily_price": daily_price,
                "total_price": subtotal,
                "mandatory": mandatory,
            }
        # end if

        return render_template(
            "index.html",
            site_name        = "ALEXTRANS",
            hero_title       = "Sewa Mobil & City Tour Mudah dan Cepat",
            hero_subtitle    = "Armada lengkap, sopir profesional, harga transparan. Siap antar ke mana saja.",
            pricing          = pricing,
            calc             = calc,
            form_values      = {
                "car_name": car_name,
                "with_driver": "1" if with_driver else "0",
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "start_date": start_date,
                "start_time": start_time,
                "end_date": end_date,
                "end_time": end_time,
                "days": str(computed_days if computed_days is not None else days),
            },
        )
    # end def

# end class


