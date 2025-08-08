import os, json, asyncio, traceback
from celery import Celery
from datetime import datetime
from packages.persistence.db import SessionLocal, init_db
from packages.persistence.models import Run, Step, Source, Snapshot as DBSnapshot, Measure
from packages.agents.search import search_official_urls
from packages.scraper.fetch import fetch_and_snapshot
from packages.agents.gemini import GeminiClient
from packages.agents.id_builder import build_intlid
from packages.schemas.validator import validate_stage

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("autoparser", broker=REDIS_URL, backend=REDIS_URL)

def _new_step(db, run_id: int, stage: str, source_id: int | None = None) -> Step:
    st = Step(run_id=run_id, stage=stage, status="running", created_at=datetime.utcnow(), source_id=source_id)
    db.add(st); db.commit(); db.refresh(st); return st

def _finish_step(db, st: Step, status: str, payload: dict | None = None):
    st.status = status
    st.payload = payload
    st.finished_at = datetime.utcnow()
    db.commit()

@celery_app.task
def run_parser(region: str):
    init_db()
    db = SessionLocal()
    run = Run(region=region, status="running", started_at=datetime.utcnow())
    db.add(run); db.commit(); db.refresh(run)

    try:
        # Stage: SEARCH
        step_search = _new_step(db, run.id, "SEARCH")
        urls = search_official_urls(region, max_results=6)
        run.found = len(urls); db.commit()
        _finish_step(db, step_search, "ok", {"urls": urls})

        gclient = GeminiClient()

        e_results = []  # collected per-url cards (E1..E7)

        for url in urls:
            # Create or get Source
            src = Source(url=url, domain="", is_official=True, region_code=str(os.getenv("REGION_DEFAULT_CODE","92")), first_seen_at=datetime.utcnow(), status="new")
            try:
                db.add(src); db.commit(); db.refresh(src)
            except Exception:
                db.rollback()
                src = db.query(Source).filter_by(url=url).first()

            # FETCH
            st_fetch = _new_step(db, run.id, "FETCH", src.id)
            snap = asyncio.get_event_loop().run_until_complete(fetch_and_snapshot(url))
            dbsnap = DBSnapshot(source_id=src.id, sha256=snap.sha256, stored_at=datetime.utcnow(),
                                path_html=snap.path_html, path_txt=snap.path_txt, http_status=snap.http_status, charset=snap.charset)
            db.add(dbsnap); db.commit(); db.refresh(dbsnap)
            _finish_step(db, st_fetch, "ok", {"snapshot_id": dbsnap.id, "path_html": snap.path_html, "path_txt": snap.path_txt})

            # CLEAN
            st_clean = _new_step(db, run.id, "CLEAN", src.id)
            with open(snap.path_txt, "r", encoding="utf-8") as f:
                source_text = f.read()
            _finish_step(db, st_clean, "ok", {"chars": len(source_text)})

            # E1..E7
            stage_map = [
                ("E1","E1_Passport"),
                ("E2","E2_Finance_Legal"),
                ("E3","E3_Operations"),
                ("E4","E4_DNA"),
                ("E5","E5_Applicant_Profile"),
                ("E6","E6_Scoring"),
                ("E7","E7_Strategic_Insights")
            ]
            stage_outputs = {}
            for stage, prompt in stage_map:
                st = _new_step(db, run.id, stage, src.id)
                vars = {
                    "msr_geocde": os.getenv("REGION_DEFAULT_CODE","92"),
                    "msr_geonme": "Регион",  # UI/lookup can set exact name
                    "msr_prglvl": "REG",
                    "msr_srclnk": url,
                    "SOURCE_TEXT": source_text,
                    "TODAY": datetime.utcnow().strftime("%d.%m.%Y")
                }
                try:
                    out = gclient.run_stage(stage, prompt, vars)
                    ok, err = validate_stage(stage, out)
                    if not ok:
                        _finish_step(db, st, "invalid", {"error": err, "raw": out})
                    else:
                        _finish_step(db, st, "ok", out)
                        stage_outputs[stage] = out
                except Exception as e:
                    _finish_step(db, st, "error", {"error": str(e)})
                    run.errors += 1; db.commit()

            # BUILD_ID
            if all(k in stage_outputs for k in ("E1","E4")):
                st_build = _new_step(db, run.id, "BUILD_ID", src.id)
                try:
                    msr_intlid = build_intlid(stage_outputs["E1"], stage_outputs["E4"], db)
                    _finish_step(db, st_build, "ok", {"msr_intlid": msr_intlid})
                    # SAVE
                    st_save = _new_step(db, run.id, "SAVE", src.id)
                    card = {}
                    for k,v in stage_outputs.items():
                        card.update(v)
                    card["msr_intlid"] = msr_intlid
                    # provenance (минимально)
                    card["provenance"] = {"region_input": region, "source_urls": [url]}
                    # Upsert Measure
                    m = Measure(msr_intlid=msr_intlid, card=card,
                                region_code=stage_outputs["E1"]["msr_geocde"],
                                prglvl=stage_outputs["E1"]["msr_prglvl"],
                                segmnt=stage_outputs["E4"]["msr_segmnt"],
                                typeid=stage_outputs["E4"]["msr_typeid"])
                    db.merge(m); db.commit()
                    _finish_step(db, st_save, "ok", {"msr_intlid": msr_intlid})
                    run.ok += 1; db.commit()
                except Exception as e:
                    _finish_step(db, st_build, "error", {"error": str(e)})
                    run.errors += 1; db.commit()

            run.processed += 1; db.commit()

        run.status = "done"; run.finished_at = datetime.utcnow(); db.commit()
        return {"run_id": run.id, "status": run.status, "found": run.found}
    except Exception as e:
        if run:
            run.status = "error"; db.commit()
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        db.close()
