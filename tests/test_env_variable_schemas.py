import pytest
from pydantic import ValidationError

from app.modules.env_variables.schemas import EnvVariableCreate, EnvVariableUpdate


def test_create_group_accepts_multiple_variables_and_strips_name() -> None:
    body = EnvVariableCreate(
        name="  Production  ",
        variables=[
            {"key": "DATABASE_URL", "value": "postgresql://production"},
            {"key": "REDIS_URL", "value": "redis://production"},
        ],
    )

    assert body.name == "Production"
    assert [variable.key for variable in body.variables] == ["DATABASE_URL", "REDIS_URL"]


def test_group_rejects_duplicate_keys() -> None:
    with pytest.raises(ValidationError, match="keys must be unique"):
        EnvVariableCreate(
            name="Production",
            variables=[
                {"key": "DATABASE_URL", "value": "first"},
                {"key": "DATABASE_URL", "value": "second"},
            ],
        )


@pytest.mark.parametrize("variables", [[], None])
def test_update_rejects_empty_or_null_variable_replacement(variables: object) -> None:
    with pytest.raises(ValidationError):
        EnvVariableUpdate(variables=variables)


def test_update_can_omit_variables() -> None:
    body = EnvVariableUpdate(description="New description")

    assert "variables" not in body.model_fields_set
