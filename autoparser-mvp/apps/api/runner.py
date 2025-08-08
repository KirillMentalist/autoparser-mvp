import os
from typing import Any

def run_parser(region: str) -> Any:
    """
    Переключатель между Celery и локальным потоком
    На основе переменной окружения LOCAL_SINGLEEXE
    """
    if os.getenv("LOCAL_SINGLEEXE"):
        # Локальный режим без Celery
        from apps.api.worker.local_impl import run_parser_local
        return run_parser_local(region)
    else:
        # Celery режим
        from apps.api.worker.app import run_parser as celery_run_parser
        task = celery_run_parser.delay(region)
        return {"status": "queued", "task_id": task.id}
