from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, glob, json, datetime

from packages.agents.prompt_loader import (
    load_prompt, save_prompt, render_prompt, load_sample_vars, default_vars, PROMPTS_BASE, load_required
)
from packages.persistence.db import SessionLocal, init_db
from packages.persistence.models import Run, Step, Measure, Snapshot as DBSnapshot
from apps.api.runner import run_parser

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/config.json"))

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"gemini_api_key": ""}

def save_config(cfg: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def mask_key(k: str) -> str:
    if not k: return ""
    if len(k) <= 6: return "*" * len(k)
    return k[:3] + "*" * (len(k)-7) + k[-4:]

app = FastAPI(title="Autoparser API", version="0.6.0")

CORS_ORIGINS = os.getenv("CORS_ORIGINS")
if CORS_ORIGINS:
    origins = [o.strip() for o in CORS_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

class RunRequest(BaseModel):
    region: str

@app.get("/health")
def health():
    return {"status": "ok"}

# ---- CONFIG (Gemini key) ----
class ConfigRequest(BaseModel):
    gemini_api_key: Optional[str] = ""

@app.get("/config")
def get_config():
    cfg = load_config()
    return {"gemini_api_key": mask_key(cfg.get("gemini_api_key",""))}

@app.post("/config")
def post_config(body: ConfigRequest):
    cfg = load_config()
    if body.gemini_api_key is not None:
        cfg["gemini_api_key"] = body.gemini_api_key
    save_config(cfg)
    return {"status": "ok"}

# ---- PARSER RUNS ----
@app.post("/parse/start")
def start_parse(req: RunRequest):
    init_db()
    result = run_parser(req.region)
    return result

@app.get("/runs", response_model=List[dict])
def list_runs():
    init_db()
    db = SessionLocal()
    try:
        q = db.query(Run).order_by(Run.id.desc()).limit(100).all()
        return [{
            "id": r.id, "region": r.region, "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "found": r.found, "processed": r.processed, "ok": r.ok, "errors": r.errors
        } for r in q]
    finally:
        db.close()

@app.get("/runs/{run_id}")
def get_run(run_id: int):
    init_db()
    db = SessionLocal()
    try:
        r = db.query(Run).get(run_id)
        if not r: raise HTTPException(404, "Run not found")
        return {
            "id": r.id, "region": r.region, "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "found": r.found, "processed": r.processed, "ok": r.ok, "errors": r.errors
        }
    finally:
        db.close()

@app.get("/runs/{run_id}/steps")
def get_steps(run_id: int):
    init_db()
    db = SessionLocal()
    try:
        steps = db.query(Step).filter(Step.run_id==run_id).order_by(Step.id.asc()).all()
        return [{
            "id": s.id, "stage": s.stage, "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            "has_payload": bool(s.payload)
        } for s in steps]
    finally:
        db.close()

@app.get("/runs/{run_id}/steps/{step_id}")
def get_step(run_id: int, step_id: int):
    init_db()
    db = SessionLocal()
    try:
        s = db.query(Step).filter(Step.run_id==run_id, Step.id==step_id).first()
        if not s: raise HTTPException(404, "Step not found")
        return {
            "id": s.id, "stage": s.stage, "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            "payload": s.payload
        }
    finally:
        db.close()

@app.get("/runs/{run_id}/steps/{step_id}/download")
def download_step(run_id: int, step_id: int, fmt: str = Query("json", enum=["json","txt"])):
    init_db()
    db = SessionLocal()
    try:
        s = db.query(Step).filter(Step.run_id==run_id, Step.id==step_id).first()
        if not s or not s.payload: raise HTTPException(404, "No payload")
        if fmt == "json":
            return s.payload
        else:
            txt = json.dumps(s.payload, ensure_ascii=False, indent=2)
            return Response(content=txt, media_type="text/plain")
    finally:
        db.close()

# New: serve snapshot content (txt/html) for a step (expects FETCH payload with snapshot_id)
@app.get("/runs/{run_id}/steps/{step_id}/snapshot")
def get_snapshot_content(run_id: int, step_id: int, kind: str = Query("txt", enum=["txt","html"])):
    init_db()
    db = SessionLocal()
    try:
        s = db.query(Step).filter(Step.run_id==run_id, Step.id==step_id).first()
        if not s or not s.payload or "snapshot_id" not in s.payload:
            raise HTTPException(404, "Snapshot not found")
        snap_id = s.payload["snapshot_id"]
        snap = db.query(DBSnapshot).filter(DBSnapshot.id==snap_id).first()
        if not snap: raise HTTPException(404, "Snapshot record missing")
        path = snap.path_txt if kind=="txt" else snap.path_html
        if not path or not os.path.exists(path): raise HTTPException(404, "Snapshot file missing")
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        media = "text/plain" if kind=="txt" else "text/html"
        return Response(content=data, media_type=media)
    finally:
        db.close()

# New: list measures for a run (by SAVE steps)
@app.get("/runs/{run_id}/measures")
def get_run_measures(run_id: int):
    init_db()
    db = SessionLocal()
    try:
        steps = db.query(Step).filter(Step.run_id==run_id, Step.stage=="SAVE", Step.status=="ok").all()
        ids = [s.payload.get("msr_intlid") for s in steps if s.payload]
        ids = [i for i in ids if i]
        measures = []
        for mid in ids:
            m = db.query(Measure).filter(Measure.msr_intlid==mid).first()
            if m:
                measures.append({"msr_intlid": mid, "region_code": m.region_code, "prglvl": m.prglvl, "segmnt": m.segmnt, "typeid": m.typeid})
        return {"items": measures}
    finally:
        db.close()

# New: get measure card
@app.get("/measures/{msr_intlid}")
def get_measure(msr_intlid: str):
    init_db()
    db = SessionLocal()
    try:
        m = db.query(Measure).filter(Measure.msr_intlid==msr_intlid).first()
        if not m: raise HTTPException(404, "Measure not found")
        return {"msr_intlid": msr_intlid, "card": m.card}
    finally:
        db.close()

# ---- PROMPTS API (unchanged) ----
@app.get("/prompts", response_model=List[str])
def list_prompts():
    paths = sorted(glob.glob(os.path.join(PROMPTS_BASE, "*.md")))
    return [os.path.splitext(os.path.basename(p))[0] for p in paths]

@app.get("/prompts/{name}")
def get_prompt(name: str):
    try:
        content = load_prompt(name)
        return {"name": name if name.endswith(".md") else f"{name}.md", "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Prompt not found")

class SavePromptRequest(BaseModel):
    content: str

@app.put("/prompts/{name}")
def put_prompt(name: str, body: SavePromptRequest):
    save_prompt(name, body.content)
    return {"status": "ok"}

class RenderRequest(BaseModel):
    variables: Dict[str, Any] = {}
    allow_missing: Optional[bool] = False

@app.post("/prompts/{name}/render")
def post_render(name: str, body: RenderRequest):
    try:
        result = render_prompt(name, body.variables or {}, allow_missing=bool(body.allow_missing))
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Prompt not found")

@app.get("/prompts/{name}/vars")
def get_vars(name: str):
    merged = default_vars()
    sample = load_sample_vars(name)
    merged.update(sample)
    required = load_required(name)
    return {"vars": merged, "sample_only": sample, "required": required}

# ---- Admin UI ----
admin_path = os.path.join(os.path.dirname(__file__), "admin")
if os.path.exists(admin_path):
    app.mount("/admin", StaticFiles(directory=admin_path, html=True), name="admin")
