from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.schemas.items_entities import ItemProcessingTask


class ProcessingTaskDataSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: UUID
    user_id: UUID
    image_url: str = Field(
        ...,
        description="S3/MinIO object key, не HTTP URL",
        min_length=1,
    )


class ProcessingTaskSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: str
    data: ProcessingTaskDataSchema

    @field_validator("event_type")
    @classmethod
    def supported_event_only(cls, v: str) -> str:
        if v != "new_item_uploaded":
            raise ValueError(f"unsupported event_type: {v!r}, expected new_item_uploaded")
        return v

    def to_domain(self) -> ItemProcessingTask:
        return ItemProcessingTask(
            item_id=self.data.item_id,
            user_id=self.data.user_id,
            object_key=self.data.image_url,
        )
