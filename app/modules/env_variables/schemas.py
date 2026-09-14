from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import ORMModel


class EnvVariableItem(BaseModel):
    key: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    value: str


class VariablesMustBeUnique(BaseModel):
    @field_validator("variables", check_fields=False)
    @classmethod
    def validate_unique_keys(
        cls, variables: list[EnvVariableItem] | None
    ) -> list[EnvVariableItem] | None:
        if variables is None:
            return variables
        keys = [variable.key for variable in variables]
        if len(keys) != len(set(keys)):
            raise ValueError("environment variable keys must be unique within a group")
        return variables


class EnvVariableCreate(VariablesMustBeUnique):
    folder_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    variables: list[EnvVariableItem] = Field(min_length=1)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, name: str) -> str:
        if not (name := name.strip()):
            raise ValueError("name must not be blank")
        return name


class EnvVariableUpdate(VariablesMustBeUnique):
    folder_id: UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    variables: list[EnvVariableItem] | None = Field(None, min_length=1)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, name: str | None) -> str | None:
        if name is not None and not (name := name.strip()):
            raise ValueError("name must not be blank")
        return name

    @model_validator(mode="after")
    def reject_null_variables(self) -> "EnvVariableUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name must not be null")
        if "variables" in self.model_fields_set and self.variables is None:
            raise ValueError("variables must be a non-empty list")
        return self


class EnvVariableItemResponse(BaseModel):
    key: str
    value: str = "********"


class EnvVariableResponse(ORMModel):
    id: UUID
    folder_id: UUID
    name: str
    variables: list[EnvVariableItemResponse]
    description: str | None
    created_at: datetime
    updated_at: datetime


class EnvVariableReveal(BaseModel):
    id: UUID
    folder_id: UUID
    name: str
    variables: list[EnvVariableItem]
    description: str | None
