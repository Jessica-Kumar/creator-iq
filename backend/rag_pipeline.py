import os
import logging
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel
from typing import List, Dict
from ingest import get_db, embed_model

class RAGState(BaseModel):
    question: str
    history: List[Dict] = []
    video_ids: List[str] = []
    context: str = ""
    answer: str = ""

def retrieve(state: RAGState) -> Dict:
    collection = get_db()
    query_embed = embed_model.encode(state.question).tolist()
    # Filter chunks so they only come from the active video IDs of the current session
    where_filter = {"video_id": {"$in": state.video_ids}} if state.video_ids else None
    results = collection.query(
        query_embeddings=[query_embed],
        n_results=5,
        where=where_filter
    )
    if not results or not results.get("documents") or len(results["documents"]) == 0 or len(results["documents"][0]) == 0:
        return {"context": "No relevant context found."}
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    context_parts = []
    for doc, meta in zip(documents, metadatas):
        vid = meta.get("video_id", "unknown")
        cidx = meta.get("chunk_index", 0)
        context_parts.append(f"[{vid} chunk {cidx}] {doc}")
    return {"context": "\n\n".join(context_parts)}

def generate_answer(state: RAGState) -> Dict:
    preferred_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    candidates = [preferred_model]
    for fallback in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"]:
        if fallback not in candidates:
            candidates.append(fallback)
            
    last_err = None
    for model_name in candidates:
        try:
            logging.info(f"Attempting to generate answer using Gemini model: {model_name}")
            llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.2, streaming=True)
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a social media analyst. Use the following video transcripts and metadata to answer the creator's question.
Always cite the source video and chunk index. Be concise but thorough.
Context:
{context}"""),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}")
            ])
            chain = prompt | llm
            response = chain.invoke({
                "context": state.context,
                "question": state.question,
                "history": [
                    HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"])
                    for m in state.history[-6:]
                ]
            })
            logging.info(f"Successfully generated answer using Gemini model: {model_name}")
            return {"answer": response.content}
        except Exception as e:
            err_msg = str(e)
            logging.warning(f"Failed to generate answer with model {model_name}: {err_msg}")
            last_err = e
            
    if last_err:
        raise last_err

def create_rag_graph():
    workflow = StateGraph(RAGState)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate_answer)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()