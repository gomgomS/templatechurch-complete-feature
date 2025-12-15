import sys
import os
import json
import time

sys.path.append("pytavia_core")
sys.path.append("pytavia_modules")
sys.path.append("pytavia_settings")
sys.path.append("pytavia_stdlib")
sys.path.append("pytavia_storage")

from flask import render_template, request, redirect, url_for, flash, jsonify
from pytavia_stdlib import sanitize

from pytavia_core import config


class web_control_proc:
    
    def __init__(self, app):
        self.app = app
        # Use relative path like view_index.py does
        self.json_file_path = os.path.join("static", "json_file")
        os.makedirs(self.json_file_path, exist_ok=True)
    # end def

    def _get_navigation_file(self):
        """Get path to navigation JSON file"""
        return os.path.join(self.json_file_path, "navigation.json")
    # end def

    def _get_content_file(self):
        """Get path to single content JSON file"""
        return os.path.join(self.json_file_path, "site_content.json")
    # end def

    def _load_navigation(self):
        """Load navigation items from JSON"""
        nav_file = self._get_navigation_file()
        try:
            if os.path.exists(nav_file):
                with open(nav_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure we return a list
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        # If it's a dict, convert to list (shouldn't happen, but handle it)
                        return list(data.values()) if data else []
                    return data if data else []
            else:
                print(f"[web_control] Navigation file not found: {nav_file}")
        except Exception as e:
            print(f"[web_control] Error loading navigation: {str(e)}")
            import traceback
            traceback.print_exc()
        return []
    # end def

    def _save_navigation(self, navigation):
        """Save navigation items to JSON"""
        nav_file = self._get_navigation_file()
        try:
            with open(nav_file, "w", encoding="utf-8") as f:
                json.dump(navigation, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[web_control] Error saving navigation: {str(e)}")
            return False
    # end def

    def _load_all_content(self):
        """Load all content from single JSON file"""
        content_file = self._get_content_file()
        try:
            if os.path.exists(content_file):
                with open(content_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[web_control] Error loading content: {str(e)}")
        return {}
    # end def

    def _load_content(self, nav_key):
        """Load content for a specific navigation item"""
        all_content = self._load_all_content()
        return all_content.get(nav_key, {})
    # end def

    def _save_content(self, nav_key, content):
        """Save content for a navigation item to single JSON file"""
        content_file = self._get_content_file()
        try:
            # Load existing content
            all_content = self._load_all_content()
            # Update or add the nav_key content
            all_content[nav_key] = content
            # Save back to file
            with open(content_file, "w", encoding="utf-8") as f:
                json.dump(all_content, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[web_control] Error saving content for {nav_key}: {str(e)}")
            return False
    # end def

    def html(self):
        """Render the web control page"""
        navigation = self._load_navigation()
        all_content = self._load_all_content()
        
        # Build content_data dict for template - extract all content from site_content.json
        # Convert from {"key": {"content": "..."}} to {"key": "..."}
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
        
        # Debug: Print navigation and content_data to verify they're loaded
        print(f"[web_control] Navigation items loaded: {len(navigation)}")
        print(f"[web_control] Content items loaded: {len(content_data)}")
        print(f"[web_control] Plugin items loaded: {len(plugin_data)}")
        
        return render_template(
            "admin/web_control.html",
            navigation=navigation,
            content_data=content_data,
            plugin_data=plugin_data
        )
    # end def

    def save_navigation(self):
        """Save navigation item (add or update)"""
        try:
            params = sanitize.clean_html_dic(request.form.to_dict())
            nav_key = params.get("nav_key", "").strip()
            nav_label = params.get("nav_label", "").strip()
            nav_url = params.get("nav_url", "").strip()
            nav_icon = params.get("nav_icon", "").strip()
            nav_order = params.get("nav_order", "0").strip()
            
            if not nav_key or not nav_label:
                flash("Navigation key and label are required.", "error")
                return redirect(url_for("admin_web_control"))
            
            # Convert order to int
            try:
                nav_order = int(nav_order)
            except:
                nav_order = 0
            
            navigation = self._load_navigation()
            
            # Check if updating existing or adding new
            existing_index = None
            for i, nav in enumerate(navigation):
                if nav.get("key") == nav_key:
                    existing_index = i
                    break
            
            nav_item = {
                "key": nav_key,
                "label": nav_label,
                "url": nav_url,
                "icon": nav_icon,
                "order": nav_order,
                "updated_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            }
            
            if existing_index is not None:
                # Update existing
                navigation[existing_index] = nav_item
                flash("Navigation item updated successfully.", "success")
            else:
                # Add new
                nav_item["created_at"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                navigation.append(nav_item)
                flash("Navigation item added successfully.", "success")
            
            # Sort by order
            navigation.sort(key=lambda x: x.get("order", 0))
            
            if self._save_navigation(navigation):
                return redirect(url_for("admin_web_control"))
            else:
                flash("Error saving navigation.", "error")
                return redirect(url_for("admin_web_control"))
                
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for("admin_web_control"))
    # end def

    def delete_navigation(self, nav_key):
        """Delete a navigation item"""
        try:
            navigation = self._load_navigation()
            navigation = [nav for nav in navigation if nav.get("key") != nav_key]
            
            if self._save_navigation(navigation):
                # Also remove content from single file
                all_content = self._load_all_content()
                if nav_key in all_content:
                    del all_content[nav_key]
                    content_file = self._get_content_file()
                    with open(content_file, "w", encoding="utf-8") as f:
                        json.dump(all_content, f, indent=2, ensure_ascii=False)
                flash("Navigation item deleted successfully.", "success")
            else:
                flash("Error deleting navigation item.", "error")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
        
        return redirect(url_for("admin_web_control"))
    # end def

    def save(self):
        """Save navigation and content together"""
        try:
            nav_name = request.form.get("nav_name", "").strip().lower().replace(" ", "-")
            nav_label = request.form.get("nav_label", "").strip()
            html_content = request.form.get("content", "").strip()
            nav_key_old = request.form.get("nav_key_old", "").strip()
            
            # Get map coordinates
            map_latitude = request.form.get("map_latitude", "").strip()
            map_longitude = request.form.get("map_longitude", "").strip()
            
            if not nav_name or not nav_label:
                flash("Nav name and label are required.", "error")
                return redirect(url_for("admin_web_control"))
            
            navigation = self._load_navigation()
            all_content = self._load_all_content()
            
            # Check if updating existing (by old key) or adding new
            existing_index = None
            if nav_key_old:
                for i, nav in enumerate(navigation):
                    if nav.get("key") == nav_key_old:
                        existing_index = i
                        break
            
            # If nav_name changed, check if new name already exists
            if nav_name != nav_key_old:
                for nav in navigation:
                    if nav.get("key") == nav_name:
                        flash(f"Navigation name '{nav_name}' already exists.", "error")
                        return redirect(url_for("admin_web_control"))
            
            # Prepare navigation item
            nav_item = {
                "key": nav_name,
                "label": nav_label,
                "url": f"#{nav_name}",
                "icon": "",
                "order": len(navigation) if existing_index is None else navigation[existing_index].get("order", len(navigation)),
                "updated_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            }
            
            # Add map data if provided
            if map_latitude and map_longitude:
                try:
                    nav_item["map_latitude"] = float(map_latitude)
                    nav_item["map_longitude"] = float(map_longitude)
                except ValueError:
                    flash("Invalid map coordinates. Please enter valid numbers.", "error")
                    return redirect(url_for("admin_web_control"))
            # Note: If map fields are empty, they won't be added to nav_item, effectively removing them
            
            if existing_index is not None:
                # Update existing - preserve created_at if it exists
                if "created_at" in navigation[existing_index]:
                    nav_item["created_at"] = navigation[existing_index]["created_at"]
                # If key changed, remove old content
                if nav_key_old != nav_name and nav_key_old in all_content:
                    del all_content[nav_key_old]
                navigation[existing_index] = nav_item
                flash("Item updated successfully.", "success")
            else:
                # Add new
                nav_item["created_at"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                navigation.append(nav_item)
                flash("Item added successfully.", "success")
            
            # Save navigation
            if not self._save_navigation(navigation):
                flash("Error saving navigation.", "error")
                return redirect(url_for("admin_web_control"))
            
            # Save content - preserve existing plugin data
            existing_content = all_content.get(nav_name, {})
            
            content = {
                "content": html_content
            }
            
            # Preserve existing plugin data if it exists
            if "plugin" in existing_content:
                content["plugin"] = existing_content["plugin"].copy()
            
            # Add or update map plugin data if coordinates are provided
            if map_latitude and map_longitude:
                try:
                    if "plugin" not in content:
                        content["plugin"] = {}
                    content["plugin"]["maps"] = {
                        "latitude": float(map_latitude),
                        "longitude": float(map_longitude)
                    }
                    # If embed_url exists, preserve it
                    if "plugin" in existing_content and "maps" in existing_content["plugin"] and "embed_url" in existing_content["plugin"]["maps"]:
                        content["plugin"]["maps"]["embed_url"] = existing_content["plugin"]["maps"]["embed_url"]
                except ValueError:
                    flash("Invalid map coordinates. Please enter valid numbers.", "error")
                    return redirect(url_for("admin_web_control"))
            # If map fields are cleared, remove maps from plugin
            elif "plugin" in existing_content and "maps" in existing_content["plugin"]:
                # Keep plugin but remove maps
                if "plugin" not in content:
                    content["plugin"] = existing_content["plugin"].copy()
                if "maps" in content["plugin"]:
                    del content["plugin"]["maps"]
            
            if not self._save_content(nav_name, content):
                flash("Error saving content.", "error")
                return redirect(url_for("admin_web_control"))
            
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
        
        return redirect(url_for("admin_web_control"))
    # end def

    def save_content(self):
        """Save content for a navigation item (kept for backward compatibility)"""
        return self.save()
    # end def

# end class

