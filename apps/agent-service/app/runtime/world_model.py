"""
runtime/world_model.py — Application World Model & Behavioral Communication Graph.

Architecture (AGENTS.md §8):
  Evolves InsightAPI from an endpoint list to a structured behavioral communication graph:
    Page -> contains -> UIElement
    UIElement -> triggers -> Endpoint
    Page -> causes -> NetworkObservation
    Endpoint -> returns -> Entity
    Endpoint -> depends_on -> Endpoint
    Endpoint -> requires -> Authentication
    Evidence -> supports -> Endpoint
    Evidence -> supports -> Hypothesis

Storage: In-memory structured representation with JSONB serialization. No external graph DB required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.runtime.models import (
    Observation,
    ObservationSource,
    ConfidenceLevel,
    EvidenceStatus,
)


class NodeType(str, Enum):
    PAGE = "page"
    UI_ELEMENT = "ui_element"
    ENDPOINT = "endpoint"
    ENTITY = "entity"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"


class RelationType(str, Enum):
    CONTAINS = "contains"
    TRIGGERS = "triggers"
    CAUSES = "causes"
    RETURNS = "returns"
    DEPENDS_ON = "depends_on"
    REQUIRES_AUTH = "requires_auth"
    USES_PARAM = "uses_param"
    PRODUCES_ID = "produces_id"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class GraphNode(BaseModel):
    """A generic node in the Application World Model graph."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType
    label: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphEdge(BaseModel):
    """A directed edge representing a relationship in the Application Graph."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relation: RelationType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApplicationGraph(BaseModel):
    """
    Stateful Application World Model for an active investigation session.
    """
    session_id: str
    nodes: Dict[str, GraphNode] = Field(default_factory=dict)
    edges: List[GraphEdge] = Field(default_factory=list)

    # Index lookups for O(1) deduplication
    _url_to_page_id: Dict[str, str] = {}
    _endpoint_key_to_id: Dict[str, str] = {}

    def add_page(
        self,
        url: str,
        title: str = "",
        state_hash: str = "",
        status_code: Optional[int] = 200,
    ) -> str:
        """Add or update a Page node in the graph."""
        if url in self._url_to_page_id:
            page_id = self._url_to_page_id[url]
            page_node = self.nodes[page_id]
            if title:
                page_node.attributes["title"] = title
            if state_hash:
                page_node.attributes["state_hash"] = state_hash
            return page_id

        page_id = f"page-{uuid.uuid4().hex[:8]}"
        node = GraphNode(
            id=page_id,
            node_type=NodeType.PAGE,
            label=title or url,
            attributes={
                "url": url,
                "title": title,
                "state_hash": state_hash,
                "status_code": status_code,
            },
        )
        self.nodes[page_id] = node
        self._url_to_page_id[url] = page_id
        return page_id

    def add_ui_element(
        self,
        page_id: str,
        role: str,
        name: str,
        tag_name: str,
        selector: Optional[str] = None,
        ref_id: Optional[str] = None,
    ) -> str:
        """Add a UI element node and link Page -> contains -> UIElement."""
        elem_id = f"elem-{uuid.uuid4().hex[:8]}"
        node = GraphNode(
            id=elem_id,
            node_type=NodeType.UI_ELEMENT,
            label=f"<{tag_name}> {name[:30]}",
            attributes={
                "role": role,
                "name": name,
                "tag_name": tag_name,
                "selector": selector,
                "ref_id": ref_id,
                "page_id": page_id,
            },
        )
        self.nodes[elem_id] = node

        # Edge: Page -> contains -> UIElement
        self.add_edge(page_id, elem_id, RelationType.CONTAINS)
        return elem_id

    def add_endpoint(
        self,
        method: str,
        template_path: str,
        example_url: Optional[str] = None,
        status_code: Optional[int] = 200,
        is_graphql: bool = False,
        graphql_operation: Optional[str] = None,
        auth_required: Optional[bool] = None,
        inferred_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add or update an API Endpoint node in the graph."""
        endpoint_key = f"{method.upper()} {template_path}"
        if endpoint_key in self._endpoint_key_to_id:
            ep_id = self._endpoint_key_to_id[endpoint_key]
            ep_node = self.nodes[ep_id]
            if status_code:
                ep_node.attributes["status_code"] = status_code
            if inferred_schema:
                ep_node.attributes["inferred_schema"] = inferred_schema
            if auth_required is not None:
                ep_node.attributes["auth_required"] = auth_required
            return ep_id

        ep_id = f"ep-{uuid.uuid4().hex[:8]}"
        node = GraphNode(
            id=ep_id,
            node_type=NodeType.ENDPOINT,
            label=endpoint_key,
            attributes={
                "method": method.upper(),
                "template_path": template_path,
                "example_url": example_url,
                "status_code": status_code,
                "is_graphql": is_graphql,
                "graphql_operation": graphql_operation,
                "auth_required": auth_required,
                "inferred_schema": inferred_schema,
                "confidence": ConfidenceLevel.TESTED.value if status_code else ConfidenceLevel.INFERRED.value,
            },
        )
        self.nodes[ep_id] = node
        self._endpoint_key_to_id[endpoint_key] = ep_id
        return ep_id

    def add_entity(self, name: str, fields: List[str], identifier_field: Optional[str] = None) -> str:
        """Add a Data Entity node in the graph (e.g., User, Order, Product)."""
        entity_id = f"ent-{uuid.uuid4().hex[:8]}"
        node = GraphNode(
            id=entity_id,
            node_type=NodeType.ENTITY,
            label=name,
            attributes={
                "name": name,
                "fields": fields,
                "identifier_field": identifier_field or "id",
            },
        )
        self.nodes[entity_id] = node
        return entity_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: RelationType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphEdge:
        """Create a directed relationship between two existing nodes."""
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            metadata=metadata or {},
        )
        self.edges.append(edge)
        return edge

    def link_ui_to_endpoint(self, ui_element_id: str, endpoint_id: str) -> GraphEdge:
        """Link UIElement -> triggers -> Endpoint."""
        return self.add_edge(ui_element_id, endpoint_id, RelationType.TRIGGERS)

    def link_endpoint_dependency(
        self,
        upstream_endpoint_id: str,
        downstream_endpoint_id: str,
        param_mapping: Optional[Dict[str, str]] = None,
    ) -> GraphEdge:
        """Link Endpoint -> depends_on -> Endpoint (with optional parameter mapping)."""
        return self.add_edge(
            source_id=downstream_endpoint_id,
            target_id=upstream_endpoint_id,
            relation=RelationType.DEPENDS_ON,
            metadata={"param_mapping": param_mapping or {}},
        )

    def link_endpoint_returns_entity(self, endpoint_id: str, entity_id: str) -> GraphEdge:
        """Link Endpoint -> returns -> Entity."""
        return self.add_edge(endpoint_id, entity_id, RelationType.RETURNS)

    def record_observation(self, obs: Observation) -> Optional[str]:
        """
        Integrate an Observation directly into the Application Graph:
        - Automatically creates/updates Endpoint node if request data exists.
        - Automatically links Page -> causes -> Endpoint if page_url is present.
        """
        if not obs.request_url and not obs.request_method:
            return None

        import urllib.parse
        import re

        method = obs.request_method or "GET"
        parsed = urllib.parse.urlparse(obs.request_url) if obs.request_url else None
        raw_path = obs.request_template or (parsed.path if parsed and parsed.path else "/")
        
        # Dynamic path normalization (e.g. /projects/1 -> /projects/{id})
        template_path = raw_path
        if "{" not in template_path:
            template_path = re.sub(r"/(\d+)(?=/|$)", r"/{id}", template_path)
            template_path = re.sub(r"/(org-\d+|user-\d+|item-\d+)(?=/|$)", r"/{id}", template_path)

        is_auth = (obs.response_status in (401, 403)) or bool("authorization" in [h.lower() for h in (obs.request_headers or {}).keys()])

        ep_id = self.add_endpoint(
            method=method,
            template_path=template_path,
            example_url=obs.request_url,
            status_code=obs.response_status,
            inferred_schema=obs.inferred_schema,
            auth_required=is_auth if is_auth else None,
        )

        if obs.page_url:
            page_id = self.add_page(obs.page_url, title=obs.page_title or "")
            self.add_edge(page_id, ep_id, RelationType.CAUSES, {"observation_id": obs.id})

        return ep_id

    def summary(self) -> Dict[str, Any]:
        """Summary metrics of the discovered application graph."""
        type_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            type_counts[node.node_type.value] = type_counts.get(node.node_type.value, 0) + 1

        rel_counts: Dict[str, int] = {}
        for edge in self.edges:
            rel_counts[edge.relation.value] = rel_counts.get(edge.relation.value, 0) + 1

        return {
            "session_id": self.session_id,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_counts": type_counts,
            "relation_counts": rel_counts,
        }

    def get_endpoints(self) -> List[DiscoveredEndpoint]:
        """Returns all discovered endpoints as typed DiscoveredEndpoint models."""
        from app.runtime.models import DiscoveredEndpoint
        results = []
        for n in self.nodes.values():
            if n.node_type == NodeType.ENDPOINT:
                results.append(
                    DiscoveredEndpoint(
                        session_id=self.session_id,
                        method=n.attributes.get("method", "GET"),
                        template_path=n.attributes.get("template_path", n.label),
                        example_url=n.attributes.get("example_url"),
                        status_code=n.attributes.get("status_code", 200),
                        is_graphql=n.attributes.get("is_graphql", False),
                        graphql_operation=n.attributes.get("graphql_operation"),
                        auth_required=bool(n.attributes.get("auth_required", False)),
                        inferred_schema=n.attributes.get("inferred_schema"),
                        confidence=ConfidenceLevel(n.attributes.get("confidence", ConfidenceLevel.TESTED.value)),
                    )
                )
        return results

    def to_dict(self) -> Dict[str, Any]:
        """Full JSON-serializable representation of the graph."""
        return {
            "session_id": self.session_id,
            "nodes": [n.model_dump(mode="json") for n in self.nodes.values()],
            "edges": [e.model_dump(mode="json") for e in self.edges],
            "summary": self.summary(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicationGraph":
        """Deserialize ApplicationGraph from dictionary structure."""
        raw_nodes = data.get("nodes", {})
        nodes_dict: Dict[str, GraphNode] = {}
        if isinstance(raw_nodes, list):
            for n in raw_nodes:
                node = GraphNode.model_validate(n)
                nodes_dict[node.id] = node
        elif isinstance(raw_nodes, dict):
            for k, v in raw_nodes.items():
                nodes_dict[k] = GraphNode.model_validate(v)

        raw_edges = data.get("edges", [])
        edges_list = [GraphEdge.model_validate(e) for e in raw_edges]

        graph = cls(
            session_id=data.get("session_id", ""),
            nodes=nodes_dict,
            edges=edges_list,
        )
        # Rebuild index lookups
        for node in nodes_dict.values():
            if node.node_type == NodeType.PAGE:
                url = node.attributes.get("url")
                if url:
                    graph._url_to_page_id[url] = node.id
            elif node.node_type == NodeType.ENDPOINT:
                method = node.attributes.get("method", "GET")
                template = node.attributes.get("template_path", "")
                graph._endpoint_key_to_id[f"{method} {template}"] = node.id

        return graph
