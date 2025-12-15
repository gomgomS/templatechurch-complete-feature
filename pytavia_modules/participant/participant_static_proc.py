import os
import json

from pytavia_core import config


class participant_static_proc:
    """
    Handle load/save of static participant data stored as JSON per tab.
    """

    def __init__(self):
        # Anchor to the project root where this module lives, not the process CWD
        project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.base_dir = os.path.join(project_root, "static", "json_file")
        os.makedirs(self.base_dir, exist_ok=True)

    def normalize_tab(self, tab_in: str) -> str:
        tab = (tab_in or "khotbah").lower()
        if tab not in ("khotbah", "ss", "rabu", "vesper"):
            tab = "khotbah"
        return {
            "khotbah": "khotbah",
            "ss": "sekolah_sabat",
            "sekolah_sabat": "sekolah_sabat",
            "rabu": "rabu_malam",
            "rabu_malam": "rabu_malam",
            "vesper": "vesper",
        }.get(tab, "khotbah")

    def load(self, tab_key: str) -> dict:
        """
        Load a static participant payload from json_file directory.
        """
        try:
            fp = os.path.join(self.base_dir, f"{tab_key}.json")
            if not os.path.exists(fp):
                return {}
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            try:
                print("[participant_static_proc.load] error:", str(e))
            except Exception:
                pass
            return {}

    def save(self, tab_key: str, payload: dict):
        """
        Persist a static participant payload into json_file directory.
        """
        try:
            fp = os.path.join(self.base_dir, f"{tab_key}.json")
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"[participant_static_proc.save] saved {fp}")
        except Exception as e:
            try:
                print("[participant_static_proc.save] error:", str(e))
            except Exception:
                pass

    def build_payload(self, tab_key: str, params: dict) -> dict:
        """
        Map sanitized form params to static payload per tab.
        """
        if tab_key == "khotbah":
            return {
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
        if tab_key == "sekolah_sabat":
            return {
                "pemimpin_acara": params.get("pemimpin_acara", ""),
                "ayat_hafalan_dan_doa": params.get("ayat_hafalan_doa", ""),
                "berita_mission": params.get("berita_mission", ""),
                "pemimpin_lagu": params.get("pemimpin_lagu", ""),
                "pianis": params.get("pianis", ""),
                "lagu_pujian": params.get("lagu_pujian", ""),
                "pelayanan_perorangan": params.get("pelayanan_perorangan", ""),
                "rumah_tangga": params.get("rumah_tangga", ""),
            }
        if tab_key in ("rabu_malam", "vesper"):
            return {
                "renungan": params.get("renungan", ""),
                "protokol": params.get("protokol", ""),
                "pianis": params.get("pianis", ""),
                "pemimpin_lagu": params.get("pemimpin_lagu", ""),
                "lagu_pujian": params.get("lagu_pujian", ""),
            }
        return {}

# end class


