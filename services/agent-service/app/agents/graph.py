from langgraph.graph import StateGraph, END
from app.agents.state import CrawlState
from app.agents.nodes.planner import PlannerNode
from app.agents.nodes.risk_evaluator import RiskEvaluatorNode
from app.agents.nodes.executor import ExecutorNode
from app.agents.nodes.analyzer import AnalyzerNode
from app.agents.nodes.reflection import ReflectionNode
from app.agents.nodes.security_reasoner import SecurityReasonerNode


def should_continue_risk(state: CrawlState) -> str:
    """Conditional router following risk evaluation."""
    if state.get("is_complete", False):
        return "analyzer"
    if not state.get("is_safe_action", True):
        return "planner"  # Skip unsafe action and re-plan
    return "executor"     # Proceed to UI execution


def should_continue_executor(state: CrawlState) -> str:
    """Conditional router following UI interaction execution."""
    if state.get("is_complete", False):
        return "analyzer"
    if ReflectionNode.should_reflect(state):
        return "reflection"  # Route to periodic self-critique review
    return "planner"     # Loop back to planner for next interaction cycle


def should_continue_after_analyzer(state: CrawlState) -> str:
    """Route to security_reasoner if security testing is enabled, else END."""
    if state.get("security_testing_enabled"):
        return "security_reasoner"
    return END


async def safe_planner_process(state: CrawlState) -> CrawlState:
    try:
        return await PlannerNode.process(state)
    except Exception as e:
        import logging
        logging.getLogger("agent.graph").error(f"PlannerNode error: {e}", exc_info=True)
        state["is_complete"] = True
        state["error_message"] = str(e)
        return state


async def safe_executor_process(state: CrawlState) -> CrawlState:
    try:
        return await ExecutorNode.process(state)
    except Exception as e:
        import logging
        logging.getLogger("agent.graph").error(f"ExecutorNode error: {e}", exc_info=True)
        state["is_complete"] = True
        state["error_message"] = str(e)
        return state


def build_crawl_graph() -> StateGraph:
    """
    Constructs and compiles the master LangGraph execution graph for InsightAPI AI.
    """
    workflow = StateGraph(CrawlState)

    # Add Nodes (wrapped with crash resilience)
    workflow.add_node("planner", safe_planner_process)
    workflow.add_node("risk_evaluator", RiskEvaluatorNode.process)
    workflow.add_node("executor", safe_executor_process)
    workflow.add_node("reflection", ReflectionNode.process)
    workflow.add_node("analyzer", AnalyzerNode.process)
    workflow.add_node("security_reasoner", SecurityReasonerNode.process)

    # Set Entry Point
    workflow.set_entry_point("planner")

    # Add Edges
    workflow.add_edge("planner", "risk_evaluator")
    
    workflow.add_conditional_edges(
        "risk_evaluator",
        should_continue_risk,
        {
            "planner": "planner",
            "executor": "executor",
            "analyzer": "analyzer"
        }
    )

    workflow.add_conditional_edges(
        "executor",
        should_continue_executor,
        {
            "planner": "planner",
            "reflection": "reflection",
            "analyzer": "analyzer"
        }
    )

    workflow.add_edge("reflection", "planner")
    workflow.add_conditional_edges(
        "analyzer",
        should_continue_after_analyzer,
        {
            "security_reasoner": "security_reasoner",
            END: END,
        }
    )
    workflow.add_edge("security_reasoner", END)

    return workflow.compile()
