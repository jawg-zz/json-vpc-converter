"""
JSON ↔ VPC Converter Web App
Convert hymn songbook JSON files to/from VPC format via a web UI.
"""

import io
import json
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, Response

from json2vpc import json_to_vpc, vpc_to_json

app = FastAPI(title="JSON ↔ VPC Converter", version="1.0.0")

# Serve static files (CSS etc.)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)


def _html_page(body: str) -> str:
    """Wrap content in a full HTML page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JSON ↔ VPC Converter</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0f1117; color: #e1e4e8; min-height: 100vh; display: flex;
         flex-direction: column; align-items: center; }}
  .container {{ max-width: 720px; width: 100%; padding: 2rem 1.5rem; }}
  h1 {{ font-size: 1.75rem; margin-bottom: .25rem; }}
  .subtitle {{ color: #8b949e; margin-bottom: 2rem; font-size: .9rem; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
           padding: 1.5rem; margin-bottom: 1.5rem; }}
  .card h2 {{ font-size: 1.1rem; margin-bottom: 1rem; color: #f0f6fc; }}
  .card p {{ color: #8b949e; font-size: .85rem; margin-bottom: 1rem; }}
  label {{ display: block; margin-bottom: .4rem; font-weight: 600; font-size: .85rem; }}
  input[type=file] {{ display: block; width: 100%; padding: .6rem; background: #0d1117;
                      border: 1px dashed #30363d; border-radius: 6px; color: #c9d1d9;
                      font-size: .85rem; margin-bottom: 1rem; cursor: pointer; }}
  input[type=file]:hover {{ border-color: #58a6ff; }}
  button {{ background: #238636; color: #fff; border: none; border-radius: 6px;
            padding: .6rem 1.2rem; font-size: .85rem; font-weight: 600; cursor: pointer; }}
  button:hover {{ background: #2ea043; }}
  button.secondary {{ background: #21262d; border: 1px solid #30363d; }}
  button.secondary:hover {{ background: #30363d; }}
  .flash {{ background: #1c2128; border: 1px solid #30363d; border-radius: 6px;
            padding: 1rem; margin-bottom: 1.5rem; color: #f0f6fc; }}
  .flash.error {{ border-color: #da3633; background: #2d1b1b; }}
  .flash.success {{ border-color: #238636; background: #1b2d1b; }}
  .footer {{ color: #484f58; font-size: .8rem; margin-top: 2rem; text-align: center; }}
  .footer a {{ color: #58a6ff; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">
  <h1>📖 JSON ↔ VPC</h1>
  <p class="subtitle">Convert between JSON hymn files and Ekumenical songbook VPC format</p>
  {body}
  <div class="footer">
    <a href="https://github.com/jawg-zz/json-vpc-converter">json-vpc-converter</a>
  </div>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    body = """
    <div class="card">
      <h2>JSON → VPC</h2>
      <p>Upload a hymn songbook JSON file to convert to compressed VPC format.</p>
      <form action="/convert" method="post" enctype="multipart/form-data">
        <label for="json_file">JSON file</label>
        <input type="file" name="file" id="json_file" accept=".json" required>
        <button type="submit">Convert to VPC</button>
      </form>
    </div>

    <div class="card">
      <h2>VPC → JSON</h2>
      <p>Upload a VPC file to extract the original JSON.</p>
      <form action="/reverse" method="post" enctype="multipart/form-data">
        <label for="vpc_file">VPC file</label>
        <input type="file" name="file" id="vpc_file" accept=".vpc" required>
        <button type="submit" class="secondary">Extract to JSON</button>
      </form>
    </div>
    """
    return _html_page(body)


@app.post("/convert")
async def convert_to_vpc(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(400, "Please upload a .json file")

    try:
        content = await file.read()
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    try:
        vpc_text = json_to_vpc(data)
    except Exception as e:
        raise HTTPException(500, f"Conversion failed: {e}")

    # ZIP-compress
    buf = io.BytesIO()
    base_name = file.filename.rsplit(".", 1)[0]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.json", vpc_text)
    vpc_bytes = buf.getvalue()

    return Response(
        content=vpc_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}.vpc"',
            "Content-Length": str(len(vpc_bytes)),
        },
    )


@app.post("/reverse")
async def convert_to_json(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".vpc"):
        raise HTTPException(400, "Please upload a .vpc file")

    try:
        content = await file.read()
        if not zipfile.is_zipfile(io.BytesIO(content)):
            raise HTTPException(400, "Invalid VPC file (not a ZIP archive)")

        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            names = zf.namelist()
            if not names:
                raise HTTPException(400, "VPC file is empty")
            vpc_text = zf.read(names[0]).decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Cannot read VPC file: {e}")

    try:
        data = vpc_to_json(vpc_text)
    except Exception as e:
        raise HTTPException(500, f"VPC parsing failed: {e}")

    json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    base_name = file.filename.rsplit(".", 1)[0]
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}.json"',
            "Content-Length": str(len(json_bytes)),
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
