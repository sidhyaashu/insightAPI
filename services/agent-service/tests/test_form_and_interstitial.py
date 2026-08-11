import pytest
from app.engine.executor.dynamic_executor import FormDummyInjector, COMMON_OVERLAY_SELECTORS


def test_form_dummy_injector_search():
    meta = {"name": "search_query", "placeholder": "Search catalog...", "type": "text"}
    val = FormDummyInjector.get_dummy_value(meta)
    assert val == "test search"


def test_form_dummy_injector_email():
    meta = {"name": "user_email", "placeholder": "Enter your email", "type": "email"}
    val = FormDummyInjector.get_dummy_value(meta)
    assert val == "user@example.com"


def test_form_dummy_injector_date():
    meta = {"name": "start_date", "type": "date"}
    val = FormDummyInjector.get_dummy_value(meta)
    assert val == "2026-01-01"


def test_form_dummy_injector_number():
    meta = {"name": "quantity", "type": "number"}
    val = FormDummyInjector.get_dummy_value(meta)
    assert val == "10"


def test_form_dummy_injector_fallback():
    meta = {"name": "custom_field_xyz", "type": "text"}
    val = FormDummyInjector.get_dummy_value(meta)
    assert val == "sample input"


def test_common_overlay_selectors_list():
    assert len(COMMON_OVERLAY_SELECTORS) > 0
    assert any("Accept" in sel for sel in COMMON_OVERLAY_SELECTORS)
    assert any("Close" in sel for sel in COMMON_OVERLAY_SELECTORS)
