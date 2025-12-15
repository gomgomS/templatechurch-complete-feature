

import json
import time
import pymongo
import sys
import urllib.parse
import base64
import urllib
import ast
import pdfkit
import html as html_unescape
import os

from urllib.parse import urlencode

sys.path.append("pytavia_core")
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_storage")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_modules/auth")
sys.path.append("pytavia_modules/configuration")
sys.path.append("pytavia_modules/cookie")
sys.path.append("pytavia_modules/middleware")
sys.path.append("pytavia_modules/security")
sys.path.append("pytavia_modules/user")
sys.path.append("pytavia_modules/view")
sys.path.append("pytavia_modules/file_list")
sys.path.append("pytavia_modules/web_control")



##########################################################
from pytavia_core       import database
from pytavia_core       import config

from pytavia_stdlib     import utils
from pytavia_stdlib     import cfs_lib
from pytavia_stdlib     import idgen
from pytavia_stdlib     import sanitize
from pytavia_stdlib     import security_lib
from datetime           import date, timedelta


##########################################################
from configuration      import config_all
from configuration      import config_setting_security_timeout


from cookie             import cookie_engine
from middleware         import browser_security
from security           import security_login
from user               import user_proc

from view               import view_welcome
from view               import view_index
from view               import view_susunan_acara
from view               import view_triwulan
from booking            import booking_proc
from participant        import participant_proc
from participant        import participant_static_proc
from file_list          import file_list_proc
from web_control        import web_control_proc

##########################################################
# LANDINGPAGE
##########################################################
from flask              import request
from flask              import render_template
from flask              import Flask
from flask              import session
from flask              import make_response
from flask              import redirect
from flask              import url_for
from flask              import flash, get_flashed_messages
from flask              import abort
from flask              import jsonify 
from flask              import send_from_directory

from wtforms            import ValidationError

from flask_wtf.csrf     import CSRFProtect
from flask_wtf.csrf     import CSRFError
from flask_wtf.csrf     import generate_csrf

# from follow_up import follow_up_templates_proc
# from follow_up import follow_up_proc
#
# Main app configurations
#
app                   = Flask( __name__, config.G_STATIC_URL_PATH )
app.secret_key        = config.G_FLASK_SECRET
app.session_interface = cookie_engine.MongoSessionInterface()
csrf                  = CSRFProtect(app)
app.jinja_env.globals["csrf_token"] = generate_csrf

# Cache headers for static files
@app.after_request
def set_cache_headers(response):
    # Set cache headers for static assets (CSS, JS, images, fonts)
    if request.endpoint == 'static' or '/static/' in request.path:
        # Cache static assets for 1 year
        response.cache_control.max_age = 31536000  # 1 year in seconds
        response.cache_control.public = True
        response.cache_control.immutable = True
    # Set cache headers for HTML pages (shorter cache)
    elif request.endpoint in ['index', 'layanan', 'contact', 'gallery']:
        response.cache_control.max_age = 3600  # 1 hour
        response.cache_control.public = True
    return response

app.config['WTF_CSRF_TIME_LIMIT'] = 86400

# Increase CSRF token expiration time (e.g., 1 day)
app.config['WTF_CSRF_TIME_LIMIT'] = 86400  # in seconds

#
# Utility Function
#
# @app.errorhandler(CSRFError)
# def handle_csrf_error(e):
#     return redirect(url_for("login_html"))
# # end def


# @app.route("/")
# def landingpage():
#     fk_user_id  = session.get("fk_user_id")
#     params = request.form.to_dict()
#     # end if

#     html   = view_landing_page.view_landing_page().html( params )
#     return html

# @app.route("/")
# def index():
#     return view_welcome.view_welcome().html()

##########################################################
################# alextrans ################
##########################################################
@app.route("/")
def index():
    return view_index.view_index().html()

@app.route("/admin")
def contact():
    return render_template("admin/home.html")

@app.route("/admin/pengumuman")
def admin_pengumuman():
    return render_template("admin/pengumuman.html")

@app.route("/admin/susunan-acara")
def admin_susunan_acara():
    return view_susunan_acara.view_susunan_acara(app).html_dynamic()

@app.route("/admin/susunan-acara/save", methods=["POST"])
def admin_susunan_acara_save():
    return view_susunan_acara.view_susunan_acara(app).save_dynamic()

@app.route("/admin/susunan-acara-static")
def admin_susunan_acara_static():
    return view_susunan_acara.view_susunan_acara(app).html_static()

@app.route("/admin/susunan-acara-static/save", methods=["POST"])
def admin_susunan_acara_static_save():
    return view_susunan_acara.view_susunan_acara(app).save_static()

@app.route("/admin/triwulan")
def admin_triwulan():
    return view_triwulan.view_triwulan().html_triwulan()

@app.route("/admin/triwulan/<int:year>/<int:quarter>")
def admin_triwulan_detail(year, quarter):
    return view_triwulan.view_triwulan().html_triwulan_detail(year, quarter)

@app.route("/admin/triwulan/<int:year>/<int:quarter>/export/<string:kind>")
def admin_triwulan_export(year, quarter, kind):
    export_type = (request.args.get("type") or "pdf").lower()
    if export_type == "xlsx":
        if kind.lower() == "all":
            return view_triwulan.view_triwulan().export_triwulan_xlsx_all(year, quarter)
        return view_triwulan.view_triwulan().export_triwulan_xlsx(year, quarter, kind)
    # default PDF
    if kind.lower() == "all":
        return view_triwulan.view_triwulan().export_triwulan_pdf(year, quarter, "all")
    return view_triwulan.view_triwulan().export_triwulan_pdf(year, quarter, kind)

@app.route("/admin/file-list")
def admin_file_list():
    return file_list_proc.file_list_proc(app).html()

@app.route("/admin/file-list/upload", methods=["POST"])
def admin_file_list_upload():
    return file_list_proc.file_list_proc(app).upload()

@app.route("/admin/file-list/delete/<string:file_id>", methods=["POST"])
def admin_file_list_delete(file_id):
    return file_list_proc.file_list_proc(app).delete(file_id)

@app.route("/admin/web-control")
def admin_web_control():
    return web_control_proc.web_control_proc(app).html()

@app.route("/admin/web-control/save", methods=["POST"])
def admin_web_control_save():
    return web_control_proc.web_control_proc(app).save()

@app.route("/admin/web-control/delete-nav/<string:nav_key>", methods=["POST"])
def admin_web_control_delete_nav(nav_key):
    return web_control_proc.web_control_proc(app).delete_navigation(nav_key)

@app.route("/admin/blank")
def admin_blank():
    return render_template("admin/blank.html")

@app.route("/admin/login")
def admin_login():
    return render_template("admin/login.html")


@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


# FOR EXAMPLE ROUTE
# @csrf.exempt
# @app.route('/follow-up/history/add', methods=['POST'])
# @middleware_privilege
# def api_follow_up_history_add():
#     body                  = request.get_json() or {}
#     params                = sanitize.clean_html_dic(body)
#     params["fk_user_id"]  = session.get("fk_user_id")
#     response              = follow_up_proc.follow_up_proc(app).add(params)
#     return jsonify(response)
