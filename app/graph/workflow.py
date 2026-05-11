from langgraph.graph import END, START, StateGraph

from app.graph.checkpoint import get_postgres_checkpointer
from app.graph.nodes import (
    categorizer_node,
    conflict_agent_node,
    critic_node,
    hitl_review_node,
    pii_scrubber_node,
    text_loader_node,
)
from app.graph.state import ADGSGraphState


def route_after_critic(state: ADGSGraphState) -> str:
    if state.get("requires_admin_approval"):
        return "hitl_review"

    return END


def build_adgs_graph():
    graph_builder = StateGraph(ADGSGraphState)

    graph_builder.add_node("text_loader", text_loader_node)
    graph_builder.add_node("categorizer", categorizer_node)
    graph_builder.add_node("pii_scrubber", pii_scrubber_node)
    graph_builder.add_node("conflict_agent", conflict_agent_node)
    graph_builder.add_node("critic", critic_node)
    graph_builder.add_node("hitl_review", hitl_review_node)

    graph_builder.add_edge(START, "text_loader")
    graph_builder.add_edge("text_loader", "categorizer")
    graph_builder.add_edge("categorizer", "pii_scrubber")
    graph_builder.add_edge("pii_scrubber", "conflict_agent")
    graph_builder.add_edge("conflict_agent", "critic")

    graph_builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "hitl_review": "hitl_review",
            END: END,
        },
    )

    graph_builder.add_edge("hitl_review", END)

    checkpointer = get_postgres_checkpointer()

    return graph_builder.compile(checkpointer=checkpointer)