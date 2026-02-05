import chromadb
from sentence_transformers import SentenceTransformer
import uuid

class SemanticSearchEngine:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name="campus_docs")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def index_document(self, text: str, metadata: dict):
        chunk_size = 500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - 50)]
        
        if not chunks:
            return

        embeddings = self.model.encode(chunks).tolist()
        
        ids = [f"{metadata['title']}_{i}_{str(uuid.uuid4())[:8]}" for i in range(len(chunks))]
        metadatas = [metadata for _ in range(len(chunks))]
        
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        print(f"Indexed {len(chunks)} chunks for {metadata['title']}")

    def search(self, query: str, n_results: int = 5, filters: dict = None):
        query_embedding = self.model.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=filters
        )
        
        clean_results = []
        if results['documents']:
            for i in range(len(results['documents'][0])):
                clean_results.append({
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "relevance_score": 1 - results['distances'][0][i]
                })
        return clean_results

    def get_document_count(self):
        return self.collection.count()

    def delete_document(self, filename: str):
        target_url = f"http://localhost:8000/files/{filename}"
        print(f"Deleting vectors for: {target_url}")
        self.collection.delete(
            where={"source_url": target_url}
        )