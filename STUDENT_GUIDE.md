# 🎓 Student & Developer Guide: College Information Chatbot using RAG

Welcome to the **College Information Chatbot using RAG (Retrieval-Augmented Generation)** project built with Python and Flask.

---

## 📖 Table of Contents
1. [What is RAG and Why Do We Need It?](#1-what-is-rag-and-why-do-we-need-it)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Under the Hood: Step-by-Step RAG Mechanics](#3-under-the-hood-step-by-step-rag-mechanics)
4. [Project Structure](#4-project-structure)
5. [Running the Project Locally](#5-running-the-project-locally)
6. [Testing the REST API](#6-testing-the-rest-api)
7. [How to Extend with Custom PDFs or External LLMs](#7-how-to-extend-with-custom-pdfs-or-external-llms)
8. [Viva Voce & Lab Exam Questions (Q&A)](#8-viva-voce--lab-exam-questions-qa)

---

## 1. What is RAG and Why Do We Need It?

### The Problem with Standalone LLMs
Standard Large Language Models (like GPT-4, LLaMA, or Claude) are trained on general internet text up to a fixed cutoff date:
1. **No Access to Private Data:** They do not know your college's specific 2026 fee structure, hostel charges, cutoff ranks, or scholarship rules.
2. **Hallucinations:** When asked specific institutional questions, standard LLMs often guess plausible-sounding but completely fabricated numbers and dates.
3. **Expensive Fine-Tuning:** Retraining or fine-tuning an LLM every time college fees or deadlines change is slow, costly, and complex.

### The RAG Solution
**Retrieval-Augmented Generation (RAG)** splits the job into two distinct stages:
1. **Retrieval (The Librarian):** Search your institutional database to find the exact paragraphs that contain the answer.
2. **Generation (The Writer):** Feed those retrieved paragraphs into the model with an instruction: *"Answer the student's question using ONLY these verified documents."*

Result: **100% factual accuracy, verifiable citations, and zero hallucinations.**

---

## 2. High-Level Architecture

```
User Query: "What is the B.Tech CSE fee and hostel cost?"
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ 1. Vector Transformation                               │
│    Tokenize -> Sublinear TF -> Multiply by IDF -> L2   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Cosine Similarity Vector Retrieval (NumPy)          │
│    Dot product with Document Vectors + Tag Boost       │
│    Matches: [Chunk #7: B.Tech Fees, Chunk #8: Hostels] │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Prompt Augmentation                                 │
│    Inject retrieved chunks into System Context Window  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Generation & Synthesis                              │
│    Synthesizer (Offline) OR Gemini/OpenAI API          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
Final Answer + Sources + Similarity Scores (e.g., 88% Match)
```

---

## 3. Under the Hood: Step-by-Step RAG Mechanics

### Step 1: Document Chunking
Institutional data in `data/college_knowledge_base.json` is organized into focused, atomic passages. Each chunk includes:
- `id`: Unique identifier (e.g., `fees_btech_01`).
- `category`: Domain area (`Admissions`, `Fees`, `Placements`, `Campus`).
- `title`: Topic heading.
- `content`: Factual institutional text.
- `tags`: Key searchable acronyms (`cse`, `jee`, `lpa`, `tuition`).

### Step 2: Vector Space Modeling (TF-IDF & Embeddings)
To calculate mathematical similarity between a question and documents:

1. **Term Frequency (TF) with Sublinear Scaling:**
   $$\text{tf}(t, d) = 1 + \ln(\text{count}(t, d)) \quad \text{if count} > 0$$
   *Why sublinear scaling?* A word appearing 10 times in a chunk is not 10 times as important as a word appearing once; logarithmic dampening prevents repetitive words from dominating.

2. **Inverse Document Frequency (IDF) with Smoothing:**
   $$\text{idf}(t) = \ln\left(\frac{1 + N}{1 + \text{df}(t)}\right) + 1.0$$
   Gives higher weight to unique words like *"hostel"* or *"scholarship"* while penalizing ubiquitous words.

3. **L2 Normalization:**
   Each document vector $\mathbf{v}$ is divided by its Euclidean norm $\|\mathbf{v}\|_2$:
   $$\hat{\mathbf{v}} = \frac{\mathbf{v}}{\|\mathbf{v}\|_2}$$
   When vectors are unit normalized, **Cosine Similarity equals the simple dot product**:
   $$\cos(\theta) = \hat{\mathbf{q}} \cdot \hat{\mathbf{d}}$$

### Step 3: Top-K Vector Retrieval + Hybrid Keyword Boost
The retriever computes dot products across all document vectors in parallel using NumPy. In addition, exact keyword/acronym matches in tags receive a small bonus score ($+0.08$) to ensure technical terms like *"CSE"*, *"LPA"*, *"JEE"*, *"NIRF"* achieve top rank.

### Step 4: Prompt Augmentation & Synthesis
The top-$K$ matching chunks are formatted into an augmented prompt:
```
You are the official AI Academic Advisor for Apex Institute.
Answer the user's question accurately using ONLY the verified context below:

[Source 1: B.Tech and BCA Tuition Fee Structure]
Tuition fee for B.Tech in Computer Science is ₹1,10,000 per semester...

STUDENT QUESTION:
What is the fee for CSE?
```
The generator formats the response, highlights key metrics (fees, percentages, dates), and cites the verified sources.

---

## 4. Project Structure

```
part6/
├── app.py                         # Flask web application & REST API routes
├── rag_engine.py                  # Core RAG Engine (Vector space, retrieval, generator)
├── STUDENT_GUIDE.md               # Detailed student manual & viva questions
├── requirements.txt               # Dependencies list (Flask, numpy)
├── data/
│   └── college_knowledge_base.json # Official institutional documents
├── static/
│   ├── css/
│   │   └── style.css              # Modern dark-mode glassmorphic styling
│   └── js/
│       └── main.js                # Chat logic, RAG inspector toggle, modals
└── templates/
    └── index.html                 # Main chatbot webpage
```

---

## 5. Running the Project Locally

### Prerequisites
- Python 3.9+ installed.
- Terminal / command line.

### Steps:

1. **Activate the Virtual Environment:**
   ```bash
   cd /Users/akil/Desktop/part6
   source venv/bin/activate
   ```

2. **Start the Flask Application:**
   ```bash
   python app.py
   ```

3. **Open in Browser:**
   Visit: **[http://127.0.0.1:5001](http://127.0.0.1:5001)**

---

## 6. Testing the REST API

You can query the RAG engine programmatically using `curl` or Postman:

### Query the Chatbot Endpoint:
```bash
curl -X POST http://127.0.0.1:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the highest placement package?", "top_k": 3}'
```

**Sample JSON Output:**
```json
{
  "status": "success",
  "query": "What is the highest placement package?",
  "backend": "Local Knowledge Synthesizer (Built-in RAG)",
  "retrieval_latency_ms": 1.45,
  "total_latency_ms": 3.82,
  "sources": [
    {
      "title": "Placement Statistics and Top Recruiters",
      "category": "Placements & Internships",
      "similarity": 0.8076
    }
  ],
  "answer": "Here is what our official records indicate regarding What is the highest placement package..."
}
```

### View Knowledge Topics:
```bash
curl http://127.0.0.1:5001/api/topics
```

---

## 7. How to Extend with Custom PDFs or External LLMs

### A. Connecting External LLMs (Gemini / OpenAI)
The project works **100% offline out-of-the-box**. If you wish to enable Google Gemini or OpenAI:
```bash
# For Gemini
export GEMINI_API_KEY="your-gemini-api-key"

# OR For OpenAI
export OPENAI_API_KEY="your-openai-key"

python app.py
```
`rag_engine.py` automatically detects the key and switches from local synthesizer to the LLM with zero extra configuration.

### B. Adding Your Own College PDF Documents
To ingest real college prospectuses or PDF brochures:
1. Install `pypdf`: `pip install pypdf`
2. Extract text pages and append to `data/college_knowledge_base.json`.
3. Click **"Re-index Documents"** in the web interface (or call `/api/reload`) to rebuild the vector matrix in memory.

---

## 8. Viva Voce & Lab Exam Questions (Q&A)

**Q1: What does RAG stand for, and what are its two core phases?**
> **Answer:** RAG stands for Retrieval-Augmented Generation. The two phases are:
> 1. *Retrieval:* Searching an external document database for passages relevant to the query.
> 2. *Generation:* Feeding the retrieved context to an LLM/generator to formulate a coherent answer grounded in the sources.

**Q2: What is the difference between Fine-Tuning and RAG?**
> **Answer:** 
> - *Fine-tuning* updates the model weights with new training data. It is expensive, prone to hallucinations, and hard to update dynamically.
> - *RAG* keeps the model weights frozen and injects facts into the prompt during inference. Updating knowledge is as simple as updating a database file.

**Q3: Why do we use Cosine Similarity instead of Euclidean Distance?**
> **Answer:** Cosine similarity measures the angle between two vectors rather than their magnitude. In text processing, a longer document may repeat words more frequently (larger magnitude), but cosine similarity normalizes by vector length, ensuring relevance is not biased by passage length.

**Q4: What is the purpose of IDF (Inverse Document Frequency)?**
> **Answer:** IDF penalizes words that appear everywhere across all documents (like "the", "college", "student") and boosts distinctive query terms (like "scholarship", "hostel", "placement").

**Q5: What is Top-K Retrieval?**
> **Answer:** Top-$K$ refers to selecting the highest $K$ ranked documents based on similarity score (e.g. $K=3$). This prevents overflowing the context window while providing sufficient information.
