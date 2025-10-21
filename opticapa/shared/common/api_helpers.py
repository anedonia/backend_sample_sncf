import uuid
from typing import Optional
from opticapa.shared.common.base_model import BaseModel


class CreatedResponse(BaseModel):
    created: uuid.UUID | str
    main_zp_id: Optional[int] = None


class MultipleCreatedUpdatedResponse(BaseModel):
    created_updated: list[uuid.UUID]
    main_zp_id: Optional[int] = None


class UpdatedResponse(BaseModel):
    updated: uuid.UUID | int
    main_zp_id: Optional[int] = None


class DeletedResponse(BaseModel):
    deleted: uuid.UUID | str | int


class MultipleDeletedResponse(BaseModel):
    deleted: list[uuid.UUID]
