import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

import reliabase.config as config
from reliabase.api import main
from reliabase.api import deps


@pytest.fixture()
def temp_db() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        os.environ["RELIABASE_DATABASE_URL"] = f"sqlite:///{db_path}"
        # Reload config to pick up env
        import importlib

        importlib.reload(config)
        engine = config.get_engine()
        SQLModel.metadata.create_all(engine)
        yield db_path


@pytest.fixture()
def session(temp_db) -> Generator[Session, None, None]:
    engine = config.get_engine()
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(session) -> Generator[TestClient, None, None]:
    def override_session():
        with Session(config.get_engine()) as s:
            yield s

    main.app.dependency_overrides[deps.get_db_session] = override_session
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()
