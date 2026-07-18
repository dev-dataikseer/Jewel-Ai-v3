"""Wave 3/4 regression: path containment, batch aggregates."""
from pathlib import Path

import pytest

from app.auth.security import hash_password
from app.models import Batch, GenerationJob, User


def test_storage_read_upload_rejects_traversal(tmp_path):
    from app.storage.local import StorageService

    svc = StorageService()
    svc.backend = "local"
    svc.uploads_dir = Path(tmp_path)
    (tmp_path / "ok.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    data, ctype = svc.read_upload("ok.png")
    assert data.startswith(b"\x89PNG")
    assert "png" in ctype or ctype == "application/octet-stream"

    with pytest.raises(FileNotFoundError):
        svc.read_upload("../secrets.txt")
    with pytest.raises(FileNotFoundError):
        svc.read_upload("..\\secrets.txt")
    assert svc.resolve_path("/uploads/../secrets.txt") is None


def test_batch_status_counts_group_by(db_session):
    """When include_jobs=False, counts come from GROUP BY (no job list)."""
    from app.api.routers.jobs import _batch_to_out

    user = User(
        email="wave3@test.local",
        hashed_password=hash_password("password123"),
        role="user",
        credits=10,
    )
    db_session.add(user)
    db_session.flush()

    batch = Batch(
        name="wave3",
        workflow="CATALOG_IMAGE",
        jewelry_type="Ring",
        status="RUNNING",
        total_jobs=3,
        completed_jobs=1,
        user_id=user.id,
    )
    db_session.add(batch)
    db_session.flush()
    for status in ("PENDING", "PROCESSING", "COMPLETED"):
        db_session.add(
            GenerationJob(
                user_id=user.id,
                batch_id=batch.id,
                workflow="CATALOG_IMAGE",
                status=status,
                input_url="/uploads/x.jpg",
            )
        )
    db_session.commit()

    out = _batch_to_out(db_session, batch, include_jobs=False)
    assert out.pending_jobs == 1
    assert out.processing_jobs == 1
    assert out.jobs == []

    out_full = _batch_to_out(db_session, batch, include_jobs=True)
    assert len(out_full.jobs) == 3
    assert out_full.pending_jobs == 1
