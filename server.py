

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
import random

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
from auth               import auth_proc

from view               import view_welcome
from view               import view_index
from view               import view_susunan_acara
from view               import view_triwulan
from booking            import booking_proc
from participant        import participant_proc
from participant        import participant_static_proc
from file_list          import file_list_proc
from file_list          import file_list_static_proc
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
# Set permanent session lifetime to 24 hours
app.permanent_session_lifetime = timedelta(hours=24)
csrf                  = CSRFProtect(app)
app.jinja_env.globals["csrf_token"] = generate_csrf

# Helper function to render HTML editor content
def render_html_editor(data):
    """
    Render HTML editor block
    
    Args:
        data: string (HTML) or dict with 'html' key (legacy format)
    
    Returns:
        str: HTML content
    """
    # Handle string format (new, simple format)
    if isinstance(data, str):
        return data
    
    # Handle legacy object format with 'html' key
    if isinstance(data, dict):
        return data.get('html', '')
    
    return ""

# Register as Jinja2 filter
app.jinja_env.filters['render_html_editor'] = render_html_editor
app.jinja_env.globals['render_html_editor'] = render_html_editor

# Cache headers for static files and pages
@app.after_request
def set_cache_headers(response):
    # Prevent caching for index page and admin pages to ensure fresh content
    if request.endpoint == 'index' or request.path == '/':
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
        response.cache_control.max_age = 0
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    # Prevent caching for admin web control page
    elif 'admin/web-control' in request.path:
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
        response.cache_control.max_age = 0
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    # Set cache headers for static assets (CSS, JS, images, fonts)
    elif request.endpoint == 'static' or '/static/' in request.path:
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
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    # return render_template("admin/home.html")
    return web_control_proc.web_control_proc(app).html()

@app.route("/admin/pengumuman")
def admin_pengumuman():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return render_template("admin/pengumuman.html")

@app.route("/admin/susunan-acara")
def admin_susunan_acara():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return view_susunan_acara.view_susunan_acara(app).html_dynamic()

@app.route("/admin/susunan-acara/save", methods=["POST"])
def admin_susunan_acara_save():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return view_susunan_acara.view_susunan_acara(app).save_dynamic()

@app.route("/admin/susunan-acara-static")
def admin_susunan_acara_static():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return view_susunan_acara.view_susunan_acara(app).html_static()

@app.route("/admin/susunan-acara-static/save", methods=["POST"])
def admin_susunan_acara_static_save():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return view_susunan_acara.view_susunan_acara(app).save_static()

@app.route("/admin/triwulan")
def admin_triwulan():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return view_triwulan.view_triwulan().html_triwulan()

@app.route("/admin/triwulan/<int:year>/<int:quarter>")
def admin_triwulan_detail(year, quarter):
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return view_triwulan.view_triwulan().html_triwulan_detail(year, quarter)

@app.route("/admin/triwulan/<int:year>/<int:quarter>/export/<string:kind>")
def admin_triwulan_export(year, quarter, kind):
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
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
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return file_list_proc.file_list_proc(app).html()

@app.route("/admin/file-list/upload", methods=["POST"])
def admin_file_list_upload():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return file_list_proc.file_list_proc(app).upload()

@app.route("/admin/file-list/delete/<string:file_id>", methods=["POST"])
def admin_file_list_delete(file_id):
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return file_list_proc.file_list_proc(app).delete(file_id)

@app.route("/admin/file-list/api", methods=["GET"])
def admin_file_list_api():
    """API endpoint to return file list as JSON for Quill editor"""
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        return jsonify({"error": "Unauthorized"}), 401
    # end if
    from flask import jsonify
    mgd = database.get_db_conn(config.mainDB)
    files = list(mgd.db_external_file.find({"is_deleted": False}).sort("rec_timestamp", -1))
    
    # Format files for JSON response
    file_list = []
    for file in files:
        file_url = url_for('static', filename='external_file/' + file.get("file", ""))
        file_list.append({
            "id": str(file.get("_id", "")),
            "file": file.get("file", ""),
            "original_filename": file.get("original_filename", file.get("file", "")),
            "display_name": file.get("display_name", file.get("original_filename", file.get("file", ""))),
            "location": file.get("location", ""),
            "url": file_url,
            "file_size": file.get("file_size", 0),
            "created_at": file.get("created_at", file.get("rec_timestamp_str", ""))
        })
    
    return jsonify(file_list)

@app.route("/admin/file-list/upload-api", methods=["POST"])
def admin_file_list_upload_api():
    """API endpoint for AJAX file upload that returns JSON"""
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        mgd = database.get_db_conn(config.mainDB)
        
        # Check current file count against max from config
        max_files = getattr(config, 'G_FILE_LIST_MAX_COUNT', 20)
        current_count = mgd.db_external_file.count_documents({"is_deleted": False})
        if current_count >= max_files:
            return jsonify({"success": False, "message": f"Maximum {max_files} files allowed. Please delete some files before uploading new ones."})
        
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file selected"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"})
        
        # Check file size
        max_file_size = getattr(config, 'G_FILE_LIST_MAX_SIZE', 5 * 1024 * 1024)
        file.seek(0, 2)  # Seek to end of file
        file_size_bytes = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size_bytes > max_file_size:
            max_size_mb = max_file_size / (1024 * 1024)
            file_size_mb = file_size_bytes / (1024 * 1024)
            return jsonify({"success": False, "message": f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB)"})
        
        # Get display name from form (optional)
        display_name = request.form.get('display_name', '').strip()
        if not display_name:
            display_name = file.filename  # Use original filename if no custom name provided
        
        # Ensure external_file directory exists
        external_file_path = os.path.join(config.G_HOME_PATH, "static", "external_file")
        os.makedirs(external_file_path, exist_ok=True)
        
        # Generate unique filename
        current_time = int(time.time() * 1000)
        random_int = random.randint(1000000, 9999999)
        file_ext = os.path.splitext(file.filename)[1].replace(".", "")
        if not file_ext:
            file_ext = "bin"
        file_name = "file_" + str(current_time) + "_" + str(random_int) + "." + file_ext
        
        # Save file
        save_path = os.path.join(external_file_path, file_name)
        file.save(save_path)
        
        # Get file size
        file_size = os.path.getsize(save_path)
        
        # Store in database using get_record to avoid find_and_modify issue
        file_record = database.get_record("db_external_file")
        file_record["file"] = file_name
        file_record["location"] = config.G_STATIC_URL_PATH + "/external_file/" + file_name
        file_record["original_filename"] = file.filename
        file_record["display_name"] = display_name
        file_record["file_size"] = file_size
        file_record["created_at"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        mgd.db_external_file.insert_one(file_record)
        
        # Return success with file info
        file_url = url_for('static', filename='external_file/' + file_name)
        return jsonify({
            "success": True,
            "message": "File uploaded successfully",
            "file": {
                "id": str(file_record.get("_id", "")),
                "file": file_name,
                "original_filename": file.filename,
                "display_name": display_name,
                "location": file_record["location"],
                "url": file_url,
                "file_size": file_size,
                "created_at": file_record["created_at"]
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error uploading file: {str(e)}"})


# Static File List Routes (JSON Storage)
@app.route("/admin/file-list-static")
def admin_file_list_static():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return file_list_static_proc.file_list_static_proc(app).html()

@app.route("/admin/file-list-static/upload", methods=["POST"])
def admin_file_list_static_upload():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return file_list_static_proc.file_list_static_proc(app).upload()

@app.route("/admin/file-list-static/delete/<string:file_id>", methods=["POST"])
def admin_file_list_static_delete(file_id):
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return file_list_static_proc.file_list_static_proc(app).delete(file_id)

@app.route("/admin/file-list-static/api", methods=["GET"])
def admin_file_list_static_api():
    """API endpoint to return static file list as JSON for Quill editor"""
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        return jsonify({"error": "Unauthorized"}), 401
    # end if
    return file_list_static_proc.file_list_static_proc(app).api()

@app.route("/admin/web-control")
def admin_web_control():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return web_control_proc.web_control_proc(app).html()

@app.route("/admin/web-control/save", methods=["POST"])
def admin_web_control_save():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return web_control_proc.web_control_proc(app).save()

@app.route("/admin/web-control/delete-nav/<string:nav_key>", methods=["POST"])
def admin_web_control_delete_nav(nav_key):
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return web_control_proc.web_control_proc(app).delete_navigation(nav_key)

@app.route("/admin/web-control/reorder-nav", methods=["POST"])
def admin_web_control_reorder_nav():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return web_control_proc.web_control_proc(app).reorder_navigation()

@app.route("/admin/web-control/toggle-active", methods=["POST"])
def admin_web_control_toggle_active():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    # end if
    return web_control_proc.web_control_proc(app).toggle_active()

@app.route("/admin/web-control/save-settings", methods=["POST"])
def admin_web_control_save_settings():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return web_control_proc.web_control_proc(app).save_settings()

@app.route("/admin/web-control/templates", methods=["GET"])
def admin_web_control_templates():
    """Serve template JSON file"""
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        return jsonify({"error": "Unauthorized"}), 401
    # end if
    import os
    template_file = os.path.join("static", "json_file", "site_content_template.json")
    try:
        if os.path.exists(template_file):
            with open(template_file, "r", encoding="utf-8") as f:
                import json
                templates = json.load(f)
                return jsonify(templates)
        else:
            return jsonify({}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/blank")
def admin_blank():
    fk_user_id = session.get("fk_user_id")
    if fk_user_id == None:
        flash("Please login to access admin panel.", "warning")
        return redirect(url_for("admin_login"))
    # end if
    return render_template("admin/blank.html")

@app.route("/admin/login")
def admin_login():
    return auth_proc.auth_proc(app).login_html({})

@app.route("/auth/login", methods=["POST"])
def auth_login():
    params = request.form.to_dict()
    response = auth_proc.auth_proc(app).login(params)
    
    if response["message_action"] == "LOGIN_SUCCESS":
        # Set session as permanent (24 hours)
        session.permanent = True
        session["fk_user_id"] = response["message_data"]["fk_user_id"]
        session["username"] = response["message_data"]["username"]
        session["role"] = response["message_data"]["role"]
        session["user_uuid"] = response["message_data"]["user_uuid"]
        session["email"] = response["message_data"]["email"]
        flash("Login successful!", "success")
        return redirect(url_for("contact"))  # Redirect to admin home
    else:
        flash(response["message_desc"], "danger")
        return redirect(url_for("admin_login"))

@app.route("/auth/logout")
def auth_logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("admin_login"))


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
