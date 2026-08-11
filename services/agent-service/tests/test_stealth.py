import pytest
from app.engine.browser.manager import STEALTH_JS


def test_stealth_js_webgl_masking():
    assert "hardwareConcurrency" in STEALTH_JS
    assert "deviceMemory" in STEALTH_JS
    assert "WebGLRenderingContext" in STEALTH_JS
    assert "Intel Inc." in STEALTH_JS
    assert "permissions.query" in STEALTH_JS
