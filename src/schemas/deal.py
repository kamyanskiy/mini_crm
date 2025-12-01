from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from models.deal import DealStage, DealStatus


class DealCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    contact_id: int | None = None
    amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = Field(default="USD", max_length=3)
    status: DealStatus = DealStatus.NEW
    stage: DealStage = DealStage.QUALIFICATION


class DealUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    contact_id: int | None = None
    amount: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=3)
    status: DealStatus | None = None
    stage: DealStage | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount_for_won(cls, v: Decimal | None, info: ValidationInfo) -> Decimal | None:
        # This will be further validated in the service layer with status check
        return v


class DealStageUpdate(BaseModel):
    stage: DealStage


class DealStatusUpdate(BaseModel):
    status: DealStatus


class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    contact_id: int | None
    owner_id: int
    title: str
    amount: Decimal
    currency: str
    status: DealStatus
    stage: DealStage
    created_at: datetime
    updated_at: datetime
