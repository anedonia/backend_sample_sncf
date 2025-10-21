import uuid
from typing import Union, Optional, Type, Any, Callable

import sqlalchemy as sqla
from fastapi import HTTPException
from opticapa_models import (
    Alternat,
    Fenetre,
    GroupementVoies,
    RegleAlternat,
    PeriodeExclusion,
    ServiceAnnuel,
)
from opticapa_models.infrastructure.models.axe_ef import AxeEf
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import insert, Insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette import status

from opticapa.shared.common.enums import CrudOperation
from opticapa.shared.database.base import Base
from opticapa.shared.utils.logger import logger
from psycopg2 import errors
from opticapa.shared.common.service.crud.crud_verify_existence import (
    verify_existence_and_get,
)


class OrmCrudSyncService:
    @classmethod
    def create_procedure(
        cls,
        db_object: Union[
            Fenetre,
            PeriodeExclusion,
            Alternat,
            AxeEf,
            GroupementVoies,
            RegleAlternat,
            ServiceAnnuel,
        ],
        session: Session,
    ):
        """
        This function executes an ORM add procedure for a create operation of a CRUD service.
        During this procedure, we first flush before committing in order to launch ORM events and access to trigger logs.
        Args:
            db_object: object to insert in db which must be loaded beforehand.
            session: database session
        """
        session.add(db_object)
        cls._commit_and_log_session(
            session=session, db_object=db_object, crud_operation=CrudOperation.create
        )

    @classmethod
    def update_procedure(
        cls,
        db_object: Union[
            Fenetre, PeriodeExclusion, Alternat, AxeEf, GroupementVoies, RegleAlternat
        ],
        obj_to_update: Union[
            Fenetre, PeriodeExclusion, Alternat, AxeEf, GroupementVoies, RegleAlternat
        ],
        session: Session,
    ):
        """
        This function executes an ORM procedure merge for an update operation of a CRUD service.
        During this procedure, we first flush before committing in order to launch ORM events and access to trigger logs.
        Args:
            db_object: object to merge in db which must be loaded beforehand.
            session: database session
            obj_to_update: capacity object to update. Mandatory if ORM operation is an update
        """
        if isinstance(obj_to_update, (Fenetre, PeriodeExclusion)):
            obj_to_update.ressources_espace_temps.clear()
        elif isinstance(obj_to_update, (Alternat, GroupementVoies)):
            obj_to_update.lvpks.clear()
        elif isinstance(obj_to_update, AxeEf):
            obj_to_update.sections.clear()
        session.flush()
        db_object = session.merge(db_object)
        cls._commit_and_log_session(
            session=session, db_object=db_object, crud_operation=CrudOperation.update
        )

    @classmethod
    def delete_procedure(
        cls,
        db_object: Union[
            Fenetre,
            PeriodeExclusion,
            Alternat,
            AxeEf,
            GroupementVoies,
            RegleAlternat,
        ],
        session: Session,
    ):
        """
        This function executes an ORM procedure delete for a delete operation of CRUD service.
        During this procedure, we first flush before committing in order to launch ORM events and access to trigger logs.
        Args:
            db_object: object to delete in db which must be loaded beforehand.
            session: database session
        """
        session.delete(db_object)
        cls._commit_and_log_session(
            session=session, db_object=db_object, crud_operation=CrudOperation.delete
        )

    @classmethod
    def upsert_procedure(
        cls,
        session: Session,
        main_model: Type[Base],
        object_to_insert: Union[dict[str, Any], list[dict[str, Any]]],
        sub_object_models: dict[str, Type[Base]],
        sub_obj_parent_columns: Optional[dict[str, Column]] = None,
        id_column: str = "id",
        do_update: bool = False,
        execute_after_insert: Optional[Callable] = None,
        execute_after_delete: Optional[Callable] = None,
    ):
        """
        Inserts in database object_to_insert and their sub objects.
        If do_update is True, this method delete all previous sub objects, and update object_to_insert.

        Args:
            session: db session
            main_model: table in which to insert object_to_insert (main object to insert)
            object_to_insert: dict mapping column names with values to insert in db
            sub_object_models: dict mapping the key of the sub_objects in object_to_insert with the table in which to
            insert the sub_objects
            sub_obj_parent_columns: dict mapping the key of the sub_objects in object_to_insert with the column to
             retrieve the id of object_to_insert in table sub_model
            id_column: name of the primary key column in table main_model
            do_update: if True, on_conflict_do_update is added to insert statement.
            execute_after_insert: async function to execute after inserting sub-objects
            execute_after_delete: async function to execute after deleting sub-objects (when do_update is True)
        """
        if do_update:
            crud_operation = CrudOperation.update
            updated_ids = [object_to_insert.get(id_column, "")]
            for key, sub_model in sub_object_models.items():
                cls.delete_object(
                    object_ids=updated_ids,
                    model_to_delete=sub_model,
                    model_to_retrieve=main_model,
                    db=session,
                    model_column_id=sub_obj_parent_columns.get(key, None)
                    if sub_obj_parent_columns
                    else None,
                )
                if execute_after_insert:
                    execute_after_delete(
                        session=session,
                        updated_pe_ids=tuple(updated_ids),
                    )
        else:
            crud_operation = CrudOperation.create

        ids = cls.multiple_insert_procedure(
            session=session,
            main_model=main_model,
            object_to_insert=object_to_insert,
            sub_object_models=sub_object_models,
            id_column=id_column,
            do_update=do_update,
        )

        if execute_after_insert:
            execute_after_insert(session=session)

        session.commit()
        logger.debug(
            f"{crud_operation.value} {main_model.__tablename__} with id(s) {ids}"
        )

    @classmethod
    def multiple_insert_procedure(
        cls,
        session: Session,
        main_model: Type[Base],
        object_to_insert: dict[str, Any],
        sub_object_models: dict[str, Type[Base]],
        id_column: str = "id",
        do_update: bool = False,
    ) -> str:
        """

        Args:
            session: db session
            main_model: table in which to insert object_to_insert (main object to insert)
            object_to_insert: dict mapping column names with values to insert in db
            sub_object_models: dict mapping the key of the sub_objects in object_to_insert with the table in which to
            insert the sub_objects
            id_column: name of the primary key column in table main_model
            do_update: if True, on_conflict_do_update is added to insert statement.

        Returns:
            inserted ids

        """
        if isinstance(object_to_insert, list):
            ids = ""
            for obj in object_to_insert:
                cls.insert_procedure(
                    session=session,
                    main_model=main_model,
                    object_to_insert=obj,
                    sub_object_models=sub_object_models,
                    id_column=id_column,
                    do_update=do_update,
                )
                ids = f"{ids} {obj.get(id_column, '')} ,"
        else:
            ids = object_to_insert.get(id_column, "")
            cls.insert_procedure(
                session=session,
                main_model=main_model,
                object_to_insert=object_to_insert,
                sub_object_models=sub_object_models,
                id_column=id_column,
                do_update=do_update,
            )
        return ids

    @classmethod
    def insert_procedure(
        cls,
        session: Session,
        main_model: Type[Base],
        object_to_insert: dict[str, Any],
        sub_object_models: dict[str, Type[Base]],
        id_column: str = "id",
        do_update: bool = False,
    ):
        """
        Computes and execute insert statements, to insert the object object_to_insert and all of its sub_objects
        (defined in object_to_insert["sub_object_key"]).
        Only one insert statement is created for all sub objects.
        If object_to_insert has the same libelle as another object in db, then an exception is raised.

        Args:
            session: db session
            main_model: table in which to insert object_to_insert (main object to insert)
            object_to_insert: dict mapping column names with values to insert in db
            sub_object_models: dict mapping the key of the sub_objects in object_to_insert with the table in which to
            insert the sub_objects
            id_column: name of the primary key column in table main_model
            do_update: if True, on_conflict_do_update is added to insert statement.

        """
        sub_objects = [
            (model, objs)
            for key, model in sub_object_models.items()
            if (objs := object_to_insert.pop(key, None)) is not None
        ]
        upsert_stmt = insert(main_model).values(object_to_insert)
        if do_update:
            update_columns = {
                key: upsert_stmt.excluded[key]
                for key in object_to_insert
                if key
                not in (
                    id_column,
                    "created_at",
                    "created_by",
                )
            }
            upsert_stmt = upsert_stmt.on_conflict_do_update(
                index_elements=[id_column], set_=update_columns
            )

        cls.execute_stmt(
            stmt=upsert_stmt,
            session=session,
            main_model=main_model,
        )
        for model, objs in sub_objects:
            if objs:
                session.execute(insert(model).values(objs))
            else:
                logger.debug(
                    f"Sub-object {model.__tablename__} is empty, skipping insert."
                )

    @staticmethod
    def execute_stmt(
        session: Session,
        stmt: Insert,
        main_model: Type[Base],
    ):
        """
        This method execute an insert statement and catch integrity error.

        Args:
            session: DB session,
            stmt: insert statement to execute
            main_model: table in which to insert object_to_insert (main object to insert)

        """
        try:
            session.execute(stmt)
        except IntegrityError as e:
            orig = e.orig
            logger.error(str(e))
            if isinstance(orig, errors.UniqueViolation):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Object {main_model.__tablename__} with label "
                        f"{e.params.get('libelle', '')} already exists."
                        "Please try again with another label."
                    ),
                )
            elif isinstance(orig, errors.NotNullViolation):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database integrity error: {str(e)}",
                ) from e

    @classmethod
    def delete_object(
        cls,
        object_ids: list[Union[int, str, uuid.UUID]],
        model_to_delete: Base,
        model_to_retrieve: Base,
        db: AsyncSession,
        model_column_id: Optional[Column] = None,
    ):
        """
        Deletes objects from the database by their IDs after verifying their existence.

        This method determines the appropriate ID column based on the model,
        verifies that the objects exist, and performs a bulk delete operation
        using the provided session.

        Args:
            object_ids: List of object IDs to delete.
            model_to_delete: The SQLAlchemy model class of the objects to delete.
            model_to_retrieve: The model used to verify object existence (often the same as model_to_delete).
            model_column_id: the column of the pkey or fkey where to find the object ids
            db: The database session (AsyncSession) used to execute the deletion.
        """
        verify_existence_and_get(object_ids, model=model_to_retrieve, db=db)
        if not model_column_id:
            model_column_id = model_to_delete.id
        stmt = (
            sqla.delete(model_to_delete)
            .where(model_column_id.in_(object_ids))
            .execution_options(synchronize_session="fetch")
        )
        db.execute(stmt)

    @staticmethod
    def _commit_and_log_session(
        session: Session,
        db_object: Union[
            Fenetre,
            PeriodeExclusion,
            Alternat,
            GroupementVoies,
            RegleAlternat,
            ServiceAnnuel,
        ],
        crud_operation: CrudOperation,
    ):
        """
        This method commits an ORM session after a CRUD operation is performed. If done well, the ressource to commit is
        refreshed and a log is sent when the operation performed correctly.
        Args:
            session: DB session
            db_object: Capacity object to be committed
            crud_operation: CRUD operation performed. Either create, update, or delete
        """
        try:
            session.flush()
            session.commit()
        except IntegrityError as e:
            orig = e.orig
            logger.error(str(e))
            if isinstance(orig, errors.UniqueViolation):
                duplicated_label = e.params.get("libelle", "")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Object {db_object.__tablename__} with label {duplicated_label} already exists."
                    f"Please try again with another label.",
                )
            elif isinstance(orig, errors.NotNullViolation):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database integrity error: {str(e)}",
                ) from e
        logger.debug(
            f"{crud_operation.value} {db_object.__tablename__} with id {db_object.id}"
        )
