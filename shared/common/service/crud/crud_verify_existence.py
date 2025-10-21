import uuid
from typing import Union, Optional, Type

import sqlalchemy as sqla
from fastapi import HTTPException
from sqlalchemy import Column, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, strategy_options
from starlette import status

from opticapa.shared.database.base import Base


def _verify_existence_and_get_stmt(
    object_id: Union[int, str, uuid.UUID, list[int], list[str], list[uuid.UUID]],
    model: Base,
    model_column_id: Optional[Column] = None,
    returned_column: Optional[Column] = None,
    load_options: Optional[list[strategy_options.Load]] = None,
) -> (Select, bool):
    """
    this function is used to verifier if the list of object ids exsist or not and get the result of query
    Args:
        object_id: list of str or uuid
        model: database model
        model_column_id: if one wants to us a different key than id, one has to use this param
        load_options:
        returned_column: Column to return. If None, module returns the whole model

    Returns: the result of query

    """
    if not model_column_id:
        model_column_id = model.id
    stmt = sqla.select(returned_column) if returned_column else sqla.select(model)
    if load_options:
        stmt = stmt.options(*load_options)
    if (
        isinstance(object_id, int)
        or isinstance(object_id, str)
        or isinstance(object_id, uuid.UUID)
    ):
        return stmt.where(model_column_id == object_id), False
    return stmt.where(model_column_id.in_(object_id)), True


def verify_existence_and_get(
    object_id: Union[int, str, uuid.UUID, list[int], list[str], list[uuid.UUID]],
    model: Type[Base],
    db: Session,
    model_column_id: Optional[Column] = None,
    returned_column: Optional[Column] = None,
    load_options: Optional[list[strategy_options.Load]] = None,
    return_model: bool = True,
) -> Optional[Union[Base, dict, list[Base], list[dict]]]:
    """
    this function is used to verifier if the list of object ids exsist or not and get the result of query
    Args:
        object_id: list of str or uuid
        model: database model
        model_column_id: if one wants to us a different key than id, one has to use this param
        db: database
        load_options:
        return_model: bool set to True if we want the function to return the requested result
        returned_column: Column to return. If None, module returns the whole model

    Returns: the result of query

    """
    stmt, multiple_result = _verify_existence_and_get_stmt(
        object_id=object_id,
        model=model,
        model_column_id=model_column_id,
        returned_column=returned_column,
        load_options=load_options,
    )
    result = (
        db.execute(stmt).scalars().all()
        if multiple_result
        else db.execute(stmt).scalars().first()
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__tablename__} with id {object_id} does not exists",
        )
    return result if return_model else None


async def async_verify_existence_and_get(
    object_id: Union[int, str, uuid.UUID, list[int], list[str], list[uuid.UUID]],
    model: Type[Base],
    db: AsyncSession,
    model_column_id: Optional[Column] = None,
    returned_column: Optional[Column] = None,
    load_options: Optional[
        list[Union[strategy_options.Load, strategy_options._AbstractLoad]]
    ] = None,
    return_model: bool = True,
    ignore_not_found: bool = False,
) -> Optional[Union[Base, dict, list[Base], list[dict]]]:
    """
    this function is used to verifier if the list of object ids exsist or not and get the result of query
    Args:
        object_id: list of str or uuid
        model: database model
        model_column_id: if one wants to us a different key than id, one has to use this param
        db: database
        load_options:
        return_model: bool set to True if we want the function to return the requested result
        returned_column: Column to return. If None, module returns the whole model
        ignore_not_found: bool set to True if we want the function to ignore not found (NONE)

    Returns: the result of query

    """
    stmt, multiple_result = _verify_existence_and_get_stmt(
        object_id=object_id,
        model=model,
        model_column_id=model_column_id,
        returned_column=returned_column,
        load_options=load_options,
    )
    result = await db.execute(stmt)
    result = result.scalars().all() if multiple_result else result.scalars().first()
    if not ignore_not_found and not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__tablename__} with id {object_id} does not exist",
        )
    return result if return_model else None
