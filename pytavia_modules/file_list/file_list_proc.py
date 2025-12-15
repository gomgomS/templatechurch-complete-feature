import sys
import os
import time
import random

sys.path.append("pytavia_core")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_storage")

from flask import render_template, request, redirect, url_for, flash
from bson.objectid import ObjectId

from pytavia_core import database, config


class file_list_proc:
    
    def __init__(self, app):
        self.app = app
    # end def

    def html(self):
        mgd = database.get_db_conn(config.mainDB)
        files = list(mgd.db_external_file.find({"is_deleted": False}).sort("rec_timestamp", -1))
        max_files = getattr(config, 'G_FILE_LIST_MAX_COUNT', 20)
        max_file_size = getattr(config, 'G_FILE_LIST_MAX_SIZE', 5 * 1024 * 1024)
        return render_template("admin/file_list.html", files=files, max_files=max_files, max_file_size=max_file_size)
    # end def

    def upload(self):
        try:
            mgd = database.get_db_conn(config.mainDB)
            
            # Check current file count against max from config
            max_files = getattr(config, 'G_FILE_LIST_MAX_COUNT', 20)
            current_count = mgd.db_external_file.count_documents({"is_deleted": False})
            if current_count >= max_files:
                flash(f"Maximum {max_files} files allowed. Please delete some files before uploading new ones.", "error")
                return redirect(url_for("admin_file_list"))
            
            if 'file' not in request.files:
                flash("No file selected.", "error")
                return redirect(url_for("admin_file_list"))
            
            file = request.files['file']
            if file.filename == '':
                flash("No file selected.", "error")
                return redirect(url_for("admin_file_list"))
            
            # Check file size
            max_file_size = getattr(config, 'G_FILE_LIST_MAX_SIZE', 5 * 1024 * 1024)
            file.seek(0, 2)  # Seek to end of file
            file_size_bytes = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size_bytes > max_file_size:
                max_size_mb = max_file_size / (1024 * 1024)
                file_size_mb = file_size_bytes / (1024 * 1024)
                flash(f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB).", "error")
                return redirect(url_for("admin_file_list"))
            
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
            
            flash("File uploaded successfully.", "success")
        except Exception as e:
            flash(f"Error uploading file: {str(e)}", "error")
        
        return redirect(url_for("admin_file_list"))
    # end def

    def delete(self, file_id):
        try:
            mgd = database.get_db_conn(config.mainDB)
            
            # Find file record
            file_record = mgd.db_external_file.find_one({"_id": ObjectId(file_id), "is_deleted": False})
            if file_record:
                # Delete physical file
                file_location = file_record.get("location", "")
                if file_location.startswith("/"):
                    file_location = file_location[1:]  # Remove leading slash
                file_path = os.path.join(config.G_HOME_PATH, file_location)
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Mark as deleted in database
                mgd.db_external_file.update_one(
                    {"_id": ObjectId(file_id)},
                    {"$set": {"is_deleted": True}}
                )
                flash("File deleted successfully.", "success")
            else:
                flash("File not found.", "error")
        except Exception as e:
            flash(f"Error deleting file: {str(e)}", "error")
        
        return redirect(url_for("admin_file_list"))
    # end def

# end class

