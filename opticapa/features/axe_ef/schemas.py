from datetime import datetime
from typing import Optional

from opticapa_models.infrastructure.enums import NatureAxeEf

from opticapa.shared.common.base_model import BaseModel
from opticapa.shared.common.schemas.common import ObjectGetAll


class SectionAxeProto(BaseModel):
    onb_tcap: int
    libelle: str
    service_annuel_id: str

class AxeEfProto(BaseModel):
    nature: NatureAxeEf
    description: Optional[str] = None
    service_annuel_id: str


class AxeEfCreateUpdate(AxeEfProto, GetColoredSimpleObj):
    section_axe_onbs: list[int]


class AxeEfGet(AxeEfProto, GetIdentifiedSimpleObj):
    section_axes: list[SectionAxeProto]


class AxeEfGetAll(GetIdentifiedSimpleObj, ObjectGetAll):
    nature: NatureAxeEf
    updated_at: datetime


class PaginationAxeEf(BaseModel):
    items: list[AxeEfGetAll]
    count: int