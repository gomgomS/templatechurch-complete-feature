import sys
import traceback
import time

sys.path.append("pytavia_core")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_settings")

from pytavia_core   import database
from pytavia_core   import config
from pytavia_stdlib import idgen
import ast
from notification   import service_proc as notification_service


class follow_up_proc:

    mgdDB = database.get_db_conn(config.mainDB)

    def __init__(self, webapp):
        self.webapp = webapp
    # end def

    def list(self, params):
        call_id  = idgen._get_api_call_id()
        response = {
            "message_id": call_id,
            "message_action": "FOLLOW UP HISTORY LIST",
            "message_code": "0",
            "message_title": "",
            "message_desc": "",
            "message_data": []
        }
        try:
            fk_user_id      = params.get("fk_user_id")
            transaction_id  = params.get("transaction_id")
            if not fk_user_id or not transaction_id:
                response["message_code"] = "400"
                response["message_title"] = "Bad Request"
                response["message_desc"] = "fk_user_id and transaction_id are required"
                return response
            # end if

            query = {"fk_user_id": fk_user_id, "transaction_id": transaction_id}

            projection = {
                "_id": 0,
                "template_title": 1,
                "message_sent": 1,
                "timestamp": 1,
                "rec_timestamp": 1,
                "rec_timestamp_str": 1
            }
            items = list(self.mgdDB.db_follow_up_history.find(query, projection).sort("rec_timestamp", -1))

            response["message_data"] = items
        except Exception:
            log = database.new(self.mgdDB, "db_logs")
            log.put("source", "ERROR_LIST_FOLLOW_UP_HISTORY")
            log.put("content", traceback.format_exc())
            log.insert()
            response["message_code"] = "500"
            response["message_title"] = "Internal Error"
            response["message_desc"] = "Internal error"
        return response
    # end def

    def add(self, params):
        call_id  = idgen._get_api_call_id()
        response = {
            "message_id": call_id,
            "message_action": "FOLLOW UP HISTORY ADD",
            "message_code": "0",
            "message_title": "",
            "message_desc": "",
            "message_data": {}
        }
        try:
            fk_user_id     = params.get("fk_user_id")
            transaction_id = params.get("transaction_id")
            customer_name  = params.get("customer_name", "")
            customer_phone = params.get("customer_phone", "")
            template_title = params.get("template_title", "")
            message_sent   = params.get("message_sent", "")

            if not fk_user_id or not transaction_id or not message_sent:
                response["message_code"] = "400"
                response["message_title"] = "Bad Request"
                response["message_desc"] = "fk_user_id, transaction_id and message_sent are required"
                return response
            # end if

            # Try to send WhatsApp message if receiver phone is provided
            is_success = False
            error_desc = ""
            if customer_phone and message_sent:
                # Change first digit from 0 to 62
                customer_phone_62 = customer_phone
                if customer_phone.startswith('0'):
                    customer_phone_62 = '62' + customer_phone[1:]

                try:
                    # 1) Check existing WhatsApp notification logs for this receiver
                    existing_log = self.mgdDB.db_whatsapp_notification_logs.find_one({
                        "request.receiver": {"$in": [customer_phone, customer_phone_62]}
                    }, sort=[("rec_timestamp", -1)])
                    
                    # If there's a recent log with "receiver number is not exists" error, skip sending
                    if existing_log and existing_log.get('response', {}).get('message_data', {}).get('message') == 'The receiver number is not exists.':
                        is_success = False
                        error_desc = 'The receiver number is not exists.'
                    else:
                        # 2) Find user's WhatsApp device (sender)
                        device_rec = self.mgdDB.db_whatsapp_devices.find_one({
                            'fk_user_id': fk_user_id,
                            'deleted_at': None
                        }, { '_id': 0 })

                        if device_rec is not None:
                            # Use whatsapp.send() which handles token and session internally
                            req_wa = {
                                'fk_user_id': fk_user_id,
                                'phone_number': [customer_phone],
                                'template': {
                                    'blast_message': message_sent,
                                    'attachment_type': '',
                                    'attachment_url': ''
                                },
                                'device_rec': device_rec
                            }
                            resp_send = notification_service.whatsapp(self.webapp).send(req_wa)
                            
                            # 3) Check logs again after sending to verify actual result
                            time.sleep(3)  # Wait a moment for log to be written
                            latest_log = self.mgdDB.db_whatsapp_notification_logs.find_one({
                                "request.receiver": {"$in": [customer_phone, customer_phone_62]}
                            }, sort=[("rec_timestamp", -1)])
                            
                            # If latest log shows "receiver number is not exists", use that error
                            if latest_log and latest_log.get('response', {}).get('message_data', {}).get('message') == 'The receiver number is not exists.':
                                is_success = False
                                error_desc = 'The receiver number is not exists.'
                            else:
                                # Use original response logic
                                is_success = (
                                    str(resp_send.get('message_code')) in ['0', '00'] and
                                    not str(resp_send.get('message_action', '')).endswith('FAILED')
                                )
                                if not is_success:
                                    # Derive a friendly error message when session is missing
                                    try:
                                        resp_action = str(resp_send.get('message_action', ''))
                                        resp_desc   = resp_send.get('message_desc', '')
                                        desc_str    = str(resp_desc)
                                        if 'GET_SESSION_FAILED' in resp_action or 'GET_SESSION_FAILED' in desc_str:
                                            inner_desc = ''
                                            try:
                                                if isinstance(resp_desc, dict):
                                                    inner_desc = resp_desc.get('message_desc', '')
                                                else:
                                                    inner_obj = ast.literal_eval(desc_str)
                                                    if isinstance(inner_obj, dict):
                                                        inner_desc = inner_obj.get('message_desc', '')
                                            except Exception:
                                                inner_desc = ''
                                            error_desc = inner_desc or 'Session not found. Please scan device first'
                                        else:
                                            error_desc = 'SEND_FAILED: ' + str(resp_send)
                                    except Exception:
                                        error_desc = 'SEND_FAILED'
                        else:
                            error_desc = "DEVICE_NOT_FOUND for fk_user_id=" + str(fk_user_id)
                            # end if
                        # end if
                    # end if
                except Exception:
                    error_desc = "EXCEPTION: " + traceback.format_exc()
            # end if

            now_int = int(time.time())
            now_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_int))

            rec = database.new(self.mgdDB, "db_follow_up_history")
            rec.put("fk_user_id"        , fk_user_id)
            rec.put("transaction_id"    , transaction_id or "")
            rec.put("customer_name"     , customer_name)
            rec.put("customer_phone"    , customer_phone)
            rec.put("template_title"    , template_title)
            rec.put("message_sent"      , message_sent)
            rec.put("timestamp"         , now_str)
            rec.put("rec_timestamp"     , now_int)
            rec.put("rec_timestamp_str" , now_str)
            rec.put("is_success"        , is_success)
            rec.put("error_desc"        , error_desc)
            rec.insert()

            # Build response status for UI notification
            if is_success:
                response["message_action"] = "FOLLOW UP SEND SUCCESS"
                response["message_code"]   = "00"
                response["message_title"]  = "Success"
                response["message_desc"]   = "WhatsApp message has been sent successfully."
            else:
                response["message_action"] = "FOLLOW UP SEND FAILED"
                response["message_code"]   = "01"
                response["message_title"]  = "Failed"
                response["message_desc"]   = "WhatsApp message failed to send."

            response["message_data"] = {"pkey": rec.get().get("pkey"), "is_success": is_success, "error_desc": error_desc}
        except Exception:
            log = database.new(self.mgdDB, "db_logs")
            log.put("source", "ERROR_ADD_FOLLOW_UP_HISTORY")
            log.put("content", traceback.format_exc())
            log.insert()
            response["message_code"] = "500"
            response["message_title"] = "Internal Error"
            response["message_desc"] = "Internal error"
        return response
    # end def


