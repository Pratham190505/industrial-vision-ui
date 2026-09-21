import io
import os
import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Set testing environment variables before importing settings
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_minimum_32_characters_long_for_tests"

from unittest.mock import AsyncMock, patch
from app.core.config import get_settings
from app.core.security import create_access_token
from app.api.dependencies import get_db_dep
from app.main import app


class MockCursor:
    def __init__(self, items):
        self._items = list(items)

    def sort(self, key, direction=1):
        reverse = direction == -1
        self._items = sorted(self._items, key=lambda x: str(x.get(key, "")), reverse=reverse)
        return self

    def skip(self, n):
        self._items = self._items[n:]
        return self

    def limit(self, n):
        self._items = self._items[:n]
        return self

    async def to_list(self, length=None):
        if length is not None:
            return self._items[:length]
        return self._items


class MockAsyncCollection:
    def __init__(self):
        self._docs = {}

    async def create_index(self, keys, **kwargs):
        return "mock_index"

    async def insert_one(self, doc):
        _id = str(doc.get("_id"))
        self._docs[_id] = dict(doc)
        return type("InsertResult", (), {"inserted_id": _id})()

    async def find_one(self, query):
        for doc in self._docs.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return dict(doc)
        return None

    async def count_documents(self, query):
        count = 0
        for doc in self._docs.values():
            if all(doc.get(k) == v for k, v in query.items()):
                count += 1
        return count

    def find(self, query=None):
        query = query or {}
        matches = [
            dict(doc) for doc in self._docs.values()
            if all(doc.get(k) == v for k, v in query.items())
        ]
        return MockCursor(matches)

    async def update_one(self, query, update):
        for doc in self._docs.values():
            if all(doc.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    doc.update(update["$set"])
                return type("UpdateResult", (), {"modified_count": 1})()
        return type("UpdateResult", (), {"modified_count": 0})()


class MockAsyncDatabase:
    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = MockAsyncCollection()
        return self._collections[name]


@pytest.fixture(autouse=True)
def mock_mongodb():
    """Mock MongoDB connection and operations during testing."""
    mock_db = MockAsyncDatabase()
    app.dependency_overrides[get_db_dep] = lambda: mock_db
    with patch("app.core.database.get_database", return_value=mock_db), \
         patch("app.core.database.connect_to_mongo", new_callable=AsyncMock), \
         patch("app.core.database.close_mongo_connection", new_callable=AsyncMock):
        yield mock_db
    app.dependency_overrides.pop(get_db_dep, None)


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Ensure cached settings are cleared between test environments."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    """Synchronous test client fixture for FastAPI app endpoints."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user():
    return {"user_id": "usr_test_12345", "email": "operator@warehouse.ai"}


@pytest.fixture
def auth_headers(test_user):
    """Return Bearer authorization headers for the primary test user."""
    token = create_access_token(data={"sub": test_user["user_id"], "email": test_user["email"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_headers():
    """Return Bearer authorization headers for a secondary user."""
    token = create_access_token(data={"sub": "usr_other_99999", "email": "other@warehouse.ai"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_image_bytes():
    """Create valid JPEG image bytes in memory."""
    img = Image.new("RGB", (640, 480), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def sample_png_bytes():
    """Create valid PNG image bytes in memory."""
    img = Image.new("RGB", (320, 240), color=(50, 80, 120))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_video_path(tmp_path):
    """Generate a tiny 5-frame MP4 video for fast, self-contained testing."""
    import cv2
    import numpy as np

    video_file = tmp_path / "test_forklift.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_file), fourcc, 10.0, (160, 120))
    for i in range(5):
        frame = np.full((120, 160, 3), fill_value=(i * 40, 100, 150), dtype=np.uint8)
        out.write(frame)
    out.release()
    return video_file


@pytest.fixture
def sample_video_bytes(sample_video_path):
    """Return bytes of the generated test video."""
    return sample_video_path.read_bytes()
