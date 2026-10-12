
import json
import os
import tempfile
import threading 

from flask import current_app


DEFAULT_FILES = {
    "users.json": [],
    "apartments.json": [],
    "roommate_profiles.json": [],
    "interests.json": [],
}

# NEW: Flask handles requests on several threads. This lock makes read-modify-write steps take turns so no change gets lost.
storage_lock = threading.RLock()

def _get_file_path(filename):
    if filename not in DEFAULT_FILES:
        raise ValueError(f"Unsupported storage file: {filename}")

    data_dir = current_app.config["DATA_DIR"]
    os.makedirs(data_dir, exist_ok=True)

    return os.path.join(data_dir, filename)


def initialize_storage():
    """Create the JSON files if they do not already exist."""
    with storage_lock:
        for filename, default_data in DEFAULT_FILES.items():
            path = _get_file_path(filename)
            if not os.path.exists(path):
                write_json(filename, default_data)


def read_json(filename):
    """Read data from a JSON file."""
    path = _get_file_path(filename)
    
    with storage_lock:
        if not os.path.exists(path):
            write_json(filename, DEFAULT_FILES[filename])

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)


def write_json(filename, data):
    """Save data to a JSON file."""
    path = _get_file_path(filename)

    # Write to a temporary file before replacing the original.
    # This helps prevent partially written JSON files.
    temp_path = None
    
    with storage_lock:  
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=os.path.dirname(path),
                delete=False,
            ) as file:
                temp_path = file.name
                json.dump(data, file, indent=4, ensure_ascii=False)
                file.write("\n")

            os.replace(temp_path, path)
            temp_path = None

        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)
