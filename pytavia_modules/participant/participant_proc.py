import sys
import calendar
from datetime import date, timedelta, datetime

sys.path.append("pytavia_core")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_storage")

from pytavia_core import database
from pytavia_core import config


class participant_proc:

    mgdDB = database.get_db_conn(config.mainDB)

    def __init__(self, app):
        self.webapp = app
    # end def

    def update(self, params):
        """
        Public entry that mirrors 'profile_proc.update' style.
        Accepts sanitized form params and upserts participant schedule.
        """
        try:
            print("[participant_proc.update] incoming_params:", dict(params))
        except Exception:
            pass
        return self._participant_upsert(params)
    # end def

    def _compute_week_dates(self, year: int, quarter: int, week_index: int):
        q = 1 if quarter not in (1, 2, 3, 4) else quarter
        first_month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
        months_span = [first_month, first_month + 1, first_month + 2]
        start_date = date(year, months_span[0], 1)
        last_day = calendar.monthrange(year, months_span[-1])[1]
        end_date = date(year, months_span[-1], last_day)
        # first Saturday in quarter
        cur = start_date
        while cur.weekday() != 5 and cur <= end_date:
            cur += timedelta(days=1)
        # target Saturday for this week (1..13)
        sat = cur + timedelta(days=7 * max(0, int(week_index) - 1))
        # week Sunday..Saturday
        sun = sat - timedelta(days=6)
        try:
            print(f"[participant_proc._compute_week_dates] year={year} quarter={q} week_index={week_index} -> sun={sun} sat={sat}")
        except Exception:
            pass
        return sun.strftime("%Y-%m-%d"), sat.strftime("%Y-%m-%d")
    # end def

    def _participant_upsert(self, params):
        """
        Create or update a participant schedule row for a specific (year, quarter, week_index).
        Expects params including:
          - year, quarter, week_index (1..13), tab in {khotbah, ss, rabu, vesper}
          - fields per tab (see mappings below)
        """
        response = {"status": "FAILED", "desc": "", "data": {}}
        try:
            year = int(params.get("year", 0))
            quarter = int(params.get("quarter", 0))
            week_index = int(params.get("week_index", 0))
            tab_in = (params.get("tab") or "").strip().lower()
            print(f"[participant_proc.upsert] parsed: year={year}, quarter={quarter}, week_index={week_index}, tab={tab_in}")

            if not (year and quarter in (1, 2, 3, 4) and 1 <= week_index <= 13):
                response["desc"] = "Invalid year/quarter/week_index"
                print("[participant_proc.upsert] validation_failed:", response["desc"])
                return response

            # Compute week dates (Sunday..Saturday)
            start_date_str, end_date_str = self._compute_week_dates(year, quarter, week_index)

            # Normalize tab to participant subdocument key and build payload
            tab_key = None
            payload = {}
            if tab_in == "khotbah":
                tab_key = "khotbah"
                payload = {
                    "pelayanan": params.get("pelayanan", ""),
                    "protokol": params.get("protokol", ""),
                    "pendamping": params.get("pendamping", ""),
                    "cerita_anak_anak": params.get("cerita_anak", ""),
                    "pemimpin_lagu": params.get("pemimpin_lagu", ""),
                    "pianist": params.get("pianist", ""),
                    "backing_vocal": params.get("backing_vocal", ""),
                    "khotbah_dan_ss": params.get("khotbah_ss", ""),
                    "lagu_pujian": params.get("lagu_pujian", ""),
                    "diakon_diakones": params.get("diakon", ""),
                    "penerima_tamu": params.get("penerima_tamu", ""),
                }
            elif tab_in in ("ss", "sekolah_sabat", "sekolah-sabat"):
                tab_key = "sekolah_sabat"
                payload = {
                    "pemimpin_acara": params.get("pemimpin_acara", ""),
                    "ayat_hafalan_dan_doa": params.get("ayat_hafalan_doa", ""),
                    "berita_mission": params.get("berita_mission", ""),
                    "pemimpin_lagu": params.get("pemimpin_lagu", ""),
                    "pianis": params.get("pianis", ""),
                    "lagu_pujian": params.get("lagu_pujian", ""),
                    "pelayanan_perorangan": params.get("pelayanan_perorangan", ""),
                    "rumah_tangga": params.get("rumah_tangga", ""),
                }
            elif tab_in in ("rabu", "rabu_malam"):
                tab_key = "rabu_malam"
                payload = {
                    "renungan": params.get("renungan", ""),
                    "protokol": params.get("protokol", ""),
                    "pianis": params.get("pianis", ""),
                    "pemimpin_lagu": params.get("pemimpin_lagu", ""),
                    "lagu_pujian": params.get("lagu_pujian", ""),
                }
            elif tab_in in ("vesper", "jumat"):
                tab_key = "vesper"
                payload = {
                    "renungan": params.get("renungan", ""),
                    "protokol": params.get("protokol", ""),
                    "pianis": params.get("pianis", ""),
                    "pemimpin_lagu": params.get("pemimpin_lagu", ""),
                    "lagu_pujian": params.get("lagu_pujian", ""),
                }
            else:
                tab_key = "khotbah"

            print(f"[participant_proc.upsert] tab_key={tab_key} payload:", payload)

            # Try update existing
            query = {"year": year, "quarter": quarter, "week_index": week_index}
            print("[participant_proc.upsert] query:", query)
            existing = self.mgdDB.db_participant_schedule.find_one(query)
            print("[participant_proc.upsert] existing_found:", existing is not None)
            if existing:
                set_fields = {
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    f"participant.{tab_key}": payload,
                }
                result = self.mgdDB.db_participant_schedule.update_one(query, {"$set": set_fields})
                try:
                    print(
                        "[participant_proc.upsert] update_one matched_count:",
                        getattr(result, "matched_count", None),
                        "modified_count:",
                        getattr(result, "modified_count", None),
                    )
                except Exception:
                    pass
                updated = self.mgdDB.db_participant_schedule.find_one(query, {"_id": 0})
                response["status"] = "SUCCESS"
                response["data"] = updated or {}
                return response

            # Create new doc via upsert (no dependency on database.new)
            part = {
                "khotbah": {
                    "pelayanan": "",
                    "protokol": "",
                    "pendamping": "",
                    "cerita_anak_anak": "",
                    "pemimpin_lagu": "",
                    "pianist": "",
                    "backing_vocal": "",
                    "khotbah_dan_ss": "",
                    "lagu_pujian": "",
                    "diakon_diakones": "",
                    "penerima_tamu": "",
                },
                "sekolah_sabat": {
                    "pemimpin_acara": "",
                    "ayat_hafalan_dan_doa": "",
                    "berita_mission": "",
                    "pemimpin_lagu": "",
                    "pianis": "",
                    "lagu_pujian": "",
                    "pelayanan_perorangan": "",
                    "rumah_tangga": "",
                },
                "rabu_malam": {
                    "renungan": "",
                    "protokol": "",
                    "pianis": "",
                    "pemimpin_lagu": "",
                    "lagu_pujian": "",
                },
                "vesper": {
                    "renungan": "",
                    "protokol": "",
                    "pianis": "",
                    "pemimpin_lagu": "",
                    "lagu_pujian": "",
                },
            }
            part[tab_key] = payload
            set_doc = {
                "year": year,
                "quarter": quarter,
                "week_index": week_index,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "participant": part,
            }
            res = self.mgdDB.db_participant_schedule.update_one(query, {"$set": set_doc}, upsert=True)
            try:
                print(
                    "[participant_proc.upsert] upsert insert, matched_count:",
                    getattr(res, "matched_count", None),
                    "upserted_id:", getattr(res, "upserted_id", None),
                )
            except Exception:
                pass

            created = self.mgdDB.db_participant_schedule.find_one(query, {"_id": 0})
            print("[participant_proc.upsert] created_doc_found:", created is not None)
            response["status"] = "SUCCESS"
            response["data"] = created or {}
            return response
        except Exception as e:
            try:
                print("[participant_proc.upsert] exception:", str(e))
            except Exception:
                pass
            response["desc"] = f"ERROR: {e}"
            return response
    # end def

# end class




