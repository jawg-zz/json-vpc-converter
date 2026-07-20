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

app = FastAPI(title="JSON ↔ VPC Converter", version="1.1.0")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JSON ↔ VPC Converter</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0f1117; color: #e1e4e8; min-height: 100vh; display: flex;
         flex-direction: column; align-items: center; }
  .container { max-width: 800px; width: 100%; padding: 2rem 1.5rem; }
  h1 { font-size: 1.75rem; margin-bottom: .25rem; }
  .subtitle { color: #8b949e; margin-bottom: 2rem; font-size: .9rem; }

  /* Upload zone */
  .upload-area { background: #161b22; border: 2px dashed #30363d; border-radius: 10px;
                  padding: 2.5rem 1.5rem; text-align: center; margin-bottom: 1.5rem;
                  transition: border-color .2s; cursor: pointer; position: relative; }
  .upload-area:hover { border-color: #58a6ff; }
  .upload-area.dragover { border-color: #2ea043; background: #1c2936; }
  .upload-area.has-file { border-color: #2ea043; border-style: solid; padding: 1.5rem; }
  .upload-icon { font-size: 2.5rem; margin-bottom: .75rem; }
  .upload-label { color: #8b949e; font-size: .85rem; }
  .upload-label strong { color: #c9d1d9; }
  .upload-area input[type=file] { position: absolute; inset: 0; opacity: 0; cursor: pointer; }

  /* Preview card */
  .preview { display: none; }
  .preview.visible { display: block; }

  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
          padding: 1.5rem; margin-bottom: 1.5rem; }
  .card h2 { font-size: 1.1rem; margin-bottom: 1rem; color: #f0f6fc; }

  /* Metadata grid */
  .meta-grid { display: grid; grid-template-columns: auto 1fr; gap: .4rem 1rem;
               font-size: .85rem; margin-bottom: 1rem; }
  .meta-grid .label { color: #8b949e; }
  .meta-grid .value { color: #c9d1d9; }

  /* Song table */
  .song-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  .song-table th { text-align: left; color: #8b949e; font-weight: 600;
                   padding: .5rem .75rem; border-bottom: 1px solid #30363d; }
  .song-table td { padding: .5rem .75rem; border-bottom: 1px solid #21262d;
                   color: #c9d1d9; }
  .song-table tr:hover td { background: #1c2128; }
  .song-table .num { color: #484f58; text-align: right; width: 3rem; }
  .song-table .title { font-weight: 500; }
  .song-table .verses { color: #8b949e; text-align: center; width: 4rem; }
  .song-table .empty { color: #484f58; text-align: center; padding: 2rem; }

  /* Scrollable song list */
  .song-scroll { max-height: 320px; overflow-y: auto; border: 1px solid #21262d;
                 border-radius: 6px; margin-bottom: 1rem; }
  .song-scroll::-webkit-scrollbar { width: 6px; }
  .song-scroll::-webkit-scrollbar-track { background: #0d1117; border-radius: 3px; }
  .song-scroll::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

  .stats { display: flex; gap: 1.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
  .stat { background: #0d1117; border: 1px solid #21262d; border-radius: 6px;
          padding: .75rem 1.25rem; text-align: center; flex: 1; min-width: 100px; }
  .stat .num { font-size: 1.5rem; font-weight: 700; color: #f0f6fc; }
  .stat .lbl { font-size: .75rem; color: #8b949e; margin-top: .15rem; }

  button { background: #238636; color: #fff; border: none; border-radius: 6px;
           padding: .7rem 1.5rem; font-size: .9rem; font-weight: 600; cursor: pointer;
           transition: background .15s; }
  button:hover { background: #2ea043; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  button.secondary { background: #21262d; border: 1px solid #30363d; }
  button.secondary:hover { background: #30363d; }

  .flash { border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.5rem;
           font-size: .85rem; display: none; }
  .flash.visible { display: block; }
  .flash.error { background: #2d1b1b; border: 1px solid #da3633; color: #f0f6fc; }

  .footer { color: #484f58; font-size: .8rem; margin-top: 2rem; text-align: center; }
  .footer a { color: #58a6ff; text-decoration: none; }

  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #30363d;
             border-top-color: #58a6ff; border-radius: 50%; animation: spin .6s linear infinite;
             vertical-align: middle; margin-right: .4rem; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .direction-toggle { display: flex; gap: .5rem; margin-bottom: 1.5rem; }
  .direction-toggle button { flex: 1; background: #0d1117; border: 1px solid #30363d;
                              color: #8b949e; font-size: .85rem; }
  .direction-toggle button.active { background: #1c2936; border-color: #58a6ff; color: #f0f6fc; }
</style>
</head>
<body>
<div class="container">
<h1>📖 Songbook Converter</h1>
<p class="subtitle">Convert between JSON hymn files and Ekumenical songbook VPC format</p>

<div class="direction-toggle" id="dirToggle">
  <button class="active" data-dir="json2vpc" onclick="setDir('json2vpc')">📤 JSON → VPC</button>
  <button data-dir="vpc2json" onclick="setDir('vpc2json')">📥 VPC → JSON</button>
</div>

<div class="upload-area" id="dropZone">
  <div class="upload-icon">📂</div>
  <div class="upload-label">
    <strong>Choose a file</strong> or drag it here<br>
    <span id="fileHint">.json files (songbook format)</span>
  </div>
  <input type="file" id="fileInput" accept=".json,.vpc" onchange="onFile()">
</div>

<div class="flash" id="flashMsg"></div>

<div class="preview" id="previewSection">
  <div id="metaCard" class="card"></div>
  <div id="statsRow" class="stats"></div>
  <div id="songList" class="card"></div>
  <button id="convertBtn" onclick="convert()">⬇ Convert & Download</button>
</div>

<div class="footer">
  <a href="https://github.com/jawg-zz/json-vpc-converter">json-vpc-converter v1.1</a>
</div>
</div>

<script>
let currentFile = null;
let currentDirection = 'json2vpc';
let convertedBlob = null;
let convertedName = '';

function setDir(dir) {
  currentDirection = dir;
  document.querySelectorAll('#dirToggle button').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-dir="${dir}"]`).classList.add('active');
  const hint = document.getElementById('fileHint');
  const input = document.getElementById('fileInput');
  if (dir === 'json2vpc') {
    hint.textContent = '.json files (songbook format)';
    input.accept = '.json';
  } else {
    hint.textContent = '.vpc files (compressed songbook)';
    input.accept = '.vpc';
  }
  clearPreview();
}

function showFlash(msg, isError) {
  const el = document.getElementById('flashMsg');
  el.textContent = msg;
  el.className = 'flash visible' + (isError ? ' error' : '');
}

function clearPreview() {
  document.getElementById('previewSection').classList.remove('visible');
  document.getElementById('metaCard').innerHTML = '';
  document.getElementById('statsRow').innerHTML = '';
  document.getElementById('songList').innerHTML = '';
  document.getElementById('convertBtn').style.display = 'none';
  currentFile = null;
}

function onFile() {
  const input = document.getElementById('fileInput');
  if (input.files.length === 0) return;
  const file = input.files[0];
  currentFile = file;
  
  // Update drop zone
  const zone = document.getElementById('dropZone');
  zone.classList.add('has-file');
  zone.querySelector('.upload-icon').textContent = '📄';
  zone.querySelector('.upload-label').innerHTML =
    `<strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;

  previewFile(file);
}

// Drag-and-drop
const dropZone = document.getElementById('dropZone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) {
    document.getElementById('fileInput').files = e.dataTransfer.files;
    currentFile = file;
    const zone = document.getElementById('dropZone');
    zone.classList.add('has-file');
    zone.querySelector('.upload-icon').textContent = '📄';
    zone.querySelector('.upload-label').innerHTML =
      `<strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
    previewFile(file);
  }
});

function previewFile(file) {
  document.getElementById('previewSection').classList.remove('visible');
  document.getElementById('convertBtn').style.display = 'none';
  showFlash('', false);

  const formData = new FormData();
  formData.append('file', file);

  fetch('/preview', { method: 'POST', body: formData })
    .then(r => { if (!r.ok) return r.json().then(e => { throw new Error(e.detail || 'Preview failed'); }); return r.json(); })
    .then(data => renderPreview(data))
    .catch(err => showFlash(err.message, true));
}

function renderPreview(data) {
  const dir = currentDirection;

  // Metadata card
  const metaFields = [];
  for (const key of ['Description', 'Text', 'Publisher', 'Author', 'Administrator', 'Copyright', 'Abbreviation', 'Language', 'Guid']) {
    if (data[key]) metaFields.push(`<span class="label">${key}</span><span class="value">${esc(data[key])}</span>`);
  }
  document.getElementById('metaCard').innerHTML =
    `<h2>📋 Metadata</h2><div class="meta-grid">${metaFields.join('')}</div>`;

  // Stats
  const sv = data.songCount || data.songs.length;
  const vv = data.verseCount || 0;
  document.getElementById('statsRow').innerHTML = `
    <div class="stat"><div class="num">${sv}</div><div class="lbl">Songs</div></div>
    <div class="stat"><div class="num">${vv}</div><div class="lbl">Verses</div></div>
    <div class="stat"><div class="num">${dir === 'json2vpc' ? data.compressedSize || '—' : data.originalSize || '—'}</div><div class="lbl">Output Size (KB)</div></div>
  `;

  // Song list
  const songs = data.songs || [];
  if (songs.length === 0) {
    document.getElementById('songList').innerHTML = `<h2>🎵 Songs</h2><div class="song-scroll"><table class="song-table"><tr><td colspan="3" class="empty">No songs found</td></tr></table></div>`;
  } else {
    let rows = songs.map((s, i) =>
      `<tr><td class="num">${i + 1}</td><td class="title">${esc(s.title || s.Text || '(untitled)')}</td><td class="verses">${s.verses || s.verseCount || 0}</td></tr>`
    ).join('');
    document.getElementById('songList').innerHTML = `
      <h2>🎵 Songs (${songs.length})</h2>
      <div class="song-scroll"><table class="song-table">
        <thead><tr><th>#</th><th>Title</th><th>Verses</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>`;
  }

  // Show convert button
  document.getElementById('previewSection').classList.add('visible');
  const btn = document.getElementById('convertBtn');
  btn.style.display = 'inline-block';
  btn.textContent = dir === 'json2vpc' ? '⬇ Convert to VPC & Download' : '⬇ Extract to JSON & Download';
  convertedBlob = null;
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

function convert() {
  if (!currentFile) return;
  const btn = document.getElementById('convertBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Converting...';

  const endpoint = currentDirection === 'json2vpc' ? '/convert' : '/reverse';
  const formData = new FormData();
  formData.append('file', currentFile);

  fetch(endpoint, { method: 'POST', body: formData })
    .then(r => {
      if (!r.ok) return r.json().then(e => { throw new Error(e.detail || 'Conversion failed'); });
      return r.blob();
    })
    .then(blob => {
      const ext = currentDirection === 'json2vpc' ? '.vpc' : '.json';
      const base = currentFile.name.replace(/\.(json|vpc)$/i, '');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = base + ext;
      document.body.appendChild(a); a.click();
      a.remove(); URL.revokeObjectURL(url);
      btn.innerHTML = '⬇ Download Again';
      btn.disabled = false;
    })
    .catch(err => {
      showFlash(err.message, true);
      btn.innerHTML = '⬇ Convert & Download';
      btn.disabled = false;
    });
}

// Click drop zone to trigger file input
document.getElementById('dropZone').addEventListener('click', function(e) {
  if (e.target.tagName !== 'INPUT') document.getElementById('fileInput').click();
});
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(PAGE)


@app.post("/preview")
async def preview_file(file: UploadFile = File(...)):
    """Parse uploaded file and return metadata for preview."""
    content = await file.read()
    name = file.filename or ""
    is_vpc = name.lower().endswith(".vpc")

    try:
        if is_vpc:
            # VPC → extract text then parse
            if not zipfile.is_zipfile(io.BytesIO(content)):
                raise HTTPException(400, "Invalid VPC file (not a ZIP archive)")
            with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                names = zf.namelist()
                if not names:
                    raise HTTPException(400, "VPC file is empty")
                vpc_text = zf.read(names[0]).decode("utf-8")
            data = vpc_to_json(vpc_text)
        else:
            # JSON
            data = json.loads(content)
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(400, f"Cannot parse file: {e}")

    songs = data.get("Songs", [])
    song_list = []
    total_verses = 0
    for s in songs:
        verses = s.get("Verses", [])
        count = len(verses)
        total_verses += count
        song_list.append({
            "title": s.get("Text", s.get("Title", "")),
            "verseCount": count,
            "id": s.get("ID"),
        })

    meta = {
        "songCount": len(songs),
        "verseCount": total_verses,
        "songs": song_list,
        "originalSize": round(len(content) / 1024, 1),
    }

    # Add root-level metadata fields
    for key in ["Text", "Description", "Publisher", "Author", "Administrator",
                 "Copyright", "Abbreviation", "Language", "Guid", "Style"]:
        if key in data:
            val = data[key]
            if isinstance(val, str):
                meta[key] = val
            elif isinstance(val, dict):
                meta[key] = json.dumps(val, ensure_ascii=False)

    return meta


@app.post("/convert")
async def convert_to_vpc(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(400, "Please upload a .json file")

    content = await file.read()
    try:
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    try:
        vpc_text = json_to_vpc(data)
    except Exception as e:
        raise HTTPException(500, f"Conversion failed: {e}")

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
    if not file.filename or not file.filename.lower().endswith(".vpc"):
        raise HTTPException(400, "Please upload a .vpc file")

    content = await file.read()
    try:
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
