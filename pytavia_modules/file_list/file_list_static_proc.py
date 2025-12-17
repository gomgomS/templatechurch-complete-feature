import sys
import os
import json
import time
import random

sys.path.append("pytavia_core")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_storage")

from flask import render_template, request, redirect, url_for, flash, jsonify, url_for as flask_url_for

from pytavia_core import config


class file_list_static_proc:
    
    def __init__(self, app):
        self.app = app
        # Use relative path for JSON file storage
        self.json_file_path = os.path.join("static", "json_file")
        os.makedirs(self.json_file_path, exist_ok=True)
        self.static_file_list_path = os.path.join(self.json_file_path, "static_file_list.json")
    # end def

    def _get_file_list_file(self):
        """Get path to static file list JSON file"""
        return self.static_file_list_path
    # end def

    def _load_file_list(self):
        """Load static file list from JSON"""
        file_list_path = self._get_file_list_file()
        try:
            if os.path.exists(file_list_path):
                with open(file_list_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure we return a list
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        # If it's a dict, convert to list
                        return list(data.values()) if data else []
                    return data if data else []
            else:
                print(f"[file_list_static] File list not found: {file_list_path}")
        except Exception as e:
            print(f"[file_list_static] Error loading file list: {str(e)}")
            import traceback
            traceback.print_exc()
        return []
    # end def

    def _save_file_list(self, file_list):
        """Save static file list to JSON"""
        file_list_path = self._get_file_list_file()
        try:
            with open(file_list_path, "w", encoding="utf-8") as f:
                json.dump(file_list, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[file_list_static] Error saving file list: {str(e)}")
            return False
    # end def

    def html(self):
        """Render the static file list page"""
        files = self._load_file_list()
        # Filter out deleted files
        active_files = [f for f in files if not f.get("is_deleted", False)]
        # Sort by created_at descending
        active_files.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        max_files = getattr(config, 'G_FILE_LIST_STATIC_MAX_COUNT', 15)
        max_file_size = getattr(config, 'G_FILE_LIST_STATIC_MAX_SIZE', 3 * 1024 * 1024)
        
        return render_template(
            "admin/file_list_static.html", 
            files=active_files, 
            max_files=max_files, 
            max_file_size=max_file_size
        )
    # end def

    def upload(self):
        """Upload a file and save metadata to JSON"""
        try:
            # Check current file count against max from config
            max_files = getattr(config, 'G_FILE_LIST_STATIC_MAX_COUNT', 15)
            files = self._load_file_list()
            active_files = [f for f in files if not f.get("is_deleted", False)]
            current_count = len(active_files)
            
            if current_count >= max_files:
                flash(f"Maximum {max_files} files allowed. Please delete some files before uploading new ones.", "error")
                return redirect(url_for("admin_file_list_static"))
            
            if 'file' not in request.files:
                flash("No file selected.", "error")
                return redirect(url_for("admin_file_list_static"))
            
            file = request.files['file']
            if file.filename == '':
                flash("No file selected.", "error")
                return redirect(url_for("admin_file_list_static"))
            
            # Check file size
            max_file_size = getattr(config, 'G_FILE_LIST_STATIC_MAX_SIZE', 3 * 1024 * 1024)
            file.seek(0, 2)  # Seek to end of file
            file_size_bytes = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size_bytes > max_file_size:
                max_size_mb = max_file_size / (1024 * 1024)
                file_size_mb = file_size_bytes / (1024 * 1024)
                flash(f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB).", "error")
                return redirect(url_for("admin_file_list_static"))
            
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
            file_name = "file_static_" + str(current_time) + "_" + str(random_int) + "." + file_ext
            
            # Save file
            save_path = os.path.join(external_file_path, file_name)
            file.save(save_path)
            
            # Get file size
            file_size = os.path.getsize(save_path)
            
            # Create file record
            file_record = {
                "id": str(current_time) + "_" + str(random_int),  # Unique ID
                "file": file_name,
                "location": config.G_STATIC_URL_PATH + "/external_file/" + file_name,
                "original_filename": file.filename,
                "display_name": display_name,
                "file_size": file_size,
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                "is_deleted": False
            }
            
            # Add to file list
            files.append(file_record)
            
            if self._save_file_list(files):
                flash("File uploaded successfully.", "success")
            else:
                flash("Error saving file metadata.", "error")
        except Exception as e:
            flash(f"Error uploading file: {str(e)}", "error")
        
        return redirect(url_for("admin_file_list_static"))
    # end def

    def delete(self, file_id):
        """Delete a file (mark as deleted in JSON)"""
        try:
            files = self._load_file_list()
            
            # Find file record
            file_record = None
            for f in files:
                if f.get("id") == file_id and not f.get("is_deleted", False):
                    file_record = f
                    break
            
            if file_record:
                # Delete physical file
                file_location = file_record.get("location", "")
                if file_location.startswith("/"):
                    file_location = file_location[1:]  # Remove leading slash
                file_path = os.path.join(config.G_HOME_PATH, file_location)
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Mark as deleted in JSON
                for f in files:
                    if f.get("id") == file_id:
                        f["is_deleted"] = True
                        f["deleted_at"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                        break
                
                if self._save_file_list(files):
                    flash("File deleted successfully.", "success")
                else:
                    flash("Error updating file metadata.", "error")
            else:
                flash("File not found.", "error")
        except Exception as e:
            flash(f"Error deleting file: {str(e)}", "error")
        
        return redirect(url_for("admin_file_list_static"))
    # end def

    def api(self):
        """API endpoint to return static file list as JSON"""
        files = self._load_file_list()
        # Filter out deleted files
        active_files = [f for f in files if not f.get("is_deleted", False)]
        # Sort by created_at descending
        active_files.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Format files for JSON response
        file_list = []
        for file in active_files:
            file_url = flask_url_for('static', filename='external_file/' + file.get("file", ""))
            file_list.append({
                "id": file.get("id", ""),
                "file": file.get("file", ""),
                "original_filename": file.get("original_filename", file.get("file", "")),
                "display_name": file.get("display_name", file.get("original_filename", file.get("file", ""))),
                "location": file.get("location", ""),
                "url": file_url,
                "file_size": file.get("file_size", 0),
                "created_at": file.get("created_at", "")
            })
        
        return jsonify(file_list)
    # end def

# end class

