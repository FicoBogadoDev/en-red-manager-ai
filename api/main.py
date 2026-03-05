from pathlib import Path

import dotenv
from fastapi import FastAPI

from manager_ai.config import build_agent

from .routes import create_router

dotenv.load_dotenv()

_DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "dev.toml"


def create_app(config_path: Path = _DEFAULT_CONFIG) -> FastAPI:
    app = FastAPI(title="Manager AI — En Red Rosario")
    agent = build_agent(config_path)
    app.include_router(create_router(agent))
    return app


app = create_app()
