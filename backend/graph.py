"""
LangGraph workflow for the RAG pipeline.

    retrieve -> (relevant?) -> generate -> (grounded?) -> END
                    | no                       | no
                web search                 safe fallback

Every node appends a label to `trace`, which the API returns so the UI can
show which path a question took.
"""
import logging
from typing import TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from ddgs import DDGS
from services import retrieve_chunks, generate_answer, check_if_grounded, rewrite_query

logger = logging.getLogger("docmind.graph")

# Retrieved chunks below this cosine similarity are treated as "not in the documents".
SIMILARITY_THRESHOLD = 0.60
TOP_K = 5
WEB_RESULTS = 3


class AgentState(TypedDict):
    question: str
    chunks: List[Dict[str, Any]]
    answer: str
    trace: List[str]
    chat_history: List[Dict[str, str]]

# --- Nodes ---

def retrieve_documents_node(state: AgentState) -> Dict:
    """Node 1: Rewrite query (if needed) and retrieve relevant chunks."""
    question = state["question"]
    history = state.get("chat_history", [])
    trace = state.get("trace", []) or []

    # 1. Rewrite the query if we have conversation history
    if history:
        standalone_question = rewrite_query(question, history)
        logger.info("Rewrote query to: %r", standalone_question)
        trace.append("Contextualized Query")
    else:
        standalone_question = question

    trace.append("Database Retrieval")

    # 2. Use the REWRITTEN question for the database search
    chunks = retrieve_chunks(standalone_question, top_k=TOP_K)

    # 3. Update the state with the standalone question so the rest of the graph uses it
    return {"question": standalone_question, "chunks": chunks, "trace": trace}

def web_search_node(state: AgentState) -> Dict:
    """Node 2: Fallback web search using DuckDuckGo"""
    question = state["question"]
    trace = state.get("trace", [])
    trace.append("Web Search Fallback")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(question, max_results=WEB_RESULTS))
            web_chunks = [
                {
                    "filename": "Web Search (DuckDuckGo)",
                    "chunk_index": i,
                    "content": r["body"],
                    "similarity": 0.85  # Placeholder: web results have no embedding score
                } for i, r in enumerate(results)
            ]
    except Exception as e:
        web_chunks = [{"filename": "System", "chunk_index": 0, "content": f"Web search failed: {str(e)}", "similarity": 0.0}]

    return {"chunks": web_chunks, "trace": trace}

def generate_answer_node(state: AgentState) -> Dict:
    """Node 3: Generate the final answer using Gemini via services.py"""
    question = state["question"]
    chunks = state.get("chunks", [])
    trace = state.get("trace", [])
    trace.append("Gemini Generation")
    history = state.get("chat_history", [])

    answer = generate_answer(question, chunks, history)

    return {"answer": answer, "trace": trace}

def hallucination_fallback_node(state: AgentState) -> Dict:
    """Node 4: Runs if the answer was not grounded in the context."""
    trace = state.get("trace", [])
    trace.append("Caught Hallucination (Fallback)")

    safe_answer = "I'm sorry, but I couldn't find enough reliable information in the documents or the web to answer that confidently."

    return {"answer": safe_answer, "trace": trace}

# --- Routing Logic ---

def route_question(state: AgentState) -> Literal["generate_answer_node", "web_search_node"]:
    """Conditional edge: answer from the documents, or fall back to web search."""
    chunks = state.get("chunks", [])

    if not chunks:
        return "web_search_node"

    max_similarity = max(c["similarity"] for c in chunks)
    logger.info("Max similarity: %.3f (threshold %.2f)", max_similarity, SIMILARITY_THRESHOLD)

    if max_similarity < SIMILARITY_THRESHOLD:
        return "web_search_node"

    return "generate_answer_node"

def check_grounding_edge(state: AgentState) -> Literal["END", "hallucination_fallback_node"]:
    """
    Conditional edge: Evaluates the generated answer.
    """
    chunks = state.get("chunks", [])
    answer = state.get("answer", "")

    # If the answer is already a standard fallback, just end
    if "No documents have been uploaded" in answer or "Web search failed" in answer:
        return "END"

    is_grounded = check_if_grounded(chunks, answer)

    if is_grounded:
        return "END"

    logger.warning("Answer failed the grounding check; returning the safe fallback")
    return "hallucination_fallback_node"

# --- Build Graph ---

workflow = StateGraph(AgentState)
workflow.add_node("retrieve_documents_node", retrieve_documents_node)
workflow.add_node("web_search_node", web_search_node)
workflow.add_node("generate_answer_node", generate_answer_node)
workflow.add_node("hallucination_fallback_node", hallucination_fallback_node)

workflow.set_entry_point("retrieve_documents_node")
workflow.add_conditional_edges("retrieve_documents_node", route_question)

# Both retrieval and web search lead to generation
workflow.add_edge("web_search_node", "generate_answer_node")

# AFTER generation, we check for grounding instead of just ending
workflow.add_conditional_edges(
    "generate_answer_node",
    check_grounding_edge,
    {
        "END": END,
        "hallucination_fallback_node": "hallucination_fallback_node"
    }
)

# The fallback node ends the graph
workflow.add_edge("hallucination_fallback_node", END)

rag_app = workflow.compile()
