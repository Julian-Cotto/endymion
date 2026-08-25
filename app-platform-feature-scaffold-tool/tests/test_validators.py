import pytest

from feature_scaffold.models import EventContract, EventsConfig, ScaffoldConfig
from feature_scaffold.validators import ValidationError, validate_config

def test_validate_accepts_basic_feature() -> None:
    validate_config(ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders"))

def test_validate_rejects_bad_base_path() -> None:
    with pytest.raises(ValidationError):
        validate_config(ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="orders"))

def test_validate_rejects_bad_event_name() -> None:
    with pytest.raises(ValidationError):
        validate_config(ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders", events=EventsConfig(publishes=[EventContract(name="OrdersCreated", schema="OrderCreated")])))
