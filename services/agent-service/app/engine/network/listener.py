import json
import logging
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, Request, Response
from app.engine.network.filter import NetworkFilter
from app.engine.network.deduplicator import URLDeduplicator
from app.core.logging_config import get_logger, log_network_event

logger = get_logger("engine.network")


class CapturedEndpoint:
    def __init__(
        self,
        method: str,
        url: str,
        template_route: str,
        status: int,
        resource_type: str,
        request_headers: Dict[str, str],
        request_payload: Optional[Any],
        response_headers: Dict[str, str],
        response_body: Optional[Any],
        graphql_operation_name: Optional[str] = None,
        triggered_by: Optional[Dict[str, Any]] = None,
        related_calls: Optional[List[Dict[str, Any]]] = None,
        is_vision_derived: Optional[bool] = False,
    ):
        self.method = method
        self.url = url
        self.template_route = template_route
        self.status = status
        self.resource_type = resource_type
        self.request_headers = request_headers
        self.request_payload = request_payload
        self.response_headers = response_headers
        self.response_body = response_body
        self.graphql_operation_name = graphql_operation_name
        self.triggered_by = triggered_by
        self.related_calls = related_calls or []
        self.is_vision_derived = is_vision_derived or False

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "method": self.method,
            "url": self.url,
            "template_route": self.template_route,
            "status": self.status,
            "resource_type": self.resource_type,
            "request_headers": self.request_headers,
            "request_payload": self.request_payload,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "graphql_operation_name": self.graphql_operation_name,
            "is_vision_derived": self.is_vision_derived,
        }
        if self.triggered_by:
            data["triggered_by"] = self.triggered_by
        if self.related_calls:
            data["related_calls"] = self.related_calls
        return data


# Maximum raw observations kept per (method, template_route, status) tuple.
# AnalyzerNode groups and merges these into one schema per group.
MAX_OBSERVATIONS_PER_ROUTE: int = 10


class NetworkObserver:
    """
    Listens to live Playwright network traffic, filters out noise, parses GraphQL operations,
    and collects structured captured API requests.

    Deduplication policy
    --------------------
    Each unique ``(method, template_route, status)`` key is captured up to
    ``MAX_OBSERVATIONS_PER_ROUTE`` times.  Keeping multiple observations lets
    ``AnalyzerNode`` merge schemas across real-world payload variation and compute
    a stability-based confidence score.  The exporter always receives one merged
    record per route group.
    """
    def __init__(self):
        self.captured_endpoints: List[CapturedEndpoint] = []
        # Maps route_key → observation count (caps at MAX_OBSERVATIONS_PER_ROUTE)
        self._route_counts: Dict[str, int] = {}

    def attach_to_page(self, page: Page):
        """Attaches request, response, and WebSocket handlers to a Playwright Page instance."""
        page.on("response", self._handle_response)
        page.on("websocket", self._handle_websocket)

    def _handle_websocket(self, ws):
        """Captures live WebSocket connection handshakes (one record per unique WS URL)."""
        try:
            url = ws.url
            template_route = URLDeduplicator.parameterize_path(url)
            route_key = f"WS:{template_route}:101"

            if self._route_counts.get(route_key, 0) >= MAX_OBSERVATIONS_PER_ROUTE:
                return
            self._route_counts[route_key] = self._route_counts.get(route_key, 0) + 1

            endpoint = CapturedEndpoint(
                method="WS",
                url=url,
                template_route=template_route,
                status=101,
                resource_type="websocket",
                request_headers={},
                request_payload=None,
                response_headers={},
                response_body={"message": "WebSocket Handshake Connection Established"},
                graphql_operation_name=None
            )
            self.captured_endpoints.append(endpoint)
        except Exception as e:
            logger.debug(f"Error handling WebSocket event: {e}")

    async def _handle_response(self, response: Response):
        try:
            request = response.request
            url = response.url
            resource_type = request.resource_type

            content_type = response.headers.get("content-type", "")
            if not NetworkFilter.is_api_request(url, resource_type, content_type):
                return

            if not NetworkFilter.is_api_content_type(content_type):
                return

            method = request.method.upper()
            status = response.status

            # Extract request payload & check GraphQL operationName (POST or GET)
            post_data = request.post_data
            request_payload = None
            graphql_op_name = None

            if post_data:
                try:
                    request_payload = json.loads(post_data)
                    if isinstance(request_payload, dict) and "operationName" in request_payload:
                        graphql_op_name = request_payload.get("operationName")
                    elif isinstance(request_payload, list):
                        op_names = [
                            op.get("operationName") for op in request_payload
                            if isinstance(op, dict) and op.get("operationName")
                        ]
                        if op_names:
                            graphql_op_name = "+".join(op_names)
                except Exception:
                    request_payload = post_data

            # Check GET query params for GraphQL operationName
            if not graphql_op_name:
                parsed_qs = parse_qs(urlparse(url).query)
                if "operationName" in parsed_qs:
                    graphql_op_name = parsed_qs["operationName"][0]

            template_route = URLDeduplicator.parameterize_path(url)
            if graphql_op_name:
                template_route = f"{template_route} ({graphql_op_name})"

            # Allow up to MAX_OBSERVATIONS_PER_ROUTE hits per (method, route, status) key.
            # AnalyzerNode merges them into one schema + examples block before export.
            route_key = f"{method}:{template_route}:{status}"
            count = self._route_counts.get(route_key, 0)
            if count >= MAX_OBSERVATIONS_PER_ROUTE:
                return
            self._route_counts[route_key] = count + 1

            # Extract response body safely (bounded by 3.0s timeout)
            response_body = None
            try:
                body_bytes = await asyncio.wait_for(response.body(), timeout=3.0)
                body_text = body_bytes.decode("utf-8", errors="ignore")
                try:
                    response_body = json.loads(body_text)
                except Exception:
                    response_body = body_text[:1000]
            except Exception as e:
                logger.debug(f"Failed to read response body for {url}: {e}")

            # Apply secret & token redaction to headers and body
            clean_req_headers = NetworkFilter.redact_sensitive_headers(dict(request.headers))
            clean_res_headers = NetworkFilter.redact_sensitive_headers(dict(response.headers))
            clean_req_payload = NetworkFilter.redact_sensitive_body(request_payload)
            clean_res_body = NetworkFilter.redact_sensitive_body(response_body)

            endpoint = CapturedEndpoint(
                method=method,
                url=url,
                template_route=template_route,
                status=status,
                resource_type=resource_type,
                request_headers=clean_req_headers,
                request_payload=clean_req_payload,
                response_headers=clean_res_headers,
                response_body=clean_res_body,
                graphql_operation_name=graphql_op_name
            )
            self.captured_endpoints.append(endpoint)
            log_network_event(logger, method, template_route, status, is_graphql=bool(graphql_op_name))
        except Exception as e:
            logger.debug(f"Error handling response: {e}")
