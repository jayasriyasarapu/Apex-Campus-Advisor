"""
Flask Web Application for College Information Chatbot using RAG
================================================================
Exposes REST endpoints for querying the RAG pipeline and serves
the modern web interface for interactive chat and RAG inspection.
"""

import os
from flask import Flask, render_template, request, jsonify
from rag_engine import CollegeRAGEngine

app = Flask(__name__)

# Initialize the RAG engine on startup
rag_engine = CollegeRAGEngine()


@app.route("/")
def index():
    """Render the main college chatbot interface."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    RAG Chat endpoint.
    Payload: {"message": "string", "top_k": int (optional, default 3)}
    Returns: JSON containing generated answer, retrieved sources, similarity scores, and latency.
    """
    data = request.get_json(silent=True) or {}
    user_query = data.get("message", "").strip()
    top_k = int(data.get("top_k", 3))

    if not user_query:
        return jsonify({"error": "Please provide a valid question."}), 400

    try:
        # Run the RAG pipeline
        result = rag_engine.query_rag(user_query, top_k=top_k)
        return jsonify({
            "status": "success",
            "query": result["query"],
            "answer": result["answer"],
            "backend": result["backend"],
            "sources": result["sources"],
            "retrieved_chunks": result["retrieved_chunks"],
            "rag_prompt": result["rag_prompt"],
            "retrieval_latency_ms": result["retrieval_latency_ms"],
            "total_latency_ms": result["total_latency_ms"]
        })
    except Exception as e:
        app.logger.error(f"Error processing RAG query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An error occurred while retrieving college information.",
            "details": str(e)
        }), 500


@app.route("/api/topics", methods=["GET"])
def get_topics():
    """Retrieve catalog of available topics and knowledge categories."""
    categories = {}
    for doc in rag_engine.documents:
        cat = doc.get("category", "General")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "id": doc.get("id"),
            "title": doc.get("title"),
            "tags": doc.get("tags", [])
        })

    return jsonify({
        "total_documents": len(rag_engine.documents),
        "vocabulary_size": rag_engine.vocab_size,
        "categories": categories
    })


@app.route("/api/reload", methods=["POST"])
def reload_knowledge():
    """Reload the knowledge base index from disk."""
    try:
        rag_engine.load_and_index()
        return jsonify({
            "status": "success",
            "message": f"Successfully reloaded {len(rag_engine.documents)} documents. Vocabulary size: {rag_engine.vocab_size} terms."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "documents_indexed": len(rag_engine.documents),
        "vocab_size": rag_engine.vocab_size
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"🚀 College RAG Chatbot running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
