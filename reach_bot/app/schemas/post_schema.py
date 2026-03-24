from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SourcePostOut(BaseModel):
    id: int
    telegram_message_id: int
    post_url: str
    post_text: Optional[str]
    published_at: datetime
    views_count: Optional[int]

    model_config = {"from_attributes": True}
