from langgraph.graph import StateGraph, END
from app.graph.state import DocumentState
from app.graph import nodes


def build_pipeline():
    graph = StateGraph(DocumentState)

    graph.add_node("classify_document", nodes.classify_document)
    graph.add_node("extract_native", nodes.extract_native)
    graph.add_node("extract_ocr", nodes.extract_ocr)
    graph.add_node("extract_vision", nodes.extract_vision)

    graph.set_entry_point("classify_document")

    graph.add_conditional_edges(
        "classify_document",
        nodes.route_by_type,
        {
            "extract_native": "extract_native",
            "extract_ocr": "extract_ocr",
            "extract_vision": "extract_vision",
        },
    )

    graph.add_edge("extract_native", END)

    graph.add_conditional_edges(
        "extract_ocr",
        nodes.should_escalate_to_vision,
        {
            "extract_vision": "extract_vision",
            "done": END,
        },
    )

    graph.add_edge("extract_vision", END)

    return graph.compile()


document_pipeline = build_pipeline()