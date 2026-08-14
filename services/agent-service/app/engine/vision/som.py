"""
Set-of-Mark (SoM) Visual Candidate Generator.
Takes a webpage screenshot, detects canvas / WebGL / graphical regions, proposes
candidate clickable targets, and overlays numbered bounding-box mark badges using Pillow.
"""
from __future__ import annotations

import io
import logging
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("agent.vision.som")

# Contrasting vibrant palette for numbered mark borders and badges
BADGE_COLORS = [
    ("#E11D48", "#FFFFFF"),  # Rose / White
    ("#2563EB", "#FFFFFF"),  # Blue / White
    ("#059669", "#FFFFFF"),  # Emerald / White
    ("#D97706", "#FFFFFF"),  # Amber / White
    ("#7C3AED", "#FFFFFF"),  # Violet / White
    ("#0891B2", "#FFFFFF"),  # Cyan / White
    ("#DC2626", "#FFFFFF"),  # Red / White
    ("#4F46E5", "#FFFFFF"),  # Indigo / White
]


class SetOfMarksAnnotator:
    """
    Overlays visual numbered marks on candidate interactive regions
    for Vision LLM reasoning when DOM extraction is unavailable.
    """

    @classmethod
    def propose_candidate_boxes(
        cls,
        img_width: int,
        img_height: int,
        canvas_rects: Optional[List[Dict[str, float]]] = None,
    ) -> List[Tuple[int, int, int, int]]:
        """
        Generates candidate bounding boxes [x1, y1, x2, y2] across canvas
        or graphical UI regions using spatial grid heuristics and toolbar zones.
        """
        boxes: List[Tuple[int, int, int, int]] = []

        if canvas_rects:
            for rect in canvas_rects:
                rx = int(rect.get("x", 0))
                ry = int(rect.get("y", 0))
                rw = int(rect.get("width", img_width))
                rh = int(rect.get("height", img_height))

                # Clamp to image bounds
                rx = max(0, min(rx, img_width - 10))
                ry = max(0, min(ry, img_height - 10))
                rw = max(20, min(rw, img_width - rx))
                rh = max(20, min(rh, img_height - ry))

                # 1. Top toolbar / menu strip within canvas region (4-6 buttons)
                tb_height = min(60, int(rh * 0.15))
                btn_count = 5
                btn_w = rw // btn_count
                for i in range(btn_count):
                    bx1 = rx + i * btn_w + 4
                    by1 = ry + 4
                    bx2 = min(bx1 + btn_w - 8, rx + rw)
                    by2 = ry + tb_height - 4
                    if bx2 > bx1 and by2 > by1:
                        boxes.append((bx1, by1, bx2, by2))

                # 2. Left vertical tool rail (3-4 tools)
                tool_w = min(60, int(rw * 0.15))
                tool_h = (rh - tb_height) // 4
                for i in range(4):
                    bx1 = rx + 4
                    by1 = ry + tb_height + i * tool_h + 4
                    bx2 = rx + tool_w - 4
                    by2 = min(by1 + tool_h - 8, ry + rh)
                    if bx2 > bx1 and by2 > by1:
                        boxes.append((bx1, by1, bx2, by2))

                # 3. Canvas workspace active quadrant hotspots
                ws_x = rx + tool_w
                ws_y = ry + tb_height
                ws_w = rw - tool_w
                ws_h = rh - tb_height

                if ws_w > 50 and ws_h > 50:
                    # Top-Left, Center, and Bottom-Right interaction spots
                    boxes.append((ws_x + int(ws_w * 0.2), ws_y + int(ws_h * 0.2), ws_x + int(ws_w * 0.4), ws_y + int(ws_h * 0.4)))
                    boxes.append((ws_x + int(ws_w * 0.45), ws_y + int(ws_h * 0.45), ws_x + int(ws_w * 0.65), ws_y + int(ws_h * 0.65)))
                    boxes.append((ws_x + int(ws_w * 0.7), ws_y + int(ws_h * 0.7), ws_x + int(ws_w * 0.9), ws_y + int(ws_h * 0.9)))

        # Fallback: if no canvas rects or empty boxes, generate standard 3x3 viewport grid
        if not boxes:
            cols, rows = 3, 3
            cell_w = img_width // cols
            cell_h = img_height // rows
            for r in range(rows):
                for c in range(cols):
                    x1 = c * cell_w + 10
                    y1 = r * cell_h + 10
                    x2 = (c + 1) * cell_w - 10
                    y2 = (r + 1) * cell_h - 10
                    boxes.append((x1, y1, x2, y2))

        return boxes

    @classmethod
    def annotate_image(
        cls,
        image_bytes: bytes,
        canvas_rects: Optional[List[Dict[str, float]]] = None,
    ) -> Tuple[bytes, Dict[int, Dict[str, Any]]]:
        """
        Draws numbered bounding box marks on the image.

        Returns
        -------
        (annotated_png_bytes, marks_registry)
        where marks_registry is {mark_id: {"mark": int, "x": int, "y": int, "box": list}}
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = img.size
        draw = ImageDraw.Draw(img)

        # Default system or PIL font
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        candidate_boxes = cls.propose_candidate_boxes(width, height, canvas_rects)
        marks_registry: Dict[int, Dict[str, Any]] = {}

        for idx, (x1, y1, x2, y2) in enumerate(candidate_boxes, start=1):
            color_border, color_text = BADGE_COLORS[(idx - 1) % len(BADGE_COLORS)]

            # Draw bounding box outline
            draw.rectangle([x1, y1, x2, y2], outline=color_border, width=3)

            # Draw solid badge for mark label
            badge_text = f" [{idx}] "
            badge_x = x1
            badge_y = max(0, y1 - 18)
            badge_w = 34
            badge_h = 18

            draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill=color_border)
            draw.text((badge_x + 3, badge_y + 2), badge_text, fill=color_text, font=font)

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            marks_registry[idx] = {
                "mark": idx,
                "x": cx,
                "y": cy,
                "box": [x1, y1, x2, y2],
                "label": f"Mark {idx}",
            }

        output_buf = io.BytesIO()
        img.save(output_buf, format="PNG")
        return output_buf.getvalue(), marks_registry

    @classmethod
    async def annotate_page(cls, page: Any) -> Tuple[bytes, Dict[int, Dict[str, Any]]]:
        """
        Captures screenshot of live Playwright page, queries canvas bounding rects,
        and returns annotated screenshot bytes with mark coordinates.
        """
        screenshot_bytes = await page.screenshot(type="png", full_page=False)

        canvas_rects = []
        try:
            canvas_rects = await page.evaluate("""
            () => {
                const canvases = Array.from(document.querySelectorAll('canvas, svg.dense-canvas, [data-interactive-canvas]'));
                return canvases.map(c => {
                    const r = c.getBoundingClientRect();
                    return { x: r.x, y: r.y, width: r.width, height: r.height };
                }).filter(r => r.width > 20 && r.height > 20);
            }
            """)
        except Exception:
            pass

        return cls.annotate_image(screenshot_bytes, canvas_rects)
