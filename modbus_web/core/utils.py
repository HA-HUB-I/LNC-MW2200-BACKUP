import pathlib

_NC_EXTENSIONS = {".nc", ".cnc", ".tap", ".prg", ".txt", ".gcode"}
_UPLOAD_DIR = pathlib.Path(__file__).parent.parent / "uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)

def list_uploaded_files():
    files = []
    for p in sorted(_UPLOAD_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in _NC_EXTENSIONS:
            files.append({"name": p.name, "size_bytes": p.stat().st_size})
    return files

def save_nc_file(flask_file):
    if not flask_file.filename:
        return False, "Empty filename"
    
    ext = pathlib.Path(flask_file.filename).suffix.lower()
    if ext not in _NC_EXTENSIONS:
        return False, f"Unsupported extension {ext}"
    
    safe_name = "".join(c for c in flask_file.filename if c.isalnum() or c in "._- ")
    path = _UPLOAD_DIR / safe_name
    flask_file.save(str(path))
    return True, safe_name
