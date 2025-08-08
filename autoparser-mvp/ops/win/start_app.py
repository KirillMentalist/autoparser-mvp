import os, sys, threading, time, webbrowser
import uvicorn

# Force local-singleexe mode + headless Playwright
os.environ.setdefault("LOCAL_SINGLEEXE", "1")
os.environ.setdefault("PLAYWRIGHT_HEADLESS", "true")

# Point Playwright to the bundled browsers next to the executable (ms-playwright/)
def _set_playwright_path():
    try:
        base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        mp = os.path.join(base, "ms-playwright")
        if not os.path.isdir(mp):
            # Fallback: try one level up
            mp2 = os.path.join(os.path.dirname(base), "ms-playwright")
            if os.path.isdir(mp2):
                mp = mp2
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", mp)
    except Exception:
        pass

_set_playwright_path()

def run_server():
    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000/admin/parser.html")
    t.join()
