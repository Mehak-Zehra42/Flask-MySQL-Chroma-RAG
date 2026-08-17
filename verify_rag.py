import os
import time
import rag_engine

def run_verification():
    print("=" * 60)
    print("COGNITIVERAG CORE ENGINE VERIFICATION SCRIPT")
    print("=" * 60)
    
    # 1. Check API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("[ERROR] GEMINI_API_KEY is not set in the .env file!")
        print("Please open the '.env' file and replace 'your_api_key_here' with your Google AI Studio API key.")
        print("Verification aborted.")
        return
        
    print("[INFO] Google Gemini API Key detected.")
    
    # 2. Create a temporary document with secret test data
    temp_filename = "verification_temp_doc.txt"
    test_content = (
        "CognitiveRAG System Verification Manual:\n"
        "1. The emergency warehouse gate code is 9876-ALPHA.\n"
        "2. The emergency contact person is Director Emily Stone (Phone: 555-0192).\n"
        "3. Standard operational delivery time for Suzuki spare parts is 3 business days.\n"
    )
    
    print(f"[INFO] Creating temporary test file: {temp_filename}...")
    with open(temp_filename, "w", encoding="utf-8") as f:
        f.write(test_content)
        
    try:
        # 3. Ingest document into ChromaDB
        print("[INFO] Ingesting document into local ChromaDB...")
        ingest_result = rag_engine.ingest_document(temp_filename, temp_filename)
        
        if not ingest_result["success"]:
            print(f"[ERROR] Document ingestion failed: {ingest_result['message']}")
            return
            
        print(f"[SUCCESS] Ingested document successfully! {ingest_result['message']}")
        
        # 4. Perform search and QA
        query_text = "Who is the emergency contact person and what is the gate code?"
        print(f"\n[INFO] Querying Chatbot: '{query_text}'...")
        print("[INFO] Waiting for vector database search and Gemini LLM grounding...")
        
        start_time = time.time()
        response = rag_engine.query_rag(query_text)
        duration = time.time() - start_time
        
        print("-" * 60)
        print("CHATBOT RESPONSE:")
        print(response["answer"])
        print("-" * 60)
        print(f"Response Time: {duration:.2f} seconds")
        print(f"Sources Used: {response['context_used']}")
        print("-" * 60)
        
        # 5. Validate output correctness
        answer_text = response["answer"].lower()
        if "emily stone" in answer_text and "9876-alpha" in answer_text:
            print("\n[VERIFICATION STATUS: SUCCESS]")
            print("The RAG engine successfully retrieved context from the vector database")
            print("and Gemini LLM generated a grounded, accurate response!")
        else:
            print("\n[VERIFICATION STATUS: FAILED/PARTIAL]")
            print("The response did not contain the exact expected facts ('Emily Stone' and '9876-ALPHA').")
            print("Double check if the API response had any errors or if the data wasn't indexed correctly.")
            
    except Exception as e:
        print(f"\n[ERROR] An exception occurred during verification: {e}")
        
    finally:
        # 6. Cleanup files and Database entries
        print("\n[INFO] Cleaning up test file and database records...")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            print("[INFO] Temporary text file removed.")
            
        delete_success = rag_engine.delete_document_from_db(temp_filename)
        if delete_success:
            print("[INFO] Test document removed from ChromaDB.")
        else:
            print("[WARNING] Could not delete test document from ChromaDB. You may delete it manually.")
            
    print("=" * 60)
    print("VERIFICATION COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
