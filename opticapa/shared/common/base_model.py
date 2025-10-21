from pydantic import ConfigDict, BaseModel as PydanticBaseModel


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
        validate_assignment=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
