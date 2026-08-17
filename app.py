import os
import shutil
import json
from flask import Flask, render_template, request, jsonify, session, Response
from werkzeug.utils import secure_filename
import rag_engine
import db_manager

app = Flask(__name__)

# Configure Flask Session Secret Key
app.secret_key = os.getenv("SECRET_KEY", "apex_motors_secret_rag_key_2026")

# Configure Upload Folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload to 16MB

ALLOWED_EXTENSIONS = {'txt', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize Database tables and Seed Admin accounts on startup
db_initialized = db_manager.init_db()
if not db_initialized:
    print("[WARNING] Database initialization failed. Please make sure MySQL server is running!")

@app.route('/')
def home():
    """Renders the single-page application UI."""
    return render_template('index.html')

# --- Authentication APIs ---

@app.route('/register', methods=['POST'])
def register():
    """Registers a new regular user account."""
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "Email and Password are required."}), 400
        
    email = data['email'].strip()
    password = data['password']
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and Password cannot be empty."}), 400
        
    success, message = db_manager.register_user(email, password)
    if success:
        return jsonify({"success": True, "message": message}), 201
    else:
        return jsonify({"success": False, "message": message}), 400

@app.route('/login', methods=['POST'])
def login():
    """Logs in user and starts a session."""
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"success": False, "message": "Email and Password are required."}), 400
        
    email = data['email'].strip()
    password = data['password']
    
    user = db_manager.verify_user(email, password)
    if user:
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['role'] = user['role']
        return jsonify({
            "success": True, 
            "message": "Logged in successfully.",
            "user": {
                "email": user['email'],
                "role": user['role']
            }
        }), 200
    else:
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

@app.route('/logout', methods=['POST'])
def logout():
    """Clears the user session."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200

@app.route('/session', methods=['GET'])
def check_session():
    """Returns the current user session details."""
    if 'user_id' in session:
        return jsonify({
            "logged_in": True,
            "user": {
                "email": session['email'],
                "role": session['role']
            }
        }), 200
    return jsonify({"logged_in": False}), 200

# --- Chat History APIs ---

@app.route('/history', methods=['GET'])
def chat_history():
    """Returns all saved chat history for the logged-in user."""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    history = db_manager.get_chat_history(session['user_id'])
    return jsonify({"success": True, "history": history}), 200

@app.route('/clear-history', methods=['POST'])
def clear_history():
    """Deletes all chat messages for the logged-in user."""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    success = db_manager.clear_chat_history(session['user_id'])
    if success:
        return jsonify({"success": True, "message": "Chat history cleared."}), 200
    return jsonify({"success": False, "message": "Failed to clear history."}), 500

# --- RAG Bot & Ingestion APIs ---

@app.route('/query', methods=['POST'])
def query_bot():
    """Queries the RAG chatbot, feeds chat memory, and streams the response via SSE."""
    if 'user_id' not in session:
        return jsonify({"answer": "Please log in to chat with the bot.", "context_used": [], "status": "error"}), 401
        
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"answer": "Query is missing from the request.", "context_used": [], "status": "error"}), 400
        
    user_query = data['query'].strip()
    if not user_query:
        return jsonify({"answer": "Query cannot be empty.", "context_used": [], "status": "error"}), 400
        
    try:
        # 1. Fetch the last 5 messages for this user for conversational context/memory
        chat_history = db_manager.get_last_n_messages(session['user_id'], n=5)
        
        # 2. Query RAG Engine in stream mode
        result = rag_engine.query_rag(user_query, chat_history=chat_history, stream=True)
        
        if "stream" not in result:
            return jsonify({
                "answer": result.get("answer", "An error occurred in generating answer."),
                "context_used": [],
                "status": "error"
            }), 500
            
        response_stream = result["stream"]
        sources = result["context_used"]
        
        # 3. Stream generator function
        def generate():
            full_answer = ""
            # Yield sources metadata first
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            
            try:
                for chunk in response_stream:
                    text_chunk = chunk.text
                    full_answer += text_chunk
                    yield f"data: {json.dumps({'text': text_chunk})}\n\n"
            except Exception as stream_err:
                print(f"Error during stream generation: {stream_err}")
                yield f"data: {json.dumps({'error': str(stream_err)})}\n\n"
                return
                
            # Save query and full response to MySQL database on success
            db_manager.save_chat_message(session['user_id'], 'user', user_query)
            db_manager.save_chat_message(session['user_id'], 'bot', full_answer)
            
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({
            "answer": f"Error initiating query stream: {str(e)}",
            "context_used": [],
            "status": "error"
        }), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles PDF and TXT file uploads. RESTRICTED to admins only."""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Access denied. Admin role required."}), 403
        
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part in the request."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file."}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(file_path)
            result = rag_engine.ingest_document(file_path, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 500
                
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
            
    return jsonify({"success": False, "message": "Invalid file format. Only PDF and TXT files are allowed."}), 400

@app.route('/documents', methods=['GET'])
def list_documents():
    """Lists all ingested documents in the knowledge base. RESTRICTED to admins only."""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Access denied. Admin role required."}), 403
        
    try:
        docs = rag_engine.list_ingested_documents()
        return jsonify({"success": True, "documents": docs}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error listing files: {str(e)}"}), 500

@app.route('/delete-document', methods=['POST'])
def delete_document():
    """Deletes a specific document from the knowledge base. RESTRICTED to admins only."""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"success": False, "message": "Access denied. Admin role required."}), 403
        
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({"success": False, "message": "Missing 'filename' parameter in request."}), 400
        
    filename = data['filename']
    try:
        success = rag_engine.delete_document_from_db(filename)
        if success:
            return jsonify({"success": True, "message": f"Successfully deleted '{filename}' from database."}), 200
        else:
            return jsonify({"success": False, "message": f"Failed to delete '{filename}'."}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Error during deletion: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
