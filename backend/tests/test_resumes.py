from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.resumes import require_draft


def test_draft_can_be_edited():
    resume = SimpleNamespace(status="draft")
    require_draft(resume)


def test_approved_resume_is_locked():
    resume = SimpleNamespace(status="approved")

    with pytest.raises(HTTPException) as error:
        require_draft(resume)

    assert error.value.status_code == 409