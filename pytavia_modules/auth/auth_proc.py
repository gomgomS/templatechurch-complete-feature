import sys
import traceback
import datetime
import time
import ast # use to convert string to dictionary 
from   datetime import datetime
import random
import string
import hashlib

from view   import view_index

sys.path.append("pytavia_core"    )
sys.path.append("pytavia_modules" )
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib"  )
sys.path.append("pytavia_storage" )

from pytavia_stdlib import idgen
from pytavia_stdlib import utils
from pytavia_core   import database
from pytavia_core   import config
from uuid     import uuid4
from flask import request 
from flask          import render_template

class auth_proc:

    mgdDB = database.get_db_conn(config.mainDB)

    def __init__(self, app):
        self.webapp = app
    # end def
        
                                                                                                                                                                                                                                                                   
    def login_html(self, params):
        return render_template(
            "admin/login.html",           
        )
    #end def
        

    def hash_password(self, password):
            return hashlib.sha256(password.encode()).hexdigest()
            

    def login(self, params):
        STATIC_USER = {
            "username": "admin",
            "password_hash": hashlib.sha256("mysecret".encode()).hexdigest(),
            "role": "admin",
            "user_uuid": "static-uuid",
            "email": "admin@example.com"
        }
        username = params.get("username", "")
        password = params.get("password", "")
        hashed = self.hash_password(password)

        if username == STATIC_USER["username"] and hashed == STATIC_USER["password_hash"]:
            return {
                "message_action": "LOGIN_SUCCESS",
                "message_data": {
                    "fk_user_id": STATIC_USER["user_uuid"],
                    "username": STATIC_USER["username"],
                    "role": STATIC_USER["role"],
                    "user_uuid": STATIC_USER["user_uuid"],
                    "email": STATIC_USER["email"],
                }
            }
        else:
            return {
                "message_action": "LOGIN_FAILED",
                "message_title": "Login Failed",
                "message_desc": "Username and Password Not Match",
                "message_data": {}
            }

        

    # end class


