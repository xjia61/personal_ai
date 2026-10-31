import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.database import get_db
from app.routers.applications import router
from app.models import Application, Job, ResumeVersion


def summary(status='preparing'):
    return dict(id=1, job_id=5, job_title='Scientist', company='Example', resume_version_id=2,
                resume_name='Science', resume_version=3, status=status,
                application_url='https://example.invalid/apply', created_at=datetime.now(timezone.utc))


def client_for(db):
    app = FastAPI()
    app.include_router(router)
    async def override():
        yield db
    app.dependency_overrides[get_db] = override
    return TestClient(app)


def rows_result(rows):
    return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows, first=lambda: rows[0] if rows else None))


def test_listing_and_single_application():
    db = SimpleNamespace(execute=AsyncMock(return_value=rows_result([summary()])))
    with client_for(db) as client:
        response = client.get('/api/applications?job_id=5')
        assert response.status_code == 200
        assert response.json()[0]['resume_name'] == 'Science'
        assert 'description' not in response.json()[0]
        assert 'applications.job_id' in str(db.execute.call_args.args[0])
        assert client.get('/api/applications/1').json()['job_title'] == 'Scientist'


@pytest.mark.parametrize('status', ['applied', 'screening', 'interview', 'rejected', 'offer', 'withdrawn', 'preparing', 'ready_for_review'])
def test_status_update(status):
    application = SimpleNamespace(status='preparing')
    db = SimpleNamespace(get=AsyncMock(return_value=application), commit=AsyncMock(),
                         execute=AsyncMock(return_value=rows_result([summary(status)])))
    with client_for(db) as client:
        response = client.patch('/api/applications/1/status', json={'status': status})
        assert response.status_code == 200
        assert response.json()['status'] == status
        assert application.status == status
        db.commit.assert_awaited_once()


def test_missing_application_and_invalid_status():
    db = SimpleNamespace(get=AsyncMock(return_value=None), execute=AsyncMock(return_value=rows_result([])))
    with client_for(db) as client:
        assert client.get('/api/applications/999').status_code == 404
        assert client.patch('/api/applications/999/status', json={'status': 'applied'}).status_code == 404
        db.get.reset_mock()
        assert client.patch('/api/applications/1/status', json={'status': 'submitted_by_bot'}).status_code == 422
        db.get.assert_not_awaited()


def test_prepare_reuses_exact_application():
    existing = SimpleNamespace(**{k: v for k, v in summary('applied').items() if k in {'id', 'job_id', 'resume_version_id', 'status', 'application_url', 'created_at'}})
    db = SimpleNamespace(get=AsyncMock(side_effect=[SimpleNamespace(id=5), SimpleNamespace(id=2, status='approved')]),
        execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: existing))), commit=AsyncMock())
    with client_for(db) as client:
        response = client.post('/api/applications/prepare', json={'job_id': 5, 'resume_version_id': 2})
        assert response.status_code == 200
        assert response.json()['application_id'] == 1
        assert response.json()['status'] == 'applied'
        assert db.get.call_args_list[0].kwargs['with_for_update'] is True


def test_autofill_preserves_applied_status():
    from unittest.mock import patch
    from app.routers.applications import autofill_application
    application = SimpleNamespace(id=1, resume_version_id=2, status='applied', application_url='https://example.invalid')
    db = SimpleNamespace(get=AsyncMock(side_effect=[application, SimpleNamespace(status='approved', content='Resume', version=3)]),
        execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: object()))),
        commit=AsyncMock(), refresh=AsyncMock())
    result = dict(status='ready_for_review', url='https://example.invalid', filled_fields=[], skipped_fields=[],
                  resume_uploaded=True, manual_review_required=True)
    with patch('app.routers.applications.build_resume_pdf', return_value=b'pdf'), \
         patch('app.routers.applications.autofill_application_form', new=AsyncMock(return_value=result)):
        response = asyncio.run(autofill_application(1, db))
    assert application.status == response['status'] == 'applied'
