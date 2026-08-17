"""Anti-Bot Stealth & Evasion Layer for Playwright Headless Automation."""
from __future__ import annotations

import random
import asyncio
from typing import Any, Dict

STEALTH_JS_INJECTION = """
(() => {
    // 1. Strip navigator.webdriver flag
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    // 2. Mock realistic navigator languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });

    // 3. Mock navigator plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ],
    });

    // 4. Mock window.chrome runtime object
    if (!window.chrome) {
        window.chrome = {};
    }
    if (!window.chrome.runtime) {
        window.chrome.runtime = {
            OnInstalledReason: { CHROME_UPDATE: "chrome_update", INSTALL: "install", SHARED_MODULE_UPDATE: "shared_module_update", UPDATE: "update" },
            OnRestartRequiredReason: { APP_UPDATE: "app_update", OS_UPDATE: "os_update", PERIODIC: "periodic" },
            PlatformArch: { ARM: "arm", ARM64: "arm64", MIPS: "mips", MIPS64: "mips64", X86_32: "x86-32", X86_64: "x86-64" },
            PlatformNaclArch: { ARM: "arm", MIPS: "mips", MIPS64: "mips64", X86_32: "x86-32", X86_64: "x86-64" },
            PlatformOs: { ANDROID: "android", CROS: "cros", LINUX: "linux", MAC: "mac", OPENBSD: "openbsd", WIN: "win" },
            RequestUpdateCheckStatus: { NO_UPDATE: "no_update", THROTTLED: "throttled", UPDATE_AVAILABLE: "update_available" }
        };
    }

    // 5. Spoof WebGL Vendor & Renderer
    try {
        const getParameterProto = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                return 'Google Inc. (NVIDIA)';
            }
            if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
            }
            return getParameterProto.apply(this, arguments);
        };
    } catch (e) {}

    // 6. Fix permissions query for notifications
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
})();
"""


async def apply_stealth_evasion(context: Any) -> None:
    """Apply stealth evasion scripts and realistic user agents to a Playwright browser context."""
    await context.add_init_script(STEALTH_JS_INJECTION)


async def humanized_type(element: Any, text: str, min_delay_ms: int = 30, max_delay_ms: int = 100) -> None:
    """Simulate realistic human typing speed with character jitter."""
    for char in text:
        await element.type(char, delay=random.randint(min_delay_ms, max_delay_ms))
        if random.random() < 0.05:  # occasional thinking pause
            await asyncio.sleep(random.uniform(0.1, 0.3))


async def humanized_click(element: Any) -> None:
    """Simulate human hover before clicking."""
    try:
        await element.hover(timeout=1000)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await element.click(timeout=1500)
    except Exception:
        await element.click(timeout=1500)
