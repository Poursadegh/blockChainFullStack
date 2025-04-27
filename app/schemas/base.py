from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: Optional[datetime] = None

class IDSchema(BaseSchema):
    id: int

class PaginationSchema(BaseSchema):
    page: int = 1
    per_page: int = 10
    total: int
    total_pages: int

class ResponseSchema(BaseSchema):
    success: bool = True
    message: str = "Operation successful"
    data: Optional[dict] = None 