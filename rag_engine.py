import os
import re
import pypdf
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Google Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "your_api_key_here":
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY is not set or is still the default placeholder.")

# Initialize ChromaDB Local Persistent Client
# This creates a folder named 'chroma_db' in the project directory to save data permanently.
chroma_client = chromadb.PersistentClient(path="chroma_db")

# Create or get a collection for our document chunks
# We'll handle embedding generation ourselves via Gemini API
collection = chroma_client.get_or_create_collection(
    name="company_knowledge_base",
    metadata={"hnsw:space": "cosine"}  # Use cosine similarity for match scoring
)

def extract_text_from_file(file_path):
    """
    Extracts text from a given file path. Supports PDF and TXT files.
    """
    _, ext = os.path.splitext(file_path.lower())
    text = ""
    
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            
    elif ext == ".pdf":
        try:
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            text = "\n".join(pages_text)
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            raise e
            
    else:
        raise ValueError("Unsupported file format. Please upload .txt or .pdf files.")
        
    return text.strip()

def chunk_text(text, chunk_size=800, overlap=150):
    """
    Splits text into smaller overlapping chunks to preserve local context.
    Loops through the text using a sliding window.
    """
    chunks = []
    if not text:
        return chunks
        
    # Replace multiple whitespaces/newlines with single spaces/newlines
    text = re.sub(r'\s+', ' ', text)
    
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        # Shift start forward by chunk_size - overlap
        start += chunk_size - overlap
        if start >= text_len or end == text_len:
            break
            
    return chunks

def get_gemini_embedding(text_content, is_query=False):
    """
    Calls Google Gemini API to generate vector embeddings.
    Uses 'text-embedding-004'.
    - task_type='retrieval_document' for chunks to be saved.
    - task_type='retrieval_query' for user search queries.
    """
    if not api_key or api_key == "your_api_key_here":
        raise ValueError("API Key is missing. Please add your GEMINI_API_KEY in the .env file.")
        
    task_type = "retrieval_query" if is_query else "retrieval_document"
    
    try:
        response = genai.embed_content(
            model="models/gemini-embedding-2",
            content=text_content,
            task_type=task_type
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding via Gemini API: {e}")
        raise e

def ingest_document(file_path, filename):
    """
    Processes a file: extracts text, chunks it, generates embeddings,
    and stores them in ChromaDB collection.
    """
    # 1. Extract raw text
    raw_text = extract_text_from_file(file_path)
    if not raw_text:
        return {"success": False, "message": "No readable text found in document."}
        
    # 2. Chunk text
    chunks = chunk_text(raw_text)
    if not chunks:
        return {"success": False, "message": "Document was too short or empty."}
        
    # 3. Create unique IDs, metadata, and embeddings for each chunk
    ids = []
    embeddings = []
    metadatas = []
    documents = []
    
    for i, chunk in enumerate(chunks):
        chunk_id = f"{filename}_chunk_{i}"
        
        # Call Gemini API to embed this chunk
        embedding = get_gemini_embedding(chunk, is_query=False)
        
        ids.append(chunk_id)
        embeddings.append(embedding)
        metadatas.append({"filename": filename, "chunk_index": i})
        documents.append(chunk)
        
    # 4. Upsert into ChromaDB
    # If the file was uploaded before, we want to overwrite/update it, so we delete older chunks first
    delete_document_from_db(filename)
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents
    )
    
    return {
        "success": True, 
        "chunks_count": len(chunks), 
        "message": f"Successfully ingested {filename} ({len(chunks)} chunks)."
    }

def delete_document_from_db(filename):
    """
    Removes all chunks associated with a filename from ChromaDB.
    """
    try:
        collection.delete(where={"filename": filename})
        return True
    except Exception as e:
        print(f"Error deleting {filename} from DB: {e}")
        return False

def list_ingested_documents():
    """
    Retrieves all metadata from ChromaDB and returns a set of unique filenames.
    """
    try:
        results = collection.get(include=["metadatas"])
        if not results or not results['metadatas']:
            return []
            
        filenames = set()
        for meta in results['metadatas']:
            if meta and 'filename' in meta:
                filenames.add(meta['filename'])
                
        return list(filenames)
    except Exception as e:
        print(f"Error listing documents: {e}")
        return []

def query_rag(user_query, chat_history=None, top_k=4, stream=False):
    """
    Performs semantic search on ChromaDB using query embedding,
    then uses Gemini LLM to answer the question using matching chunks as context.
    Also incorporates chat_history (memory of last N turns).
    Supports streaming response if stream=True.
    """
    # Verify API key is available
    if not api_key or api_key == "your_api_key_here":
        return {
            "answer": "API Key is missing or invalid. Please check your `.env` file configuration.",
            "context_used": [],
            "status": "error"
        }
        
    # Format chat history context
    history_context = ""
    if chat_history:
        formatted_history = []
        for sender, msg in chat_history:
            role_name = "User" if sender == "user" else "Assistant"
            formatted_history.append(f"{role_name}: {msg}")
        history_context = "\nPrevious Conversation History:\n" + "\n".join(formatted_history) + "\n\n"
        
    # Check if we have any documents in our DB
    doc_count = collection.count()
    
    # If no documents are uploaded, we can answer using general Gemini knowledge
    # but we should let the user know.
    if doc_count == 0:
        try:
            model = genai.GenerativeModel('gemini-3.5-flash')
            prompt = (
                f"System: You are a helpful assistant. The business database is empty.\n"
                f"{history_context}"
                f"User Question: {user_query}\n"
                f"Answer: Answer the question politely and inform the user that no business documents have been uploaded to the database yet, so you are answering from general knowledge."
            )
            if stream:
                response_stream = model.generate_content(prompt, stream=True)
                return {
                    "stream": response_stream,
                    "context_used": [],
                    "status": "no_context"
                }
            response = model.generate_content(prompt)
            return {
                "answer": response.text,
                "context_used": [],
                "status": "no_context"
            }
        except Exception as e:
            return {
                "answer": f"Error calling Gemini API: {str(e)}",
                "context_used": [],
                "status": "error"
            }
            
    # 1. Embed query
    try:
        query_embedding = get_gemini_embedding(user_query, is_query=True)
    except Exception as e:
        return {
            "answer": f"Error embedding query: {str(e)}",
            "context_used": [],
            "status": "error"
        }
        
    # 2. Query vector store
    try:
        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
    except Exception as e:
        return {
            "answer": f"Error querying database: {str(e)}",
            "context_used": [],
            "status": "error"
        }
        
    # Extract matching chunks and metadata
    contexts = []
    sources = []
    
    if search_results and search_results['documents'] and len(search_results['documents'][0]) > 0:
        for i in range(len(search_results['documents'][0])):
            doc_text = search_results['documents'][0][i]
            meta = search_results['metadatas'][0][i]
            dist = search_results['distances'][0][i]
            
            contexts.append(doc_text)
            sources.append({
                "filename": meta['filename'],
                "chunk": meta['chunk_index'],
                "distance": float(dist)
            })
            
    # 3. Construct the Augmented Prompt
    if contexts:
        context_str = "\n\n---\n\n".join(contexts)
        system_instruction = (
            "You are a helpful, professional, and accurate AI Knowledge Assistant for a company. "
            "Your main goal is to answer the user's questions based strictly on the provided 'Context' below. "
            "Do not make up facts. If the answer cannot be found in the Context, say: "
            "'I'm sorry, but I couldn't find that information in the uploaded company documents.' "
            "Keep your answers clear, professional, and well-structured. "
            "Provide details if present in the context."
        )
        
        prompt = f"""
System Instructions: {system_instruction}

Context:
{context_str}
{history_context}
User Question: {user_query}

Answer:
"""
    else:
        # Fallback if query returns nothing
        prompt = f"System Instructions: Politely mention that no specific context was matched in the knowledge database.\n{history_context}\nUser Question: {user_query}\nAnswer:"
        sources = []
        
    # 4. Generate Answer using Gemini LLM
    try:
        model = genai.GenerativeModel(
            model_name='gemini-3.5-flash',
            generation_config={"temperature": 0.3} # Low temperature for factual, consistent answers
        )
        if stream:
            response_stream = model.generate_content(prompt, stream=True)
            return {
                "stream": response_stream,
                "context_used": sources,
                "status": "success" if sources else "no_context"
            }
            
        response = model.generate_content(prompt)
        return {
            "answer": response.text,
            "context_used": sources,
            "status": "success" if sources else "no_context"
        }
    except Exception as e:
        return {
            "answer": f"Error generating answer via Gemini: {str(e)}",
            "context_used": sources,
            "status": "error"
        }
