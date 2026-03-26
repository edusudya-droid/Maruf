from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.schemas.analysis_schema import DetectedPostOut


class ReportOut(BaseModel):
    post_url: str
    source_views: int
    counted_posts_count: int
    confirmed_secondary_views: int
    total_confirmed_reach: int
    skipped_posts_count: int
    finished_at: datetime
    status: str


class DetailedReportOut(BaseModel):
    report: ReportOut
    detected_posts: List[DetectedPostOut]
