"""
JSON ↔ VPC Converter Web App
Convert hymn songbook JSON files to/from VPC format via a web UI.
"""

import io
import json
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, Response

from json2vpc import json_to_vpc, vpc_to_json

app = FastAPI(title="JSON ↔ VPC Converter", version="1.2.1")

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Songbook Converter</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0d0808;
    --bg-card: #181010;
    --bg-card-hover: #221717;
    --border: #2e1c1c;
    --border-hover: #4a2a2a;
    --text: #e8d8d8;
    --text-muted: #8c6e6e;
    --text-dim: #5c3e3e;
    --accent: #B8433A;
    --accent-hover: #cc5850;
    --accent-glow: rgba(184, 67, 58, 0.1);
    --radius: 12px;
    --radius-sm: 8px;
    --font: 'Outfit', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --transition: 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    overflow-x: hidden;
  }

  /* Grain texture overlay */
  body::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    opacity: 0.035;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-size: 256px 256px;
    pointer-events: none;
  }

  /* Warm gradient orb */
  body::after {
    content: '';
    position: fixed;
    top: -30%; right: -20%;
    width: 700px; height: 700px;
    background: radial-gradient(circle, rgba(184, 67, 58, 0.07) 0%, transparent 70%);
    z-index: 0;
    pointer-events: none;
  }

  .container { max-width: 840px; width: 100%; padding: 2.5rem 1.5rem 4rem; position: relative; z-index: 1; }

  /* Header */
  .header { margin-bottom: 2.5rem; animation: fadeDown 0.5s ease; }
  @keyframes fadeDown { from { opacity: 0; transform: translateY(-12px); } to { opacity: 1; transform: translateY(0); } }
  .header h1 { font-size: 1.65rem; font-weight: 600; letter-spacing: -0.02em; }
  .header h1 span { color: var(--accent); }
  .header .subtitle { color: var(--text-muted); font-size: .9rem; font-weight: 300; margin-top: .25rem; }

  /* Direction toggle */
  .dir-tabs { display: flex; gap: 2px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 3px; margin-bottom: 1.5rem; animation: fadeDown 0.5s ease 0.1s both; }
  .dir-tabs button { flex: 1; padding: .65rem 1rem; border: none; border-radius: calc(var(--radius) - 3px); background: transparent; color: var(--text-muted); font-family: var(--font); font-size: .85rem; font-weight: 500; cursor: pointer; transition: var(--transition); }
  .dir-tabs button.active { background: var(--accent-glow); color: var(--accent); }
  .dir-tabs button:not(.active):hover { color: var(--text); background: var(--bg-card-hover); }
  .dir-tabs button .icon { margin-right: .4rem; }

  /* Drop zone */
  .drop-zone { position: relative; border: 2px dashed var(--border); border-radius: var(--radius); padding: 3rem 2rem; text-align: center; cursor: pointer; transition: var(--transition); background: var(--bg-card); margin-bottom: 1.5rem; animation: fadeDown 0.5s ease 0.15s both; }
  .drop-zone:hover { border-color: var(--border-hover); background: var(--bg-card-hover); }
  .drop-zone.dragover { border-color: var(--accent); background: var(--accent-glow); }
  .drop-zone.has-file { border-style: solid; border-color: var(--accent); padding: 1.5rem 2rem; }
  .drop-zone input[type=file] { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
  .drop-icon { font-size: 2.2rem; margin-bottom: .6rem; transition: var(--transition); }
  .drop-zone.has-file .drop-icon { font-size: 1.6rem; margin-bottom: 0; }
  .drop-label { color: var(--text-muted); font-size: .85rem; font-weight: 300; }
  .drop-label strong { color: var(--text); font-weight: 500; }
  .drop-hint { color: var(--text-dim); font-size: .78rem; margin-top: .3rem; }

  /* Flash message */
  .flash { border-radius: var(--radius-sm); padding: .85rem 1.1rem; margin-bottom: 1.5rem; font-size: .85rem; display: none; animation: flashIn 0.3s ease; }
  @keyframes flashIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
  .flash.visible { display: block; }
  .flash.error { background: rgba(218, 54, 51, 0.12); border: 1px solid rgba(218, 54, 51, 0.25); color: #f0a8a8; }

  /* Preview section */
  .preview { display: none; animation: fadeUp 0.4s ease; }
  .preview.visible { display: block; }
  @keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

  .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.25rem; }
  .card h2 { font-size: 1rem; font-weight: 500; margin-bottom: 1rem; color: var(--text); display: flex; align-items: center; gap: .5rem; }
  .card h2 .badge { background: var(--accent-glow); color: var(--accent); font-size: .75rem; font-weight: 500; padding: .15rem .6rem; border-radius: 99px; }

  /* Metadata grid */
  .meta-grid { display: grid; grid-template-columns: auto 1fr; gap: .35rem 1rem; font-size: .85rem; }
  .meta-grid .label { color: var(--text-dim); font-weight: 400; white-space: nowrap; }
  .meta-grid .value { color: var(--text); font-weight: 300; overflow: hidden; text-overflow: ellipsis; }

  /* Stats row */
  .stats { display: flex; gap: .75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
  .stat { flex: 1; min-width: 100px; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: .9rem 1rem; text-align: center; }
  .stat .num { font-size: 1.5rem; font-weight: 600; color: var(--accent); line-height: 1.2; }
  .stat .lbl { font-size: .72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .04em; margin-top: .15rem; }

  /* Song search */
  .song-search { width: 100%; padding: .65rem .9rem; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text); font-family: var(--font); font-size: .85rem; outline: none; transition: var(--transition); margin-bottom: .75rem; }
  .song-search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }
  .song-search::placeholder { color: var(--text-dim); }

  /* Song table */
  .song-scroll { max-height: 320px; overflow-y: auto; border: 1px solid var(--border); border-radius: var(--radius-sm); }
  .song-scroll::-webkit-scrollbar { width: 5px; }
  .song-scroll::-webkit-scrollbar-track { background: transparent; }
  .song-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
  .song-scroll::-webkit-scrollbar-thumb:hover { background: var(--border-hover); }
  .song-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  .song-table th { text-align: left; color: var(--text-dim); font-weight: 500; padding: .55rem .75rem; border-bottom: 1px solid var(--border); background: var(--bg); position: sticky; top: 0; font-size: .78rem; text-transform: uppercase; letter-spacing: .03em; }
  .song-table td { padding: .5rem .75rem; border-bottom: 1px solid rgba(46, 28, 28, 0.5); color: var(--text-muted); transition: var(--transition); cursor: pointer; }
  .song-table tr:hover td { background: var(--bg-card-hover); color: var(--text); }
  .song-table tr.active td { background: var(--accent-glow); color: var(--accent); }
  .song-table .num { color: var(--text-dim); text-align: right; width: 2.5rem; font-size: .78rem; }
  .song-table .title { font-weight: 400; }
  .song-table .verses { text-align: center; width: 3.5rem; font-size: .78rem; color: var(--text-dim); }
  .song-table .empty { color: var(--text-dim); text-align: center; padding: 2rem; cursor: default; }
  .song-table .no-match { color: var(--text-dim); text-align: center; padding: 2rem; cursor: default; }

  /* Pagination */
  .pagination { display: flex; align-items: center; justify-content: center; gap: .35rem; padding: .75rem 0 .25rem; font-size: .82rem; }
  .pagination .pbtn { background: var(--bg); border: 1px solid var(--border); color: var(--text-muted); padding: .35rem .65rem; border-radius: 6px; cursor: pointer; font-family: var(--font); font-size: .8rem; transition: var(--transition); min-width: 2rem; text-align: center; }
  .pagination .pbtn:hover { border-color: var(--accent); color: var(--text); }
  .pagination .pbtn.active { background: var(--accent-glow); border-color: var(--accent); color: var(--accent); }
  .pagination .pbtn:disabled { opacity: .3; cursor: not-allowed; }
  .pagination .pinfo { color: var(--text-dim); padding: 0 .5rem; font-size: .78rem; white-space: nowrap; }
  .pagination .psep { color: var(--text-dim); }

  /* Selection */
  .song-table input[type=checkbox] { accent-color: var(--accent); cursor: pointer; }
  .sel-count { color: var(--accent); font-size: .8rem; font-weight: 400; margin-left: auto; }

  /* Verse detail panel */
  .verse-panel { display: none; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 1rem 1.25rem; margin-top: .75rem; animation: fadeUp 0.3s ease; }
  .verse-panel.visible { display: block; }
  .verse-panel .vtitle { font-size: .9rem; font-weight: 500; color: var(--accent); margin-bottom: .6rem; }
  .verse-panel .vheader { display: flex; justify-content: space-between; align-items: center; margin-bottom: .6rem; }
  .verse-panel .vclose { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: 1.1rem; padding: .2rem; line-height: 1; transition: var(--transition); }
  .verse-panel .vclose:hover { color: var(--text); }
  .verse-panel .vitem { padding: .5rem 0; border-bottom: 1px solid rgba(46, 28, 28, 0.3); font-size: .85rem; font-weight: 300; line-height: 1.5; color: var(--text); }
  .verse-panel .vitem:last-child { border-bottom: none; }

  /* Buttons */
  .actions { display: flex; gap: .75rem; flex-wrap: wrap; margin-top: 1.25rem; }
  .btn { padding: .7rem 1.5rem; border: none; border-radius: var(--radius-sm); font-family: var(--font); font-size: .88rem; font-weight: 500; cursor: pointer; transition: var(--transition); display: inline-flex; align-items: center; gap: .5rem; }
  .btn:active { transform: scale(0.97); }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); box-shadow: 0 4px 20px rgba(184, 67, 58, 0.25); }
  .btn-primary:disabled { opacity: .4; cursor: wait; }
  .btn-secondary { background: var(--bg); border: 1px solid var(--border); color: var(--text); }
  .btn-secondary:hover { background: var(--bg-card-hover); border-color: var(--border-hover); }
  .btn-secondary:disabled { opacity: .4; cursor: not-allowed; }

  /* Spinner */
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.2); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Footer */
  .footer { margin-top: 3rem; text-align: center; color: var(--text-dim); font-size: .78rem; }
  .footer a { color: var(--text-muted); text-decoration: none; }
  .footer a:hover { color: var(--accent); }

  /* File info in drop zone */
  .drop-zone .file-info { display: none; }
  .drop-zone.has-file .drop-prompt { display: none; }
  .drop-zone.has-file .file-info { display: block; }
  .drop-zone.has-file .file-info .fname { font-weight: 500; color: var(--accent); }

  /* Responsive */
  @media (max-width: 600px) {
    .container { padding: 1.5rem 1rem 3rem; }
    .stats { flex-direction: column; }
    .stat { min-width: auto; }
    .dir-tabs button { font-size: .8rem; padding: .55rem .7rem; }
    .drop-zone { padding: 2rem 1.25rem; }
    .actions { flex-direction: column; }
    .btn { justify-content: center; }
    .meta-grid { grid-template-columns: 1fr; gap: .15rem; }
    .meta-grid .label { font-size: .78rem; }
  }
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>Songbook <span>Converter</span></h1>
  <div class="subtitle">Convert between JSON hymn files and Ekumenical VPC format</div>
</div>

<div class="dir-tabs" id="dirTabs">
  <button class="active" data-dir="json2vpc"><span class="icon">📤</span> JSON → VPC</button>
  <button data-dir="vpc2json"><span class="icon">📥</span> VPC → JSON</button>
</div>

<div class="drop-zone" id="dropZone">
  <input type="file" id="fileInput" accept=".json,.vpc">
  <div class="drop-prompt">
    <div class="drop-icon" id="dropIcon">📂</div>
    <div class="drop-label"><strong>Choose a file</strong> or drag it here</div>
    <div class="drop-hint" id="fileHint">.json files (songbook format)</div>
  </div>
  <div class="file-info">
    <div class="drop-icon" id="fileIcon">📄</div>
    <div class="drop-label" id="fileName"></div>
    <div class="drop-hint" id="fileSize"></div>
  </div>
</div>

<div class="flash" id="flashMsg"></div>

<div class="preview" id="previewSection">
  <div class="card" id="metaCard"></div>
  <div class="stats" id="statsRow"></div>
  <div class="card">
    <h2>🎵 Songs <span class="badge" id="songBadge">0</span></h2>
    <input class="song-search" id="songSearch" type="text" placeholder="Search songs..." oninput="filterSongs()">
    <div class="song-scroll" id="songScroll">
      <table class="song-table">
        <thead><tr><th style="width:2rem"><input type="checkbox" id="selectAll" onchange="toggleAll()" title="Select all"></th><th>#</th><th>Title</th><th>Verses</th></tr></thead>
        <tbody id="songBody"></tbody>
      </table>
    </div>
    <div class="pagination" id="pagination"></div>
    <div class="verse-panel" id="versePanel"></div>
  </div>
  <div class="actions" id="actionRow"></div>
</div>

<div class="footer">
  <a href="https://github.com/jawg-zz/json-vpc-converter">json-vpc-converter v1.2</a>
</div>

</div>

<script>
/* ── State ────────────────────────────────── */
let currentFile = null;
let currentDirection = 'json2vpc';
let previewData = null;
let _filteredSongs = [];
let _page = 1;
let _perPage = 25;
let _selected = new Set();

function toggleAll() {
  const checked = document.getElementById('selectAll').checked;
  const songs = _filteredSongs;
  const start = (_page - 1) * _perPage;
  const end = Math.min(start + _perPage, songs.length);
  for (let i = start; i < end; i++) {
    if (checked) _selected.add(i); else _selected.delete(i);
  }
  renderSongTable();
  updateSelCount();
}

function toggleSel(gidx) {
  if (_selected.has(gidx)) _selected.delete(gidx); else _selected.add(gidx);
  updateSelCount();
}

function updateSelCount() {
  const badge = document.getElementById('songBadge');
  const total = window._allSongs ? window._allSongs.length : 0;
  const sel = _selected.size;
  if (sel > 0 && sel < total) badge.textContent = `${sel}/${total}`;
  else if (sel === total) badge.textContent = `${total}`;
  else badge.textContent = `${total}`;
  // Update action button text
  const btn = document.getElementById('convertBtn');
  if (btn && sel > 0 && sel < total) {
    const dir = currentDirection;
    const action = dir === 'json2vpc' ? 'Convert to VPC' : 'Extract to JSON';
    btn.innerHTML = `⬇ ${action} (${sel} selected)`;
  } else if (btn) {
    const dir = currentDirection;
    btn.innerHTML = `⬇ ${dir === 'json2vpc' ? 'Convert to VPC' : 'Extract to JSON'}`;
  }
}

/* ── Direction toggle ─────────────────────── */
document.querySelectorAll('#dirTabs button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#dirTabs button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentDirection = btn.dataset.dir;
    const hint = document.getElementById('fileHint');
    const input = document.getElementById('fileInput');
    if (currentDirection === 'json2vpc') {
      hint.textContent = '.json files (songbook format)';
      input.accept = '.json';
    } else {
      hint.textContent = '.vpc files (compressed songbook)';
      input.accept = '.vpc';
    }
    clearPreview();
  });
});

/* ── Drop zone ────────────────────────────── */
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
dropZone.addEventListener('click', e => { if (e.target.tagName !== 'INPUT') fileInput.click(); });
fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });

function handleFile(file) {
  currentFile = file;
  dropZone.classList.add('has-file');
  document.getElementById('fileIcon').textContent = file.name.match(/\.(json|vpc)$/i)?.[1] === 'vpc' ? '🗜️' : '📄';
  document.getElementById('fileName').innerHTML = `<strong>${file.name}</strong>`;
  document.getElementById('fileSize').textContent = (file.size / 1024).toFixed(1) + ' KB';
  previewFile(file);
}

/* ── Flash ────────────────────────────────── */
function flash(msg, isError) {
  const el = document.getElementById('flashMsg');
  el.textContent = msg;
  el.className = 'flash visible' + (isError ? ' error' : '');
  if (!isError) setTimeout(() => el.classList.remove('visible'), 4000);
}

/* ── Clear preview ────────────────────────── */
function clearPreview() {
  document.getElementById('previewSection').classList.remove('visible');
  document.getElementById('metaCard').innerHTML = '';
  document.getElementById('statsRow').innerHTML = '';
  document.getElementById('songBody').innerHTML = '';
  document.getElementById('songBadge').textContent = '0';
  document.getElementById('versePanel').classList.remove('visible');
  document.getElementById('actionRow').innerHTML = '';
  previewData = null;
}

/* ── Preview ──────────────────────────────── */
function previewFile(file) {
  clearPreview();
  flash('', false);
  const fd = new FormData();
  fd.append('file', file);

  fetch('/preview', { method: 'POST', body: fd })
    .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || 'Preview failed'); }))
    .then(data => {
      previewData = data;
      renderPreview(data);
    })
    .catch(err => flash(err.message, true));
}

function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

function renderPreview(data) {
  // Metadata
  const mkeys = ['Description', 'Text', 'Publisher', 'Author', 'Administrator', 'Copyright', 'Abbreviation', 'Language'];
  const mhtml = mkeys.filter(k => data[k]).map(k =>
    `<span class="label">${k}</span><span class="value">${esc(data[k])}</span>`
  ).join('');
  document.getElementById('metaCard').innerHTML = mhtml ? `<h2>📋 Metadata</h2><div class="meta-grid">${mhtml}</div>` : '';

  // Stats
  const totalV = data.verseCount || 0;
  const sCount = data.songCount || data.songs.length;
  document.getElementById('statsRow').innerHTML = `
    <div class="stat"><div class="num">${sCount}</div><div class="lbl">Songs</div></div>
    <div class="stat"><div class="num">${totalV}</div><div class="lbl">Verses</div></div>
    <div class="stat"><div class="num">${Math.round(totalV / Math.max(sCount, 1) * 10) / 10}</div><div class="lbl">Avg Verses</div></div>
    <div class="stat"><div class="num">${data.originalSize || '—'}</div><div class="lbl">File (KB)</div></div>`;

  // Songs table
  const allSongs = data.songs || [];
  document.getElementById('songBadge').textContent = allSongs.length;
  document.getElementById('songSearch').value = '';
  window._allSongs = allSongs;
  _filteredSongs = allSongs;
  _page = 1;
  // Select all by default
  _selected = new Set(allSongs.map((_, i) => i));
  renderSongTable();
  updateSelCount();

  // Action buttons
  const dir = currentDirection;
  document.getElementById('actionRow').innerHTML = `
    <button class="btn btn-primary" id="convertBtn" onclick="convert()">
      ⬇ ${dir === 'json2vpc' ? 'Convert to VPC' : 'Extract to JSON'}
    </button>
    <button class="btn btn-secondary" onclick="copySongList()">📋 Copy Song List</button>
    <button class="btn btn-secondary" onclick="exportText()">📝 Export as Text</button>`;

  document.getElementById('previewSection').classList.add('visible');
}

/* ── Song table ───────────────────────────── */
function renderSongTable() {
  const tbody = document.getElementById('songBody');
  const songs = _filteredSongs;
  if (!songs.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="no-match">No songs match your search</td></tr>`;
    return;
  }
  const totalPages = Math.ceil(songs.length / _perPage);
  if (_page > totalPages) _page = totalPages;
  const start = (_page - 1) * _perPage;
  const page = songs.slice(start, start + _perPage);
  tbody.innerHTML = page.map((s, i) => {
    const globalIdx = start + i;
    const checked = _selected.has(globalIdx) ? 'checked' : '';
    return `<tr data-gidx="${globalIdx}" onclick="showVerses(${globalIdx})">
      <td style="width:2rem;text-align:center"><input type="checkbox" ${checked} onclick="event.stopPropagation();toggleSel(${globalIdx})"></td>
      <td class="num">${s.id || globalIdx + 1}</td>
      <td class="title">${esc(s.title || s.Text || '(untitled)')}</td>
      <td class="verses">${s.verseCount || s.verses || 0}</td>
    </tr>`;
  }).join('');
  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  const el = document.getElementById('pagination');
  if (totalPages <= 1) { el.innerHTML = ''; return; }
  let h = '';
  // Prev
  h += `<button class="pbtn" onclick="goPage(${_page - 1})" ${_page <= 1 ? 'disabled' : ''}>‹ Prev</button>`;
  h += `<span class="pinfo">Page ${_page} of ${totalPages}</span>`;
  // Page numbers (show max 7)
  let start = Math.max(1, _page - 3);
  let end = Math.min(totalPages, _page + 3);
  if (start > 1) { h += `<button class="pbtn" onclick="goPage(1)">1</button>`; if (start > 2) h += `<span class="psep">…</span>`; }
  for (let i = start; i <= end; i++) {
    h += `<button class="pbtn ${i === _page ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
  }
  if (end < totalPages) { if (end < totalPages - 1) h += `<span class="psep">…</span>`; h += `<button class="pbtn" onclick="goPage(${totalPages})">${totalPages}</button>`; }
  // Next
  h += `<button class="pbtn" onclick="goPage(${_page + 1})" ${_page >= totalPages ? 'disabled' : ''}>Next ›</button>`;
  el.innerHTML = h;
}

function goPage(p) {
  _page = p;
  renderSongTable();
  closeVerses();
}

function filterSongs() {
  const q = document.getElementById('songSearch').value.toLowerCase();
  const all = window._allSongs || [];
  if (!q) { _filteredSongs = all; } else {
    _filteredSongs = all.filter(s => (s.title || s.Text || '').toLowerCase().includes(q));
  }
  _page = 1;
  renderSongTable();
}

/* ── Verse panel ──────────────────────────── */
function showVerses(gidx) {
  const all = window._allSongs || [];
  const song = all[gidx];
  if (!song) return;
  document.querySelectorAll('#songBody tr').forEach(r => r.classList.remove('active'));
  const row = document.querySelector(`#songBody tr[data-gidx="${gidx}"]`);
  if (row) row.classList.add('active');

  const panel = document.getElementById('versePanel');
  const verses = song.verses_text || [];
  let vhtml = '';
  if (verses.length) {
    verses.forEach((v, vi) => {
      let text = esc(v).replace(/`/g, ' ').replace(/_/g, ' ');
      vhtml += `<div class="vitem"><span class="vtag">v${vi+1}</span>${text}</div>`;
    });
  } else {
    vhtml = `<div class="vitem" style="color:var(--text-dim)">${song.verseCount || 0} verse${song.verseCount !== 1 ? 's' : ''}</div>`;
  }
  panel.innerHTML = `
    <div class="vheader">
      <div class="vtitle">${esc(song.title || song.Text || 'Song')}</div>
      <button class="vclose" onclick="closeVerses()">✕</button>
    </div>
    ${vhtml}`;
  panel.classList.add('visible');
}

function closeVerses() {
  document.getElementById('versePanel').classList.remove('visible');
  document.querySelectorAll('#songBody tr').forEach(r => r.classList.remove('active'));
}

/* ── Copy song list ───────────────────────── */
function copySongList() {
  const all = window._allSongs || [];
  if (!all.length) return;
  const songs = _selected.size > 0 && _selected.size < all.length
    ? all.filter((_, i) => _selected.has(i))
    : all;
  const text = songs.map((s, i) =>
    `${String(s.id || i + 1).padStart(3)}. ${s.title || s.Text || '(untitled)'} (${s.verseCount || 0} verses)`
  ).join('\n');
  navigator.clipboard.writeText(text).then(() => flash('📋 Song list copied'));
}

/* ── Export as Text ──────────────────────── */
function exportText() {
  if (!currentFile) return;
  const fd = new FormData();
  fd.append('file', currentFile);
  const all = window._allSongs || [];
  if (_selected.size > 0 && _selected.size < all.length) {
    fd.append('selected', Array.from(_selected).join(','));
  }
  const btn = document.querySelector('.btn-secondary:nth-child(3)');
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="border-top-color:var(--accent)"></span>';

  fetch('/export/txt', { method: 'POST', body: fd })
    .then(r => r.ok ? r.blob() : r.json().then(e => { throw new Error(e.detail); }))
    .then(blob => {
      const base = currentFile.name.replace(/\.(json|vpc)$/i, '');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = base + '.txt';
      document.body.appendChild(a); a.click();
      a.remove(); URL.revokeObjectURL(url);
      btn.disabled = false;
      btn.innerHTML = orig;
    })
    .catch(err => {
      flash(err.message, true);
      btn.disabled = false;
      btn.innerHTML = orig;
    });
}

/* ── Convert ──────────────────────────────── */
function convert() {
  if (!currentFile) return;
  const btn = document.getElementById('convertBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Converting…';

  const endpoint = currentDirection === 'json2vpc' ? '/convert' : '/reverse';
  const fd = new FormData();
  fd.append('file', currentFile);
  const all = window._allSongs || [];
  if (_selected.size > 0 && _selected.size < all.length) {
    fd.append('selected', Array.from(_selected).join(','));
  }

  fetch(endpoint, { method: 'POST', body: fd })
    .then(r => r.ok ? r.blob() : r.json().then(e => { throw new Error(e.detail || 'Conversion failed'); }))
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
      flash(err.message, true);
      btn.innerHTML = currentDirection === 'json2vpc' ? '⬇ Convert to VPC' : '⬇ Extract to JSON';
      btn.disabled = false;
    });
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(PAGE)


@app.post("/preview")
async def preview_file(file: UploadFile = File(...)):
    content = await file.read()
    name = file.filename or ""
    is_vpc = name.lower().endswith(".vpc")

    try:
        if is_vpc:
            if not zipfile.is_zipfile(io.BytesIO(content)):
                raise HTTPException(400, "Invalid VPC file (not a ZIP archive)")
            with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                names = zf.namelist()
                if not names:
                    raise HTTPException(400, "VPC file is empty")
                vpc_text = zf.read(names[0]).decode("utf-8")
            data = vpc_to_json(vpc_text)
        else:
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
        verse_texts = []
        for v in verses:
            vt = v.get("Text", "")
            # Split on backtick-newline patterns for readable display
            verse_texts.append(vt)
        song_list.append({
            "title": s.get("Text", s.get("Title", "")),
            "verseCount": count,
            "id": s.get("ID"),
            "verses_text": verse_texts,
        })

    meta = {
        "songCount": len(songs),
        "verseCount": total_verses,
        "songs": song_list,
        "originalSize": round(len(content) / 1024, 1),
    }

    for key in ["Text", "Description", "Publisher", "Author", "Administrator",
                 "Copyright", "Abbreviation", "Language", "Guid"]:
        if key in data:
            val = data[key]
            if isinstance(val, str):
                meta[key] = val

    return meta


@app.post("/convert")
async def convert_to_vpc(file: UploadFile = File(...), selected: str = Form("")):
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(400, "Please upload a .json file")

    content = await file.read()
    try:
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    # Apply selection filter
    if selected:
        indices = [int(i) for i in selected.split(",") if i.strip().isdigit()]
        songs = data.get("Songs", [])
        if indices:
            data["Songs"] = [songs[i] for i in indices if 0 <= i < len(songs)]

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
async def convert_to_json(file: UploadFile = File(...), selected: str = Form("")):
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

    # Apply selection filter
    if selected:
        indices = [int(i) for i in selected.split(",") if i.strip().isdigit()]
        songs = data.get("Songs", [])
        if indices:
            data["Songs"] = [songs[i] for i in indices if 0 <= i < len(songs)]

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


@app.post("/export/txt")
async def export_text(file: UploadFile = File(...), selected: str = Form("")):
    """Export song lyrics as formatted plain text."""
    content = await file.read()
    name = file.filename or ""
    is_vpc = name.lower().endswith(".vpc")

    try:
        if is_vpc:
            if not zipfile.is_zipfile(io.BytesIO(content)):
                raise HTTPException(400, "Invalid VPC file (not a ZIP archive)")
            with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                names = zf.namelist()
                if not names:
                    raise HTTPException(400, "VPC file is empty")
                vpc_text = zf.read(names[0]).decode("utf-8")
            data = vpc_to_json(vpc_text)
        else:
            data = json.loads(content)
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(400, f"Cannot parse file: {e}")

    text_title = data.get("Text", data.get("Description", "Songbook"))
    author = data.get("Author", "")
    publisher = data.get("Publisher", "")
    songs = data.get("Songs", [])

    # Apply selection filter
    if selected:
        indices = [int(i) for i in selected.split(",") if i.strip().isdigit()]
        if indices:
            songs = [songs[i] for i in indices if 0 <= i < len(songs)]

    lines = []
    sep = "=" * 60
    sub = "-" * 60

    lines.append(sep)
    lines.append(f"  {text_title}".center(len(sep) - 4))
    if author:
        lines.append(f"  Author: {author}")
    if publisher:
        lines.append(f"  Publisher: {publisher}")
    lines.append(sep)
    lines.append("")
    lines.append(f"Total: {len(songs)} songs")
    lines.append("")

    for i, s in enumerate(songs):
        title = s.get("Text", s.get("Title", f"Song {i+1}"))
        verses = s.get("Verses", [])
        lines.append(sub)
        lines.append(f"  {i+1}. {title} ({len(verses)} verses)")
        lines.append(sub)
        lines.append("")
        for j, v in enumerate(verses):
            text = v.get("Text", "")
            # Remove backtick markers, clean spacing
            cleaned = text.replace("`", " ").replace("_", " ").strip()
            # Collapse multiple spaces
            cleaned = " ".join(cleaned.split())
            if cleaned:
                lines.append(f"  {cleaned}")
            lines.append("")
        lines.append("")

    text_content = "\n".join(lines)
    base_name = name.rsplit(".", 1)[0] if "." in name else "songbook"
    if base_name.endswith(".json"):
        base_name = base_name[:-5]
    if base_name.endswith(".vpc"):
        base_name = base_name[:-4]

    bytes_content = text_content.encode("utf-8")
    return Response(
        content=bytes_content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}.txt"',
            "Content-Length": str(len(bytes_content)),
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
