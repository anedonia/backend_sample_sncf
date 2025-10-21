from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from opticapa.features.axe_ef.schemas import (
    PaginationAxeEf,
    AxeEfGet,
    AxeEfCreateUpdate,
)
from opticapa.features.axe_ef.service import AxeEfService
from opticapa.shared.common.api_helpers import (
    CreatedResponse,
    DeletedResponse,
    UpdatedResponse,
    PaginationParams,
)
from opticapa.shared.database.manage_db import get_sync_session, get_async_session

axe_ef_router = APIRouter(prefix="/axe_ef", tags=["axe_ef"])


@axe_ef_router.get("/all/", response_model=PaginationAxeEf)
def get_all_paginated_axes_ef(
    session: Session = Depends(get_sync_session),
):
    axes_ef, count = AxeEfService.get_all_axes_ef(
        session=session
    )
    return PaginationAxeEf(items=axes_ef, count=count)


@axe_ef_router.get("/{axe_ef_id}", response_model=AxeEfGet)
def get_axe_ef_by_id(axe_ef_id: str, session: Session = Depends(get_sync_session)):
    return AxeEfService.get_axe_ef(axe_ef_id=axe_ef_id, session=session)


@axe_ef_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreatedResponse
)
async def create_axe_ef(
    request: AxeEfCreateUpdate,
    session: Session = Depends(get_sync_session),
):
    return AxeEfService.create_axe_ef(
        request=request, session=session
    )


@axe_ef_router.put(
    "/{axe_ef_id}",
    response_model=UpdatedResponse,
    status_code=status.HTTP_200_OK,
)
async def update_axe_ef(
    axe_ef_id: str,
    request: AxeEfCreateUpdate,
    session: Session = Depends(get_sync_session),
):
    return AxeEfService.update_axe_ef(
        axe_ef_id=axe_ef_id,
        request=request,
        session=session,
    )


@axe_ef_router.delete(
    "/{axe_ef_id}",
    response_model=DeletedResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_axe_ef(
    axe_ef_id: str,
    session: Session = Depends(get_sync_session),
):
    return AxeEfService.delete_axe_ef(axe_ef_id=axe_ef_id, session=session)


@axe_ef_router.post("/renew/{axe_ef_id}", response_model=CreatedResponse)
async def renew_axe_ef(
    axe_ef_id: str,
    service_annuel_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    return await AxeEfService.renew_axe_ef(
        axe_ef_id=axe_ef_id,
        service_annuel_id=service_annuel_id,
        session=session,
    )
