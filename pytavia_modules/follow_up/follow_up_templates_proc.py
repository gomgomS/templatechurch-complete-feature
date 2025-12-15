import sys
import traceback
import time
import datetime
from datetime import datetime

sys.path.append("pytavia_core")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_settings")

from pytavia_core   import database
from pytavia_core   import config
from pytavia_stdlib import idgen
from notification   import whatsapp_proc


class follow_up_templates_proc:

    mgdDB = database.get_db_conn(config.mainDB)

    def __init__(self, webapp):
        self.webapp = webapp
    # end def

    def add(self, params):
        call_id = idgen._get_api_call_id()
        response = {
            "message_id": call_id,
            "message_action": "ADD TEMPLATE SUCCESS",
            "message_code": "0",
            "message_title": "",
            "message_desc": "",
            "message_data": {}
        }

        try:
            fk_user_id    = params.get("fk_user_id")
            template_text = params.get("template_text")
            is_active     = params.get("is_active", True)
            template_title = params.get("template_title", "")

            # Check for missing, empty, or whitespace-only values
            if not fk_user_id or not template_text or not template_title or not template_text.strip() or not template_title.strip():
                response["message_action"] = "ADD TEMPLATE FAILED"
                response["message_desc"] = "Template title and message cannot be empty or contain only spaces"
                return response
            # end if

            # Enforce maximum of 10 templates per user
            try:
                existing_count = self.mgdDB.db_follow_up_templates.count({
                    "fk_user_id": fk_user_id
                }, {})
            except Exception:
                # Fallback if count signature differs
                existing_count = self.mgdDB.db_follow_up_templates.find({"fk_user_id": fk_user_id}).count()
            if existing_count >= 10:
                response["message_action"] = "ADD TEMPLATE FAILED"
                response["message_desc"] = "Maximum 10 templates allowed"
                return response
            # end if

            # very naive variable extraction like {{var}}
            variables = []
            try:
                import re
                variables = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", template_text or "")
            except Exception:
                variables = []

            iso_now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            rec = database.new(self.mgdDB, "db_follow_up_templates")
            rec.put("fk_user_id", fk_user_id)
            rec.put("template_id", rec.get()["pkey"])  # mirror pkey for quick lookup
            rec.put("template_title", template_title)
            rec.put("template_text", template_text)
            rec.put("variables", variables)
            rec.put("is_active", bool(is_active))
            rec.put("created_at", iso_now)
            rec.put("updated_at", iso_now)
            inserted_id = rec.insert()
            template_id = rec.get().get("pkey")

            response["message_action"] = "ADD TEMPLATE SUCCESS"
            response["message_desc"] = "Template berhasil ditambahkan"
            response["message_data"] = {
                "_id": inserted_id,
                "template_id": template_id,
                "fk_user_id": fk_user_id,
                "template_title": template_title,
                "template_text": template_text,
                "created_at": iso_now,
                "updated_at": iso_now,
                "is_active": bool(is_active)
            }
        except Exception:
            log = database.new(self.mgdDB, "db_logs")
            log.put("source", "ERROR_ADD_FOLLOW_UP_TEMPLATE")
            log.put("content", traceback.format_exc())
            log.insert()

            response["message_action"] = "ADD TEMPLATE FAILED"
            response["message_desc"] = "Internal error"
        # end try
        return response
    # end def

    def list(self, params):
        call_id = idgen._get_api_call_id()
        response = {
            "message_id": call_id,
            "message_action": "LIST TEMPLATE SUCCESS",
            "message_code": "0",
            "message_title": "",
            "message_desc": "",
            "message_data": {}
        }

        try:
            fk_user_id = params.get("fk_user_id")
            include_deleted = bool(params.get("include_deleted", False))
            is_active = params.get("is_active")

            # Check if user has premium subscription
            is_premium = self._is_premium(fk_user_id)
            if not is_premium:
                response["message_action"] = "LIST TEMPLATE SUCCESS"
                response["message_desc"] = "Please upgrade to premium to use follow-up templates"
                response["message_data"] = {
                    "device_connected": True,   
                    "is_premium": False,
                    "redirect_url": "/admin/settings"
                }
                return response

            # Check if device session is false or doesn't exist
            device_rec              = self._find_device(params)
            if not device_rec or not device_rec.get('device_sessions', False):
                response["message_action"] = "LIST TEMPLATE SUCCESS"
                response["message_desc"] = "Please connect your WhatsApp blast first"
                response["message_data"] = {
                    "device_connected": False,
                    "redirect_url": "/admin/whatsapp-blast"
                }
                return response

            if not fk_user_id:
                response["message_action"] = "LIST TEMPLATE FAILED"
                response["message_desc"] = "Missing fk_user_id"
                response["message_data"] = []
                return response

            query = {"fk_user_id": fk_user_id}
            if not include_deleted:
                query.update({
                    "$or": [
                        {"deleted_at": None},
                        {"deleted_at": {"$exists": False}}
                    ]
                })
            if is_active is not None:
                try:
                    query.update({"is_active": bool(is_active)})
                except Exception:
                    pass

            docs = list(self.mgdDB.db_follow_up_templates.find(query).sort("_id", -1))
            data = []
            for d in docs:
                templ_id = d.get("template_id") or d.get("pkey") or str(d.get("_id"))
                # derive display title if missing
                raw_title = (d.get("template_title", "") or "").strip()
                if not raw_title:
                    txt = (d.get("template_text") or "").strip()
                    first_line = txt.splitlines()[0] if txt else ""
                    raw_title = (first_line[:60] + ("..." if len(first_line) > 60 else "")) if first_line else "Untitled"
                data.append({
                    "_id": str(d.get("_id")),
                    "template_id": templ_id,
                    "fk_user_id": d.get("fk_user_id"),
                    "template_title": raw_title,
                    "template_text": d.get("template_text"),
                    "created_at": d.get("created_at"),
                    "updated_at": d.get("updated_at"),
                    "is_active": d.get("is_active", True)
                })
            response["message_action"] = "LIST TEMPLATE SUCCESS"
            response["message_desc"] = "OK"
            response["message_data"] = data
        except Exception:
            log = database.new(self.mgdDB, "db_logs")
            log.put("source", "ERROR_LIST_FOLLOW_UP_TEMPLATE")
            log.put("content", traceback.format_exc())
            log.insert()
            response["message_action"] = "LIST TEMPLATE FAILED"
            response["message_desc"] = "Internal error"
            response["message_data"] = []
        return response
    # end def

    def get(self, params):
        call_id = idgen._get_api_call_id()
        response = {
            "message_id": call_id,
            "message_action": "GET TEMPLATE SUCCESS",
            "message_code": "0",
            "message_title": "",
            "message_desc": "",
            "message_data": {}
        }
        try:
            fk_user_id = params.get("fk_user_id")
            template_id = params.get("id")
            if not fk_user_id or not template_id:
                response["message_action"] = "GET TEMPLATE FAILED"
                response["message_desc"] = "Missing fk_user_id or id"
                return response

            doc = self.mgdDB.db_follow_up_templates.find_one({"template_id": template_id, "fk_user_id": fk_user_id})

            if not doc:
                response["message_action"] = "GET TEMPLATE FAILED"
                response["message_desc"] = "Template tidak ditemukan"
                return response

            templ_id = doc.get("template_id") or doc.get("pkey") or str(doc.get("_id"))
            # derive display title if missing
            raw_title = (doc.get("template_title", "") or "").strip()
            if not raw_title:
                txt = (doc.get("template_text") or "").strip()
                first_line = txt.splitlines()[0] if txt else ""
                raw_title = (first_line[:60] + ("..." if len(first_line) > 60 else "")) if first_line else "Untitled"
            data = {
                "_id": str(doc.get("_id")),
                "template_id": templ_id,
                "fk_user_id": doc.get("fk_user_id"),
                "template_title": raw_title,
                "template_text": doc.get("template_text"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
                "is_active": doc.get("is_active", True)
            }
            response["message_action"] = "GET TEMPLATE SUCCESS"
            response["message_desc"] = "OK"
            response["message_data"] = data
        except Exception:
            log = database.new(self.mgdDB, "db_logs")
            log.put("source", "ERROR_GET_FOLLOW_UP_TEMPLATE")
            log.put("content", traceback.format_exc())
            log.insert()
            response["message_action"] = "GET TEMPLATE FAILED"
            response["message_desc"] = "Internal error"
        return response
    # end def

    def update(self, params):
        call_id = idgen._get_api_call_id()
        response = {
            "message_id": call_id,
            "message_action": "UPDATE TEMPLATE SUCCESS",
            "message_code": "0",
            "message_title": "",
            "message_desc": "",
            "message_data": {}
        }
        try:
            fk_user_id = params.get("fk_user_id")
            template_id = params.get("id")
            template_text = params.get("template_text")
            template_title = params.get("template_title")
            is_active = params.get("is_active")

            # Check for missing, empty, or whitespace-only values
            if not fk_user_id or not template_text or not template_title or not template_text.strip() or not template_title.strip():
                response["message_action"] = "ADD TEMPLATE FAILED"
                response["message_desc"] = "Template title and message cannot be empty or contain only spaces"
                return response

            # find
            doc = self.mgdDB.db_follow_up_templates.find_one({"template_id": template_id, "fk_user_id": fk_user_id})
            if not doc:
                response["message_action"] = "UPDATE TEMPLATE FAILED"
                response["message_desc"] = "Template tidak ditemukan"
                return response

            update_doc = {}
            if template_title is not None:
                update_doc["template_title"] = template_title
            if template_text is not None:
                update_doc["template_text"] = template_text
            if is_active is not None:
                update_doc["is_active"] = bool(is_active)
            update_doc["updated_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

            if update_doc:
                self.mgdDB.db_follow_up_templates.update_one({"template_id": template_id, "fk_user_id": fk_user_id}, {"$set": update_doc})

            updated = self.mgdDB.db_follow_up_templates.find_one({"template_id": template_id, "fk_user_id": fk_user_id})
            templ_id = updated.get("template_id") or updated.get("pkey") or str(updated.get("_id"))
            # derive display title if missing
            raw_title = (updated.get("template_title", "") or "").strip()
            if not raw_title:
                txt = (updated.get("template_text") or "").strip()
                first_line = txt.splitlines()[0] if txt else ""
                raw_title = (first_line[:60] + ("..." if len(first_line) > 60 else "")) if first_line else "Untitled"
            data = {
                "_id": str(updated.get("_id")),
                "template_id": templ_id,
                "fk_user_id": updated.get("fk_user_id"),
                "template_title": raw_title,
                "template_text": updated.get("template_text"),
                "created_at": updated.get("created_at"),
                "updated_at": updated.get("updated_at"),
                "is_active": updated.get("is_active", True)
            }
            response["message_action"] = "UPDATE TEMPLATE SUCCESS"
            response["message_desc"] = "Template berhasil diubah"
            response["message_data"] = data
        except Exception:
            log = database.new(self.mgdDB, "db_logs")
            log.put("source", "ERROR_UPDATE_FOLLOW_UP_TEMPLATE")
            log.put("content", traceback.format_exc())
            log.insert()
            response["message_action"] = "UPDATE TEMPLATE FAILED"
            response["message_desc"] = "Internal error"
        return response
    # end def

    def delete(self, params):
        call_id = idgen._get_api_call_id()
        response = {
            "message_id": call_id,
            "message_action": "DELETE TEMPLATE SUCCESS",
            "message_code": "0",
            "message_title": "",
            "message_desc": "",
            "message_data": {}
        }
        try:
            fk_user_id = params.get("fk_user_id")
            template_id = params.get("id")
            if not fk_user_id or not template_id:
                response["message_action"] = "DELETE TEMPLATE FAILED"
                response["message_desc"] = "Missing fk_user_id or id"
                return response

            # find by template_id only
            doc = self.mgdDB.db_follow_up_templates.find_one({"template_id": template_id, "fk_user_id": fk_user_id})
            if not doc:
                response["message_action"] = "DELETE TEMPLATE FAILED"
                response["message_desc"] = "Template tidak ditemukan"
                return response

            # hard delete
            self.mgdDB.db_follow_up_templates.delete_one({"template_id": template_id, "fk_user_id": fk_user_id})

            # include info of the deleted template (snapshot before deletion)
            response["message_action"] = "DELETE TEMPLATE SUCCESS"
            response["message_desc"] = "Template berhasil dihapus"
            templ_id = doc.get("template_id") or doc.get("pkey") or str(doc.get("_id"))
            # derive display title if missing
            raw_title = (doc.get("template_title", "") or "").strip()
            if not raw_title:
                txt = (doc.get("template_text") or "").strip()
                first_line = txt.splitlines()[0] if txt else ""
                raw_title = (first_line[:60] + ("..." if len(first_line) > 60 else "")) if first_line else "Untitled"
            response["message_data"] = {
                "_id": str(doc.get("_id")),
                "template_id": templ_id,
                "fk_user_id": doc.get("fk_user_id"),
                "template_title": raw_title,
                "template_text": doc.get("template_text"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
                "is_active": doc.get("is_active", True)
            }
        except Exception:
            log = database.new(self.mgdDB, "db_logs")
            log.put("source", "ERROR_DELETE_FOLLOW_UP_TEMPLATE")
            log.put("content", traceback.format_exc())
            log.insert()
            response["message_action"] = "DELETE TEMPLATE FAILED"
            response["message_desc"] = "Internal error"
        return response
    # end def

    def _is_premium(self, fk_user_id):
        """Check if user has premium subscription"""
        response = False
        user_auth = self.mgdDB.db_user_auth.find_one({"fk_user_id": fk_user_id})
        date_now = datetime.now()
        premium_user = self.mgdDB.db_user_package.find_one({
            "fk_user_id": fk_user_id,
            "is_pay": True,
            "end_date": {"$gte": date_now}
        })
        if premium_user:
            response = True
        # end if
        return response
    # end def

    def _find_device(self, params):
        fk_user_id = params["fk_user_id"]

        device_rec = self.mgdDB.db_whatsapp_devices.find_one({
            'fk_user_id': fk_user_id,
            'deleted_at': None
        }, {
            '_id': 0,
            'device_id': 1
        })

        if device_rec:
            whatsapp_session = whatsapp_proc.whatsapp_notif(self.webapp).check_session({
                'fk_user_id': fk_user_id,
                'device_id': device_rec['device_id']
            })

            if whatsapp_session['message_action'] == 'PROCESS_SUCCESS':
                device_session = False
                try:
                    whatsapp_session_resp_data = whatsapp_session['message_data']['responseDescription']['data']['status']
                    device_session = True if whatsapp_session_resp_data == 'authenticated' else False
                except:
                    self.webapp.logger.debug(traceback.format_exc())
                device_rec['device_sessions'] = device_session

        return device_rec
    # end def



