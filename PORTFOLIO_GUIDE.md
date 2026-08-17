# Technical Portfolio Guide: Context-Aware MySQL RAG Chatbot

This project is a production-ready **Retrieval-Augmented Generation (RAG) Chatbot** built for business document querying. It features a local file parser, a text chunking engine, a persistent **MySQL database** for user credentials and conversation logging, and implements **Conversational Memory** using the Google Gemini API.

---

## 1. System Architecture

Below is the step-by-step data flow of the application:

```mermaid
flowchart TD
    %% Ingestion Pipeline
    subgraph Ingestion [Ingestion Pipeline (Admin Only)]
        A[Admin PDF / TXT File] --> B[Text Extractor]
        B --> C[Sliding-Window Chunker]
        C -->|Text Chunks| D[Gemini Embedding Generator]
        D -->|768-dim Vectors| E[(ChromaDB Vector Store)]
    end

    %% MySQL Auth & Chat Log
    subgraph UsersDatabase [MySQL DB (Auth & History)]
        M1[(MySQL Server)] -->|User Sessions| M2[Flask Session Cookie]
        M1 -->|Retrieve last 5 turns| M3[Context Memory Loader]
        M4[User Chat Prompts] -->|Saved to database| M1
    end

    %% Inference Pipeline
    subgraph Inference [Inference Pipeline (All Users)]
        F[User Question] --> G[Gemini Query Embedder]
        G -->|Query Vector| H[Semantic Similarity Search]
        E -->|Search database| H
        H -->|Top K matching chunks| I[Context Augmentor]
        M3 -->|Formatted Chat History| I
        F --> I
        I -->|System Instruction + RAG Context + Memory + Question| J[Gemini 3.5 Flash LLM]
        J -->|Context-Grounded Answer| K[Chatbot UI Bubble]
    end
    
    style Ingestion fill:#111b27,stroke:#3b82f6,stroke-width:2px;
    style UsersDatabase fill:#221515,stroke:#f59e0b,stroke-width:2px;
    style Inference fill:#0b1b17,stroke:#10b981,stroke-width:2px;
```

---

## 2. Core Libraries & Database Technologies

1. **Flask (Python Micro-framework)**: Serves the REST API and manages authentication sessions using secure cookies signed with a cryptographic secret key (`app.secret_key`).
2. **ChromaDB (Vector DB)**: A local vector store that persists document text chunks and vector embeddings. It calculates cosine similarity scores during query search.
3. **MySQL Database**: Manages state, user accounts, and persists chat history logs.
   - **`mysql-connector-python`**: The official, pure-python MySQL client used to run queries, fetch logs, and manage connections.
4. **google-generativeai (Google GenAI SDK)**: Coordinates with Google's Gemini models in the cloud:
   - **Embedding Model (`gemini-embedding-2`)**: Generates vector embeddings representing semantic meanings for document chunks and user queries.
   - **LLM (`gemini-3.5-flash`)**: Formulates replies using augmented instructions, database search context, and conversation memory.
5. **pypdf**: Parses text from PDFs.
6. **werkzeug.security**: Handles safe authentication by hashing passwords with salt before database storage and verifying hashes on login (`check_password_hash`).

---

## 3. Core Algorithms & Logic Loops

### A. Session-Based Authentication & Registration Policies
To fulfill the requirement *"Only 2 admin accounts, multiple user accounts"*:
1. **Admins are Pre-seeded**: On database initialization, `db_manager.py` seeds exactly two accounts with the role `'admin'` (`admin1@company.com` and `admin2@company.com`).
2. **Register Restriction Loop**: The registration endpoint `/register` blocks any registrations containing `"admin"` in the email to prevent unauthorized privilege escalation:
   ```python
   if "admin" in email.lower():
       return False, "Cannot register administrative accounts."
   ```
3. **Admin Page Protection**: Flask endpoints checking directories `/upload` or `/delete-document` enforce strict role verification:
   ```python
   if 'user_id' not in session or session.get('role') != 'admin':
       return jsonify({"success": False, "message": "Access denied."}), 403
   ```

### B. SQLite vs MySQL Connection Manager
We connect to MySQL using environment variables in `.env`. On app start, we initialize database structures:
```python
def init_db():
    conn = get_mysql_connection(include_db=False)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS " + MYSQL_DATABASE)
    ...
```
This ensures that the developer doesn't need to manually configure the schema in MySQL Workbench; the Python code configures its own table layout dynamically on runtime start.

### C. Sliding Window Text Chunking
Splits long documents into smaller overlapping sections to avoid token overflows and preserve semantic flow:
```python
def chunk_text(text, chunk_size=800, overlap=150):
    chunks = []
    text = re.sub(r'\s+', ' ', text)
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
```

### D. Conversational Memory Loop (Last 5 Chats)
To allow the chatbot to remember previous conversation turns, the system queries the MySQL database for the last 5 messages:
```python
cursor.execute(
    "SELECT sender, message FROM chat_messages WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
    (user_id, n)
)
history = cursor.fetchall()
history.reverse() # Arrange in ASC order (oldest first)
```
In `rag_engine.py`, these messages are structured into a transcript:
```python
history_context = ""
if chat_history:
    formatted_history = []
    for sender, msg in chat_history:
        role_name = "User" if sender == "user" else "Assistant"
        formatted_history.append(f"{role_name}: {msg}")
    history_context = "\nPrevious Conversation History:\n" + "\n".join(formatted_history) + "\n\n"
```
This transcript is prepended directly to the Gemini LLM prompt. For instance:
* **Turn 1 (User)**: *"How much does the Suzuki Swift Front Bumper cost?"*
* **Turn 1 (Bot)**: *"The retail price is $185."*
* **Turn 2 (User)**: *"How long does it take to install it?"*
* **RAG Context**: *Suzuki Swift Front Bumper installation time is 1.5 hours.*
* **Memory Context**: *User: Swift Bumper price? Assistant: $185.*
* **LLM Grounding**: The LLM successfully understands that *"it"* in Turn 2 refers to the Suzuki Swift Front Bumper, returning: *"The installation time is 1.5 hours."*

---

## 4. Run and Test the MySQL Integration

### Step 1: Set up MySQL Environment
1. Ensure your MySQL server (such as XAMPP, WampServer, or a local MySQL server) is running.
2. Edit the [`.env`](file:///d:/Users/Computer%20World/Desktop/RAG%20Chatbot/.env) file to configure your server password:
   ```env
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=your_mysql_password_here
   MYSQL_DATABASE=cog_rag_db
   ```

### Step 2: Start the server and test Auth
1. In your terminal, launch the application:
   ```bash
   python app.py
   ```
2. Open `http://localhost:5000` in your web browser. You will be greeted by the **Sign In** dashboard panel.
3. Try logging in as admin:
   - Email: `admin1@company.com`
   - Password: `admin123`
   - Verify that both **User Chatroom** and **Knowledge Ingestion** views are visible.
4. Go to **Knowledge Ingestion** and drag-and-drop the file [`car_support_knowledge.txt`](file:///d:/Users/Computer%20World/Desktop/RAG%20Chatbot/car_support_knowledge.txt) (located in your project root). Verify ingestion matches.
5. Log out, then select the **Sign Up** tab to register a new user:
   - Create a test account (e.g., `user2@company.com` / `user123`).
   - Log in and verify that the **Knowledge Ingestion** view is hidden from the sidebar menu.

### Step 3: Test Chat Memory
1. Ask the chatbot: *"What is the retail price of the Suzuki swift front bumper?"*
2. It should reply: *"The retail price is $185."*
3. Now test the conversation memory by asking: *"How long does it take to install?"* (without mentioning the bumper name).
4. Verify that it recalls the context and replies: *"It takes 1.5 hours to install the Suzuki Swift front bumper."*
5. Refresh the browser page. Notice that your entire message history is loaded automatically from the MySQL database!
