import os
import tempfile
import warnings
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

import reliabase.config as config
from reliabase.api import main
from reliabase.api import deps

warnings.filterwarnings("ignore", message=r".*obj.from_orm.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=r".*obj.dict\(\).*", category=DeprecationWarning)
warnings.filterwarnings(
    "ignore",
    message=r".*obj.from_orm.*",
    category=DeprecationWarning,
    module=r"anyio._backends._asyncio",
)
warnings.filterwarnings(
    "ignore",
    message=r".*obj.dict\(\).*",
    category=DeprecationWarning,
    module=r"fastapi.encoders",
)
warnings.filterwarnings(
    "ignore",
    message=r"Precision loss occurred in moment calculation.*",
    category=RuntimeWarning,
    module=r"scipy.stats._continuous_distns",
)
warnings.simplefilter("ignore", DeprecationWarning)

pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning",
    "ignore:Precision loss occurred in moment calculation.*:RuntimeWarning",
)


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
        engine.dispose()


@pytest.fixture()
def session(temp_db) -> Generator[Session, None, None]:
    engine = config.get_engine()
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture()
def client(session) -> Generator[TestClient, None, None]:
    engine = config.get_engine()

    def override_session():
        with Session(engine) as s:
            yield s

    main.app.dependency_overrides[deps.get_db_session] = override_session
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()
    engine.dispose()
