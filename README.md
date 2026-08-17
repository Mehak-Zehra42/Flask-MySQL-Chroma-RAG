# CognitiveRAG: Context-Aware Enterprise Knowledge Hub

CognitiveRAG is a production-ready, context-aware **Retrieval-Augmented Generation (RAG)** chatbot designed to answer questions strictly grounded in private corporate documents (PDFs/TXT). It separates controls between administrators and regular users, incorporates conversation memory (last 5 turns), and features real-time, low-latency streaming responses.

---

## 🚀 Key Features

* **Context-Aware Question Answering (RAG):** Searches local document databases to construct responses grounded in factual data rather than relying on general LLM knowledge.
* **Low-Latency Streaming:** Powered by **Server-Sent Events (SSE)** and JavaScript's `ReadableStream` reader to deliver token-by-token text generation in under 200ms.
* **Conversational Memory:** Persists the last 5 turns of conversation to MySQL, enabling the model to handle follow-up questions and pronouns (e.g., "how much is it?") naturally.
* **Role-Based Access Control (RBAC):** Restricts access to administrative endpoints (uploading and deleting files) strictly to verified Admin accounts, while regular users have access only to the chat window.
* **MySQL Persistence:** Keeps a secure and structured history of user accounts and chat messages that automatically reload upon page refresh.
* **Local Vector Store:** Uses **ChromaDB** fully embedded in the Python runtime to store document chunks and embeddings.

---

## 🛠️ Tech Stack & Architecture

* **Backend:** Python (Flask)
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5
* **Vector Database:** ChromaDB
* **Relational Database:** MySQL
* **LLM & Embeddings:** Google Gemini API (`gemini-3.5-flash` & `gemini-embedding-2`)
* **Document Processing:** PyPDF

### System Architecture Flow:
```
[Admin uploads PDF/TXT] ──> [PyPDF Parser] ──> [Sliding-Window Chunker]
                                                      │
                                                      ▼
[ChromaDB Vector Store] <── [gemini-embedding-2] <── [Text Chunks]

========================================================================

[User Question] ──> [Retrieve last 5 Chats from MySQL] ──> [Query Embedding]
                                                                │
                                                                ▼
[Real-Time Token Stream] <── [Gemini 3.5 Flash] <── [Cosine-Similarity Search]
```

---

## ⚙️ Installation & Local Setup

### Prerequisites
1. **Python 3.10+** installed on your system.
2. **MySQL Server** (via XAMPP, WampServer, or standalone) running locally.
3. A free **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/).

### 1. Clone the repository
```bash
git clone git@github.com:Mehak-Zehra42/Flask-MySQL-Chroma-RAG.git
cd Flask-MySQL-Chroma-RAG
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure the Environment
Create a `.env` file in the root folder and add your variables:
```env
# Google Gemini API Config
GEMINI_API_KEY=your_google_gemini_api_key_here
FLASK_ENV=development
PORT=5001

# MySQL Configuration Settings
MYSQL_HOST=127.0.0.1
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=cog_rag_db
```
*(Note: Keep `MYSQL_PASSWORD` blank if you are using XAMPP default config).*

### 4. Run the Application
1. Start your local MySQL server (e.g. click "Start" MySQL in XAMPP control panel).
2. Execute the Flask app:
   ```bash
   python app.py
   ```
3. Open your browser and navigate to:
   👉 **`http://localhost:5001`**

---

## 🔑 Seeded Demo Accounts

You can log in directly with these seeded credentials:

* **Admin 1:** `admin1@company.com` | `admin123`
* **Admin 2:** `admin2@company.com` | `admin456`
* **User signup:** Go to the "Sign Up" tab in the login form to register unlimited regular user accounts.

---

## 📁 Project Structure

* `app.py`: Flask web controller hosting server configurations, session management, and routing.
* `rag_engine.py`: Manages PDF text parsing, sliding window text splitting, ChromaDB indexing, and Gemini integration.
* `db_manager.py`: Handles MySQL database setup, pre-seeding accounts, user registration, and query history storage/retrieval.
* `verify_rag.py`: Automation script to programmatically test DB connection, API embeddings, and retrieval accuracy.
* `templates/index.html`: Responsive Bootstrap 5 glassmorphic single-page user interface.
* `static/css/style.css`: Carbon-theme styling definitions.
* `static/js/app.js`: Connects API actions, handles drag-and-drop uploads, parses SSE chunks, and updates message templates.
