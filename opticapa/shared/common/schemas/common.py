from typing import Optional
from opticapa.shared.common.schemas.lvpk import Lvpk


class ObjectGetAll:
    description: Optional[str] = None
    lvpks: list[Lvpk]
