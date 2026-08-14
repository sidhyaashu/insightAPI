"""
Humanized Playwright Interaction Engine.
Replaces robotic, instant linear clicks/keystrokes with human-like Bezier-curve mouse paths,
randomized micro-pauses, hold durations, and natural inter-keystroke cadence.
"""
import asyncio
import logging
import math
import random
from typing import Dict, Any, List, Optional, Tuple, Union
from playwright.async_api import Page

logger = logging.getLogger("engine.humanizer")


class Humanizer:
    """
    Simulates authentic human motor patterns for browser interactions to reduce
    bot-detection fingerprinting (Cloudflare Turnstile, Datadome, Akamai, PerimeterX).
    """

    @staticmethod
    def compute_bezier_points(
        start: Tuple[float, float],
        end: Tuple[float, float],
        num_points: int = 12,
    ) -> List[Tuple[float, float]]:
        """
        Generates a cubic Bezier curve between start and end coordinates
        with randomized arc curvature simulating human hand movement.
        """
        x0, y0 = start
        x3, y3 = end
        dx = x3 - x0
        dy = y3 - y0
        dist = math.hypot(dx, dy)

        if dist < 5.0 or num_points <= 1:
            return [start, end]

        # Generate control points perpendicular to the direct vector with randomized curvature
        perp_x = -dy / dist
        perp_y = dx / dist

        offset1 = (random.random() - 0.5) * dist * 0.4
        offset2 = (random.random() - 0.5) * dist * 0.4

        x1 = x0 + dx * 0.33 + perp_x * offset1
        y1 = y0 + dy * 0.33 + perp_y * offset1

        x2 = x0 + dx * 0.66 + perp_x * offset2
        y2 = y0 + dy * 0.66 + perp_y * offset2

        points: List[Tuple[float, float]] = []
        for i in range(num_points + 1):
            t = i / float(num_points)
            # Cubic Bezier formula: (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
            xt = (
                ((1 - t) ** 3) * x0
                + 3 * ((1 - t) ** 2) * t * x1
                + 3 * (1 - t) * (t ** 2) * x2
                + (t ** 3) * x3
            )
            yt = (
                ((1 - t) ** 3) * y0
                + 3 * ((1 - t) ** 2) * t * y1
                + 3 * (1 - t) * (t ** 2) * y2
                + (t ** 3) * y3
            )
            points.append((xt, yt))

        return points

    @classmethod
    async def humanized_move(
        cls,
        page: Page,
        target: Union[str, Dict[str, Any], Tuple[float, float]],
        num_steps: Optional[int] = None,
    ) -> Tuple[float, float]:
        """
        Moves the mouse smoothly along a Bezier path from the last known mouse position
        to the target element or coordinate.
        """
        raw_pos = getattr(page, "_last_mouse_pos", None)
        if isinstance(raw_pos, (tuple, list)) and len(raw_pos) == 2 and isinstance(raw_pos[0], (int, float)):
            start_pos: Tuple[float, float] = (float(raw_pos[0]), float(raw_pos[1]))
        else:
            start_pos = (150.0, 150.0)

        target_x: float = 150.0
        target_y: float = 150.0

        if isinstance(target, str):
            try:
                locator = page.locator(target).first
                box = await locator.bounding_box()
                if box:
                    # Pick an interior point slightly jittered from center
                    jitter_x = box["width"] * random.uniform(0.3, 0.7)
                    jitter_y = box["height"] * random.uniform(0.3, 0.7)
                    target_x = box["x"] + jitter_x
                    target_y = box["y"] + jitter_y
                else:
                    target_x, target_y = start_pos
            except Exception as e:
                logger.debug(f"Could not get bounding box for selector '{target}': {e}")
                target_x, target_y = start_pos
        elif isinstance(target, dict):
            coords = target.get("coordinates") or target
            target_x = float(coords.get("x", 150.0)) + random.uniform(-3, 3)
            target_y = float(coords.get("y", 150.0)) + random.uniform(-3, 3)
        elif isinstance(target, (tuple, list)):
            target_x = float(target[0])
            target_y = float(target[1])

        steps = num_steps or random.randint(8, 18)
        trajectory = cls.compute_bezier_points(start_pos, (target_x, target_y), num_points=steps)

        for px, py in trajectory:
            try:
                await page.mouse.move(round(px, 1), round(py, 1))
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.005, 0.015))

        setattr(page, "_last_mouse_pos", (target_x, target_y))
        return (target_x, target_y)

    @classmethod
    async def humanized_click(
        cls,
        page: Page,
        target: Union[str, Dict[str, Any], Tuple[float, float]],
        timeout_ms: int = 10000,
    ) -> bool:
        """
        Executes a human-like mouse click: smooth movement, pre-click pause,
        mouse down, hold duration, mouse up, and post-click hesitation.
        """
        # 1. Smoothly glide cursor to target
        tx, ty = await cls.humanized_move(page, target)

        # 2. Pre-click hesitation (50-150ms)
        await asyncio.sleep(random.uniform(0.050, 0.150))

        # 3. Mouse down
        try:
            await page.mouse.down()
        except Exception:
            pass

        # 4. Randomized hold duration (30-90ms)
        await asyncio.sleep(random.uniform(0.030, 0.090))

        # 5. Mouse up
        try:
            await page.mouse.up()
        except Exception:
            pass

        # 6. Post-click micro-pause (20-60ms)
        await asyncio.sleep(random.uniform(0.020, 0.060))
        return True

    @classmethod
    async def humanized_type(
        cls,
        page: Page,
        selector: str,
        text: str,
        timeout_ms: int = 10000,
    ) -> bool:
        """
        Types text character-by-character with natural typing variance,
        word-boundary pauses, and simulated cognitive hesitation.
        """
        # Click into target input first
        await cls.humanized_click(page, selector, timeout_ms=timeout_ms)

        # Clear existing text if necessary
        try:
            await page.fill(selector, "")
        except Exception:
            pass

        for char in text:
            try:
                await page.keyboard.type(char)
            except Exception:
                pass

            # Base per-keystroke speed: ~30-70ms
            delay = random.uniform(0.030, 0.070)

            # Natural pause on word boundaries and punctuation
            if char in " \n.,;:!?-":
                delay += random.uniform(0.060, 0.140)

            # Occasional cognitive hesitation (5% chance)
            if random.random() < 0.05:
                delay += random.uniform(0.100, 0.220)

            await asyncio.sleep(delay)

        return True

    @classmethod
    async def humanized_scroll(
        cls,
        page: Page,
        delta_y: int,
        steps: Optional[int] = None,
    ) -> bool:
        """
        Scrolls the page incrementally in smaller wheel passes rather than a single jarring jump.
        """
        num_steps = steps or random.randint(3, 7)
        chunk_size = delta_y / float(num_steps)

        for _ in range(num_steps):
            jitter = chunk_size * random.uniform(0.8, 1.2)
            try:
                await page.mouse.wheel(0, round(jitter, 1))
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.025, 0.075))

        return True
