"""Integration tests for the FastAPI application."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_create_person(client: AsyncClient):
    payload = {
        "name": "테스트 유저",
        "birth_year": 1992,
        "residence": "서울",
        "career_history": [{"role": "엔지니어", "org": "테스트코프", "years": "2020-현재"}],
        "education": [],
        "interests": ["음악", "코딩"],
        "custom_directions": [],
    }
    resp = await client.post("/api/v1/persons", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "테스트 유저"
    assert data["birth_year"] == 1992
    return data["id"]


async def test_get_person(client: AsyncClient):
    # Create first
    payload = {"name": "조회 테스트"}
    resp = await client.post("/api/v1/persons", json=payload)
    assert resp.status_code == 201
    person_id = resp.json()["id"]

    # Get
    resp = await client.get(f"/api/v1/persons/{person_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == person_id


async def test_get_person_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/persons/99999")
    assert resp.status_code == 404


async def test_submit_survey(client: AsyncClient):
    resp = await client.post("/api/v1/persons", json={"name": "설문 테스트"})
    person_id = resp.json()["id"]

    survey = {
        "responses": {
            "energy": {"score": 2, "label": "E-I"},
            "information": {"score": 5, "label": "S-N"},
            "decisions": {"score": 3, "label": "T-F"},
            "lifestyle": {"score": 6, "label": "J-P"},
        },
        "open_answers": {"self_description": "조용하고 분석적"},
    }
    resp = await client.post(f"/api/v1/persons/{person_id}/survey", json=survey)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mbti_type"] == "INTP"


async def test_get_system_prompt(client: AsyncClient):
    resp = await client.post("/api/v1/persons", json={"name": "프롬프트 테스트"})
    person_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/persons/{person_id}/system-prompt")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_prompt" in data
    assert "프롬프트 테스트" in data["system_prompt"]


async def test_create_session(client: AsyncClient):
    resp = await client.post("/api/v1/persons", json={"name": "세션 테스트"})
    person_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/persons/{person_id}/sessions")
    assert resp.status_code == 201
    data = resp.json()
    assert data["person_id"] == person_id


async def test_ingest_logs(client: AsyncClient):
    resp = await client.post("/api/v1/persons", json={"name": "민준"})
    person_id = resp.json()["id"]

    log = (
        "[오전 10:00] 지수 : 오늘 뭐 해?\n"
        "[오전 10:01] 민준 : 그냥 집에 있어 ㅋㅋ\n"
        "[오전 10:02] 지수 : 심심하지?\n"
        "[오전 10:03] 민준 : 좀 ㅋ 그래도 괜찮아\n"
    )
    resp = await client.post(
        f"/api/v1/persons/{person_id}/ingest-logs",
        json={"target_name": "민준", "raw_text": log, "format_hint": "kakao"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["speech_patterns"] != {}


async def test_delete_person(client: AsyncClient):
    resp = await client.post("/api/v1/persons", json={"name": "삭제 테스트"})
    person_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/persons/{person_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/persons/{person_id}")
    assert resp.status_code == 404
