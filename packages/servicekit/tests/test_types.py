from ulid import ULID

from servicekit import ULIDType


def test_ulid_type_process_bind_param_with_ulid() -> None:
    """process_bind_param should convert ULID inputs to strings."""
    value = ULID()
    ulid_type = ULIDType()
    assert ulid_type.process_bind_param(value, None) == str(value)


def test_ulid_type_process_bind_param_with_string() -> None:
    """process_bind_param should validate and normalize string inputs."""
    value = str(ULID())
    ulid_type = ULIDType()
    assert ulid_type.process_bind_param(value, None) == value


def test_ulid_type_process_result_value() -> None:
    """process_result_value should convert strings back to ULID."""
    value = str(ULID())
    ulid_type = ULIDType()
    assert ulid_type.process_result_value(value, None) == ULID.from_str(value)
    assert ulid_type.process_result_value(None, None) is None
