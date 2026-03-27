import contextlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from arxiv_diff import __version__
from db.models import init_db
from api.routes import router
from typing import AsyncIterator

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    # Note: the watcher check on startup will be invoked from main.py's `serve` command 
    # to avoid starting the watcher when api is just imported.
    yield
    print("Shutting down arxiv-diff API...")

app = FastAPI(title="arxiv-diff API", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"name": "arxiv-diff", "version": __version__}

app.mount("/", StaticFiles(directory="web", html=True), name="web")
