# 🧠 DocMind: Full-Stack RAG Application

DocMind is a Retrieval-Augmented Generation (RAG) application that allows users to upload documents (PDF/TXT) and chat with them using AI. It provides precise answers backed by specific source chunks extracted from the uploaded files.

## 🚀 Features

* **Document Ingestion:** Upload PDF and TXT files. The system automatically extracts text, chunks it, and generates vector embeddings.
* **Intelligent Q&A:** Ask conversational questions about your documents using Google's Gemini LLM.
* **Transparent Sourcing:** Every AI answer includes expandable source citations, showing the exact document chunk and similarity score used to generate the response.
* **Document Management:** View uploaded documents, check their chunk counts, and easily delete them from the database.

## 🛠️ Tech Stack

**Backend:**
* [FastAPI](https://fastapi.tiangolo.com/) - High-performance Python web framework
* [LangChain](https://python.langchain.com/) (v0.3) & [LangGraph](https://langchain-ai.github.io/langgraph/) - LLM orchestration and agent workflows
* [Google GenAI](https://ai.google.dev/) - Embeddings and LLM (Gemini)
* [Psycopg 3](https://www.psycopg.org/psycopg3/) - PostgreSQL database driver and connection pooling

**Frontend:**
* [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) - UI framework
* [Vite](https://vitejs.dev/) - Blazing fast frontend build tool
* [Axios](https://axios-http.com/) - HTTP client

**Database:**
* [Supabase](https://supabase.com/) (PostgreSQL) - Vector storage for document embeddings

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
* **Python 3.10+**
* **Node.js 18+** & **npm**
* A **Supabase** account with a PostgreSQL database configured
* A **Google Gemini API Key**

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/docmind-rag.git](https://github.com/YOUR_USERNAME/docmind-rag.git)
cd docmind-rag