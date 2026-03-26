from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from domain.enums import AnalysisRunStatus, ConfirmationType, DetectedPostStatus


class AnalysisRunOut(BaseModel):
    id: int
    source_post_id: int
    started_by_user_id: int
    status: AnalysisRunStatus
    started_at: datetime
    finished_at: Optional[datetime]
    source_views: int
    confirmed_secondary_views: int
    total_confirmed_reach: int
    counted_posts_count: int
    skipped_posts_count: int
    notes: Optional[str]

    model_config = {"from_attributes": True}


class DetectedPostOut(BaseModel):
    id: int
    analysis_run_id: int
    source_post_id: int
    external_channel_name: Optional[str]
    external_channel_id: Optional[int]
    telegram_message_id: Optional[int]
    post_url: Optional[str]
    post_text: Optional[str]
    published_at: Optional[datetime]
    views_count: Optional[int]
    confirmation_type: Optional[ConfirmationType]
    status: DetectedPostStatus
    skip_reason: Optional[str]
    text_similarity_score: Optional[Decimal]

    model_config = {"from_attributes": True}
