from datetime import datetime
from typing import Any
from uuid import uuid4, UUID

from fastapi import HTTPException, status
from opticapa_models import (
    SectionAxe,
    ServiceAnnuel,
)
from opticapa_models.infrastructure.models.axe_ef import AxeEf
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session, selectinload
from opticapa_models.infrastructure.models.axe_ef import AxeEfSection
from opticapa_models.infrastructure.models.sections import LvpkSectionAxe

from opticapa.features.axe_ef.schemas import (
    AxeEfGet,
    AxeEfGetAll,
    AxeEfCreateUpdate,
    SectionAxeProto
)
from opticapa.shared.common import api_helpers
from opticapa.shared.common.service.crud import OrmCrudSyncService
from opticapa.shared.common.service import verify_existence_and_get


class AxeEfService:
    @staticmethod
    def get_axe_ef(axe_ef_id: str, session: Session) -> AxeEfGet:
        """
        Gets from database the axe EF with given id

        Args:
            axe_ef_id: id of the axe EF to retrieve
            session: db session

        Returns:
            an AxeEf object corresponding to the retrieved axe EF

        """
        axe_ef: AxeEf = verify_existence_and_get(
            object_id=axe_ef_id,
            model=AxeEf,
            db=session,
            load_options=[selectinload(AxeEf.sections)],
        )
        section_axes = [SectionAxeProto(**sec.__dict__) for sec in axe_ef.sections]
        res = AxeEfGet(
            id=axe_ef.id,
            libelle=axe_ef.libelle,
            description=axe_ef.description,
            nature=axe_ef.nature,
            color=axe_ef.color,
            service_annuel_id=axe_ef.service_annuel_id,
            section_axes=section_axes,
        )
        return res

    @classmethod
    def get_all_axes_ef(
        cls,
        session: Session
    ) -> tuple[list[AxeEfGetAll], int]:
        """
        Gets all axes EF from database, and sorts them by sort_category according to the given sort order.
        If search_string is not None, axes EF are filtered by matching libelle.
        If pagination_params is not None, the result of query is limited.

        Args:
            session: db session
            service_annuel_id: id of service annuel filtering axes EF
            search_string: string filtering axes EF by libelle
            sort_category: Column to be sorted with
            sort: Sort the results in ascending or descending order
            pagination_params: contains the limit and offset for the sql query

        Returns:
            a tuple with :
            - the list of axes EF limited by pagination_params, formatted into AxeEfGetAll
            - the total number of axes EF

        """
        get_all_query = (
            select(
                AxeEf.id,
                AxeEf.libelle,
                AxeEf.color,
                AxeEf.nature,
                AxeEf.description,
                case(
                    (AxeEf.modified_at.is_not(None), AxeEf.modified_at),
                    else_=AxeEf.created_at,
                ).label("updated_at"),
                func.json_agg(
                    func.json_build_object(
                        "ligne",
                        LvpkSectionAxe.ligne,
                        "voie",
                        LvpkSectionAxe.voie,
                        "pk_debut",
                        LvpkSectionAxe.pk_debut,
                        "pk_fin",
                        LvpkSectionAxe.pk_fin,
                    )
                ).label("lvpks"),
            )
            .join(AxeEfSection, AxeEfSection.axe_ef_id == AxeEf.id)
            .join(
                LvpkSectionAxe,
                LvpkSectionAxe.section_axe_onb == AxeEfSection.section_axe_onb,
            )
            .group_by(
                AxeEf.id,
                AxeEf.libelle,
                AxeEf.color,
                AxeEf.nature,
                AxeEf.created_at,
                AxeEf.modified_at,
            )
            .order_by(AxeEf.libelle)
        )

        count_query = select(func.count(AxeEf.id))
        axes_ef = session.execute(get_all_query).mappings().all()

        count = session.execute(count_query).scalars().first()
        formatted_axes_ef = [
            AxeEfGetAll.model_validate(axe_ef)
            for axe_ef in axes_ef
        ]
        return formatted_axes_ef, count

    @staticmethod
    def _validate_sections(sections_axes: list[SectionAxe], service_annuel_id: str):
        if not sections_axes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No TCAP sections axes were specified.\n"
                f"Please select at least one valid section on the specified SA {service_annuel_id}",
            )
        unvalid_sections = [
            section_axe.libelle
            for section_axe in sections_axes
            if section_axe.service_annuel_id != service_annuel_id
        ]
        if unvalid_sections:
            libelles = ", ".join(unvalid_sections)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"TCAP sections axes {libelles} aren't valid on the specified SA {service_annuel_id}.\n"
                f"Please select valid sections on this SA",
            )

    @classmethod
    def _make_axe_ef(
        cls,
        axe_ef: AxeEfCreateUpdate,
        user_id: int,
        is_new: bool,
        session: Session,
    ) -> dict[str, Any]:
        """
        Creates axe EF.
        Args:
            axe_ef: parameters of the axe EF to add
            session: DB session

        Returns:
            An axe EF that can be added to DB
        """

        # Checks axe EF definition and existence of related objects
        verify_existence_and_get(
            object_id=axe_ef.service_annuel_id,
            model=ServiceAnnuel,
            db=session,
            return_model=False,
        )

        # Fills axe EF with sections
        axe_ef_dict = axe_ef.__dict__
        sections_onbs = axe_ef_dict.pop("section_axe_onbs", [])
        sections_axes = verify_existence_and_get(
            object_id=sections_onbs,
            model=SectionAxe,
            db=session,
            model_column_id=SectionAxe.onb_tcap,
            return_model=True,
        )
        cls._validate_sections(
            sections_axes=sections_axes, service_annuel_id=axe_ef.service_annuel_id
        )
        axe_ef_dict["sections"] = sections_axes

        # Fills dates
        if is_new:
            axe_ef_dict["created_at"] = datetime.now()
            axe_ef_dict["created_by"] = user_id
        else:
            axe_ef_dict["modified_at"] = datetime.now()
            axe_ef_dict["modified_by"] = user_id

        return axe_ef_dict

    @classmethod
    def create_axe_ef(
        cls,
        request: AxeEfCreateUpdate,
        user_id: int,
        session: Session,
    ) -> api_helpers.CreatedResponse:
        """
        Adds to db an instance of axe EF
        Args:
            request: parameters of the axe EF to add
            user_id: id of the user who's adding the resource
            session: db Session

        Returns:
            API response making sure the resource has been added
        """
        axe_ef_id = uuid4()
        axe_ef = AxeEf(
            id=axe_ef_id,
            **cls._make_axe_ef(
                axe_ef=request, user_id=user_id, is_new=True, session=session
            ),
        )
        OrmCrudSyncService.create_procedure(db_object=axe_ef, session=session)
        return api_helpers.CreatedResponse(created=axe_ef.id)

    @classmethod
    def update_axe_ef(
        cls,
        axe_ef_id: str,
        request: AxeEfCreateUpdate,
        user_id: int,
        session: Session,
    ) -> api_helpers.UpdatedResponse:
        """
        Updates an instance of axe EF from db

        Args:
            axe_ef_id: id of the axe EF to update
            request: parameters of the axe EF to add
            user_id: id of the user who's adding the resource
            session: db Session

        Returns:
            API response making sure the resource has been updated
        """
        axe_ef_to_update = verify_existence_and_get(
            object_id=axe_ef_id, model=AxeEf, db=session
        )
        axe_ef = AxeEf(
            id=axe_ef_id,
            **cls._make_axe_ef(
                axe_ef=request, user_id=user_id, is_new=False, session=session
            ),
        )
        OrmCrudSyncService.update_procedure(
            obj_to_update=axe_ef_to_update,
            db_object=axe_ef,
            session=session,
        )
        return api_helpers.UpdatedResponse(updated=axe_ef.id)

    @classmethod
    def delete_axe_ef(cls, axe_ef_id: str | UUID, session: Session):
        """
        Deletes an instance of axe EF from db
        Args:
            axe_ef_id: id of the axe EF to delete
            session: db Session

        Returns:
            API response making sure the resource has been deleted
        """
        axe_ef: AxeEf = verify_existence_and_get(
            object_id=axe_ef_id, model=AxeEf, db=session, return_model=True
        )
        OrmCrudSyncService.delete_procedure(db_object=axe_ef, session=session)
        return api_helpers.DeletedResponse(deleted=axe_ef_id)
