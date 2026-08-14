"""
VisionPlannerNode — Set-of-Mark (SoM) visual reasoning for Canvas / WebGL navigation.
Sends annotated screenshots with numbered marks to Vision LLM (GPT-4o) and resolves
the chosen visual target to screen coordinates.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Dict, Any, Optional

from app.agents.state import CrawlState
from app.core.config import settings
from app.engine.vision.som import SetOfMarksAnnotator

logger = logging.getLogger("agent.vision_planner")


class VisionPlannerNode:
    """
    Autonomous planning node that visually inspects Canvas / WebGL / graphical UIs
    using Set-of-Mark (SoM) bounding box annotations and Vision LLM reasoning.
    """

    @classmethod
    async def select_action(cls, state: CrawlState) -> Optional[Dict[str, Any]]:
        """
        Captures SoM annotated screenshot, asks Vision LLM to select the most
        promising interactive visual control, and maps it back to screen coordinates.
        """
        page = state.get("page_ref")
        if not page:
            logger.warning("VisionPlannerNode: page_ref not available in state.")
            return None

        # 1. Generate Set-of-Mark annotated screenshot and marks registry
        try:
            annotated_png, marks_registry = await SetOfMarksAnnotator.annotate_page(page)
        except Exception as e:
            logger.error(f"VisionPlannerNode: Failed to generate SoM annotation: {e}", exc_info=True)
            return None

        if not marks_registry:
            logger.warning("VisionPlannerNode: No candidate visual marks generated.")
            return None

        # 2. Check cost manager budget
        cost_manager = state.get("cost_manager")
        if cost_manager and cost_manager.is_budget_exhausted():
            logger.info("VisionPlannerNode: Token budget exhausted. Falling back to primary mark.")
            first_mark = marks_registry[1]
            return cls._build_action_dict(1, first_mark, "click", "", "Fallback: Token budget exhausted.")

        # 3. Formulate Vision Prompt
        goal = state.get("goal") or "Discover hidden API endpoints, query triggers, and submit actions"
        current_url = state.get("current_url") or page.url

        marks_summary = "\n".join(
            f"  - Mark [{m_id}]: center=({info['x']}, {info['y']}), box={info['box']}"
            for m_id, info in list(marks_registry.items())[:12]
        )

        prompt_text = (
            f"You are an autonomous web API intelligence agent inspecting a Canvas / WebGL / Graphical interface.\n"
            f"Page URL: '{current_url}'\n"
            f"Goal: '{goal}'\n\n"
            f"Numbered marks [1], [2], [3]... are overlaid on candidate interactive regions (e.g. toolbars, buttons, tools, menu items, action triggers).\n"
            f"Available candidate marks:\n{marks_summary}\n\n"
            f"Task:\n"
            f"1. Examine the attached annotated screenshot.\n"
            f"2. Select the single best numbered mark [N] that is most likely to trigger a network / API request when clicked or interacted with.\n"
            f"3. Specify the action ('click' or 'type'). If 'type', specify the text value to input.\n\n"
            f"Respond ONLY with a JSON object in this exact format:\n"
            f'{{\n  "mark": <number>,\n  "action": "click",\n  "value": "",\n  "reasoning": "<1-2 sentence explanation>"\n}}'
        )

        b64_image = base64.b64encode(annotated_png).decode("utf-8")
        data_url = f"data:image/png;base64,{b64_image}"

        # 4. Invoke Vision Model (GPT-4o / GPT-4o-mini)
        try:
            from langchain_core.messages import HumanMessage
            from app.agents.nodes.llm_client import get_llm, ModelTier, ModelRouter, extract_text_content, repair_json_string

            llm = get_llm(ModelTier.VISION)
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            )

            logger.info("👁️ VisionPlannerNode: Querying Vision LLM with Set-of-Mark screenshot...")
            response = await llm.ainvoke([message])
            response_text = extract_text_content(response)

            # Record token usage if cost manager present
            if cost_manager:
                tokens_est = (len(prompt_text) + len(response_text)) // 4 + 1000  # image tokens estimate
                model_name = ModelRouter.get_model_name(ModelTier.VISION)
                cost_manager.record_usage(tokens_est, model_name)

            clean_json = repair_json_string(response_text)
            parsed = json.loads(clean_json)

            selected_mark = int(parsed.get("mark", 1))
            action_type = parsed.get("action", "click")
            action_value = parsed.get("value", "")
            reasoning = parsed.get("reasoning", f"Vision LLM selected Mark #{selected_mark}")

            mark_info = marks_registry.get(selected_mark) or marks_registry[1]
            logger.info(f"🎯 VisionPlannerNode selected Mark #{selected_mark} at ({mark_info['x']}, {mark_info['y']}): {reasoning}")

            return cls._build_action_dict(selected_mark, mark_info, action_type, action_value, reasoning)

        except Exception as e:
            logger.warning(f"VisionPlannerNode: LLM call failed ({type(e).__name__}: {e}). Using heuristic first mark.")
            first_mark = marks_registry[1]
            return cls._build_action_dict(1, first_mark, "click", "", f"Heuristic fallback on visual mark 1 ({e})")

    @staticmethod
    def _build_action_dict(
        mark_id: int,
        mark_info: Dict[str, Any],
        action_type: str,
        value: str,
        reasoning: str,
    ) -> Dict[str, Any]:
        """Constructs an action dictionary compatible with DynamicRuntimeExecutor and CrawlState."""
        cx = mark_info["x"]
        cy = mark_info["y"]
        return {
            "action": action_type,
            "coordinates": {"x": cx, "y": cy},
            "x": cx,
            "y": cy,
            "is_vision_action": True,
            "mark": mark_id,
            "reasoning": reasoning,
            "selector": f"canvas[mark={mark_id},x={cx},y={cy}]",
            "text": f"Vision Mark #{mark_id}",
            "tag": "canvas_control",
            "value": value,
        }
