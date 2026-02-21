"""Validation polling endpoints for SHACL report access.

Provides GET /api/validation/latest for the most recent validation
report summary and GET /api/validation/{event_id} for per-event reports.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import get_validation_queue, get_validation_service
from app.services.validation import ValidationService
from app.validation.queue import AsyncValidationQueue

router = APIRouter(prefix="/api")


@router.get("/validation/latest")
async def get_latest_validation(
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    validation_service: ValidationService = Depends(get_validation_service),
):
    """Return the latest validation report summary.

    First checks the in-memory cached report from the validation queue
    for fast response. If no validation has run yet, returns a 200 with
    conforms=null and a message.
    """
    # Fast path: check in-memory cache
    cached = validation_queue.latest_report
    if cached is not None:
        return asdict(cached)

    # Fallback: query triplestore
    summary = await validation_service.get_latest_summary()
    if summary is not None:
        return asdict(summary)

    # No reports yet
    return {"conforms": None, "message": "No validation reports yet"}


@router.get("/validation/{event_id}")
async def get_validation_by_event(
    event_id: str,
    validation_service: ValidationService = Depends(get_validation_service),
):
    """Return the validation report summary for a specific event.

    Constructs the event IRI from the event_id path parameter and
    queries the triplestore for the corresponding report.

    Returns 404 if no report found for the given event.
    """
    event_iri = f"urn:sempkm:event:{event_id}"
    summary = await validation_service.get_report_by_event(event_iri)
    if summary is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"No validation report found for event {event_id}"},
        )
    return asdict(summary)
