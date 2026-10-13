from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, directory: str) -> bool:
    path = Path(directory)
    if not path.is_dir():
        return False
    app.mount("/", StaticFiles(directory=path, html=True), name="frontend")
    return True
