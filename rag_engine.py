

import json
import math
import os
import re
import time
import urllib.request
import urllib.error
import numpy as np


class CollegeRAGEngine:
    def __init__(self, data_path=None):
        self.data_path = data_path or os.path.join(
            os.path.dirname(__file__), "data", "college_knowledge_base.json"
        )
        self.documents = []
        self.vocabulary = {}
        self.idf = {}
        self.doc_vectors = None
        self.vocab_size = 0
        self.stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
            "arent", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", 
            "but", "by", "can", "cant", "cannot", "could", "did", "do", "does", "doing", "down", "during", 
            "each", "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", 
            "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isnt", "it", 
            "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", 
            "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", 
            "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", 
            "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", 
            "until", "up", "very", "was", "wasnt", "we", "were", "what", "when", "where", "which", "while", 
            "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself", "yourselves"
        }
        self.load_and_index()

    def tokenize(self, text):

        cleaned = re.sub(r"[^\w\s\.-]", " ", text.lower())
        tokens = []
        for word in re.split(r"[\s,;]+", cleaned):
            word = word.strip(".-")
            if len(word) >= 2 and word not in self.stopwords:
                tokens.append(word)
        return tokens

    def load_and_index(self):
        """Load college knowledge base and build the TF-IDF vector space index."""
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Knowledge base not found at: {self.data_path}")

        with open(self.data_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        # Build vocabulary from title, content, tags, and category
        doc_tokens_list = []
        df_counts = {}

        for doc in self.documents:
            # Emphasize title and tags by repeating them in the token pool
            combined_text = f"{doc.get('title', '')} {doc.get('title', '')} {doc.get('category', '')} {' '.join(doc.get('tags', []))} {doc.get('content', '')}"
            tokens = self.tokenize(combined_text)
            doc_tokens_list.append(tokens)

            # Document frequency
            unique_tokens = set(tokens)
            for token in unique_tokens:
                df_counts[token] = df_counts.get(token, 0) + 1

        # Vocabulary sorted by frequency/token
        self.vocabulary = {token: idx for idx, token in enumerate(sorted(df_counts.keys()))}
        self.vocab_size = len(self.vocabulary)
        num_docs = len(self.documents)

        # Compute IDF with smooth formula: log((1 + N) / (1 + df)) + 1
        self.idf = {}
        for token, df in df_counts.items():
            self.idf[token] = math.log((1 + num_docs) / (1 + df)) + 1.0

        # Build Document-Term Matrix (N x V)
        doc_matrix = np.zeros((num_docs, self.vocab_size), dtype=np.float32)
        for doc_idx, tokens in enumerate(doc_tokens_list):
            tf_counts = {}
            for token in tokens:
                tf_counts[token] = tf_counts.get(token, 0) + 1

            for token, count in tf_counts.items():
                if token in self.vocabulary:
                    v_idx = self.vocabulary[token]
                    # Sublinear TF scaling
                    tf_scaled = 1.0 + math.log(count)
                    doc_matrix[doc_idx, v_idx] = tf_scaled * self.idf[token]

        # L2 normalize document vectors for fast cosine similarity dot products
        norms = np.linalg.norm(doc_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        self.doc_vectors = doc_matrix / norms

    def query_to_vector(self, query):
        """Convert a user question into an L2-normalized vector in vocabulary space."""
        tokens = self.tokenize(query)
        if not tokens:
            return None

        q_vec = np.zeros(self.vocab_size, dtype=np.float32)
        tf_counts = {}
        for token in tokens:
            tf_counts[token] = tf_counts.get(token, 0) + 1

        for token, count in tf_counts.items():
            if token in self.vocabulary:
                v_idx = self.vocabulary[token]
                tf_scaled = 1.0 + math.log(count)
                q_vec[v_idx] = tf_scaled * self.idf[token]

        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm
        return q_vec

    def retrieve(self, query, top_k=3, min_similarity=0.12):
        """
        Step 1 & 2 of RAG: Retrieve top-k relevant knowledge chunks using
        Cosine Similarity on TF-IDF vectors + Hybrid keyword matching.
        """
        start_time = time.time()
        q_vec = self.query_to_vector(query)
        q_tokens = set(self.tokenize(query))

        if q_vec is None or np.all(q_vec == 0):
            # Query has no known keywords in vocab
            return {
                "results": [],
                "top_similarity": 0.0,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "query": query
            }

        # Vector dot products = Cosine Similarity
        cosine_scores = np.dot(self.doc_vectors, q_vec)

        # Hybrid keyword boosting for exact acronyms/tags
        hybrid_scores = []
        for idx, base_score in enumerate(cosine_scores):
            doc = self.documents[idx]
            tag_matches = sum(1 for tag in doc.get("tags", []) if tag in q_tokens or any(t in tag for t in q_tokens))
            title_tokens = set(self.tokenize(doc.get("title", "")))
            title_matches = len(title_tokens.intersection(q_tokens))
            
            # Weighted hybrid score
            boosted = float(base_score) + (tag_matches * 0.08) + (title_matches * 0.05)
            hybrid_scores.append((idx, boosted, float(base_score)))

        # Sort by boosted score descending
        hybrid_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score, cos_score in hybrid_scores[:top_k]:
            if score >= min_similarity or len(results) == 0:
                doc = self.documents[idx]
                results.append({
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "category": doc.get("category"),
                    "content": doc.get("content"),
                    "tags": doc.get("tags", []),
                    "similarity_score": round(score, 4),
                    "cosine_similarity": round(cos_score, 4)
                })

        latency = round((time.time() - start_time) * 1000, 2)
        top_sim = results[0]["similarity_score"] if results else 0.0

        return {
            "results": results,
            "top_similarity": top_sim,
            "latency_ms": latency,
            "query": query
        }

    def build_rag_prompt(self, query, retrieved_chunks):
        """
        Step 3 of RAG: Augment prompt with retrieved college facts and numbered citations.
        """
        context_blocks = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_blocks.append(
                f"[Source {i}: {chunk['title']} (Category: {chunk['category']})]\n{chunk['content']}"
            )
        context_str = "\n\n".join(context_blocks)

        prompt = f"""You are the official AI Academic Advisor for Apex Institute of Technology & Science (AITS).
Answer the user's question accurately using ONLY the verified college knowledge context provided below.
If the information is not contained in the context, politely state that the specific details are not available in the college records and suggest contacting the Admissions Office.

CONTEXT INFORMATION:
{context_str}

STUDENT QUESTION:
{query}

ANSWER (Provide a structured, helpful, professional response with direct facts and cite sources where relevant):
"""
        return prompt, context_str

    def synthesize_offline(self, query, retrieved_chunks):
        """
        High-quality built-in RAG synthesizer (100% offline, guaranteed zero failure).
        Extracts salient points, highlights data (fees, deadlines, packages), and formats markdown.
        """
        if not retrieved_chunks:
            return (
                "I couldn't find specific information regarding your question in our current college knowledge base. "
                "Please reach out to the **Central Admissions Office** at `+91 (080) 4567-8900` or email "
                "`admissions@apexinstitute.edu` for personalized assistance."
            )

        # Check for low confidence
        top_chunk = retrieved_chunks[0]
        if top_chunk["similarity_score"] < 0.15:
            return (
                f"I found some related information under **{top_chunk['title']}**, but it may not fully address your specific query:\n\n"
                f"> {top_chunk['content']}\n\n"
                f"For verified guidance, please contact `admissions@apexinstitute.edu`."
            )

        # Build structured response
        response_parts = []
        
        # Primary answer statement
        response_parts.append(f"Here is what our official records indicate regarding **{query.strip('?')}**:\n")

        for idx, chunk in enumerate(retrieved_chunks, 1):
            title = chunk["title"]
            category = chunk["category"]
            content = chunk["content"]

            # Highlight specific metrics like ₹, %, LPA, dates
            highlighted = content
            highlighted = re.sub(r"(₹[\d,]+(?:\s*(?:LPA|Lakhs?|per\s+\w+))?)", r"**\1**", highlighted)
            highlighted = re.sub(r"(\b\d{1,2}(?:\.\d+)?%)", r"**\1**", highlighted)
            highlighted = re.sub(r"(\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b)", r"**\1**", highlighted)

            # Break sentences into structured points if informative
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", highlighted) if s.strip()]
            
            response_parts.append(f"### 📌 {title} *({category})*")
            if len(sentences) > 1:
                for sent in sentences:
                    response_parts.append(f"- {sent}")
            else:
                response_parts.append(f"{sentences[0]}")
            response_parts.append("")

        response_parts.append("\n💡 *Need more assistance? Central Admissions Helpline: +91 (080) 4567-8900 | admissions@apexinstitute.edu*")
        return "\n".join(response_parts)

    def generate_with_gemini(self, prompt, api_key):
        """Call Gemini API via standard HTTP request (no third-party pip dependencies required)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 800
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        return None

    def generate_with_openai(self, prompt, api_key):
        """Call OpenAI API via standard HTTP request."""
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are the helpful AI Academic Advisor for Apex Institute."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 800
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        return None

    def query_rag(self, query, top_k=3):
        """
        Complete end-to-end RAG Execution:
        1. Retrieve top matching chunks
        2. Format augmented prompt
        3. Synthesize or generate answer
        4. Return answer + audit metadata for transparency
        """
        start_total = time.time()
        
        # 1. Retrieval
        retrieval_output = self.retrieve(query, top_k=top_k)
        retrieved_chunks = retrieval_output["results"]
        
        # 2. Augmentation
        prompt, context_str = self.build_rag_prompt(query, retrieved_chunks)

        # 3. Generation (Check for Gemini / OpenAI API keys, fallback to Offline Synthesizer)
        generator_backend = "Local Knowledge Synthesizer (Built-in RAG)"
        answer = None
        
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if gemini_key:
            try:
                gen_text = self.generate_with_gemini(prompt, gemini_key)
                if gen_text:
                    answer = gen_text
                    generator_backend = "Gemini 1.5 Flash (via Google AI API)"
            except Exception as e:
                # Silently fallback to synthesizer
                pass

        if not answer and openai_key:
            try:
                gen_text = self.generate_with_openai(prompt, openai_key)
                if gen_text:
                    answer = gen_text
                    generator_backend = "OpenAI GPT-3.5 (via OpenAI API)"
            except Exception as e:
                pass

        if not answer:
            answer = self.synthesize_offline(query, retrieved_chunks)

        total_latency = round((time.time() - start_total) * 1000, 2)

        return {
            "query": query,
            "answer": answer,
            "backend": generator_backend,
            "retrieval_latency_ms": retrieval_output["latency_ms"],
            "total_latency_ms": total_latency,
            "retrieved_chunks": retrieved_chunks,
            "sources": [
                {
                    "title": c["title"],
                    "category": c["category"],
                    "similarity": c["similarity_score"]
                }
                for c in retrieved_chunks
            ],
            "rag_prompt": prompt
        }
