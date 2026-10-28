"""Evaluation Centre endpoints for VerifyAI benchmark metrics."""

from __future__ import annotations

from fastapi import APIRouter
from app.services.evaluation_runner import get_latest_evaluation_results, run_benchmark_evaluation

router = APIRouter(prefix="/evaluation", tags=["Evaluation Centre"])


@router.get("/results", summary="Get latest evaluation and benchmark test results")
def get_evaluation_results() -> dict:
    return get_latest_evaluation_results()


@router.post("/run", summary="Trigger evaluation pipeline run on labelled benchmark set")
def trigger_evaluation_run() -> dict:
    return run_benchmark_evaluation()

