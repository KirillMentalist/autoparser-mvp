"""
Локальная реализация парсера без Celery для single-exe режима
"""
import os, json, asyncio, traceback
from datetime import datetime
from packages.persistence.db import SessionLocal, init_db
from packages.persistence.models import Run, Step, Source, Snapshot as DBSnapshot, Measure
from packages.agents.search import search_official_urls
from packages.scraper.fetch import fetch_and_snapshot
from packages.agents.gemini import GeminiClient
from packages.agents.id_builder import build_intlid
from packages.schemas.validator import validate_stage

def _new_step(db, run_id: int, stage: str, source_id: int | None = None) -> Step:
    st = Step(run_id=run_id, stage=stage, status="running", created_at=datetime.utcnow(), source_id=source_id)
    db.add(st); db.commit(); db.refresh(st); return st

def _finish_step(db, st: Step, status: str, payload: dict | None = None):
    st.status = status
    st.payload = payload
    st.finished_at = datetime.utcnow()
    db.commit()

def run_parser_local(region: str):
    """Локальная синхронная версия парсера"""
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

            if not src:
                continue

            # Process this URL through all stages
            try:
                # FETCH & CLEAN
                step_fetch = _new_step(db, run.id, "FETCH", src.id)
                result = fetch_and_snapshot(url)
                
                if result["status"] == "ok":
                    # Save snapshot
                    snap = DBSnapshot(source_id=src.id, raw_html=result.get("raw_html",""), 
                                    clean_text=result.get("clean_text",""), created_at=datetime.utcnow())
                    db.add(snap); db.commit()
                    _finish_step(db, step_fetch, "ok", result)
                    
                    # E1-E7 stages
                    stages = ["E1", "E2", "E3", "E4", "E5", "E6", "E7"]
                    e_data = {}
                    
                    for stage in stages:
                        step_e = _new_step(db, run.id, stage, src.id)
                        try:
                            variables = {"clean_text": result["clean_text"], "msr_geocde": region}
                            e_result = gclient.run_stage(stage, f"{stage}_Passport", variables)
                            
                            # Validate JSON schema
                            valid, error = validate_stage(stage, e_result)
                            if valid:
                                e_data[stage] = e_result
                                _finish_step(db, step_e, "ok", e_result)
                            else:
                                _finish_step(db, step_e, "error", {"error": f"Validation failed: {error}"})
                                
                        except Exception as e:
                            _finish_step(db, step_e, "error", {"error": str(e)})
                    
                    # BUILD_ID and SAVE if we have E1 and E4
                    if "E1" in e_data and "E4" in e_data:
                        step_id = _new_step(db, run.id, "BUILD_ID", src.id)
                        try:
                            intlid = build_intlid(e_data["E1"], e_data["E4"], db)
                            _finish_step(db, step_id, "ok", {"msr_intlid": intlid})
                            
                            # SAVE to measures table
                            step_save = _new_step(db, run.id, "SAVE", src.id)
                            measure = Measure(
                                msr_intlid=intlid,
                                card={**e_data["E1"], **e_data.get("E2",{}), **e_data.get("E3",{}), 
                                     **e_data.get("E4",{}), **e_data.get("E5",{}), **e_data.get("E6",{}), **e_data.get("E7",{})},
                                region_code=region,
                                prglvl=e_data["E1"].get("msr_prglvl",""),
                                segmnt=e_data["E4"].get("msr_segmnt",""),
                                typeid=e_data["E4"].get("msr_typeid",""),
                                chkdat=datetime.utcnow()
                            )
                            db.merge(measure); db.commit()
                            _finish_step(db, step_save, "ok", {"msr_intlid": intlid})
                            run.ok += 1
                            
                        except Exception as e:
                            _finish_step(db, step_id, "error", {"error": str(e)})
                            run.errors += 1
                else:
                    _finish_step(db, step_fetch, "error", result)
                    run.errors += 1
                    
            except Exception as e:
                run.errors += 1
                
            run.processed += 1
            db.commit()

        # Finish run
        run.status = "completed"
        run.finished_at = datetime.utcnow()
        db.commit()
        
        return {"status": "completed", "run_id": run.id}
        
    except Exception as e:
        run.status = "failed"
        run.finished_at = datetime.utcnow()
        db.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
