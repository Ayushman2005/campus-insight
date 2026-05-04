import chromadb
from sentence_transformers import SentenceTransformer
import uuid

class SemanticSearchEngine:
    def __init__(self):
        # Clean, standard initialization
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name="campus_docs")
        self.model = None

    def _get_model(self):
        if self.model is None:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        return self.model

    def index_document(self, text: str, metadata: dict):
        chunk_size = 500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - 50)]
        
        if not chunks:
            return

        embeddings = self._get_model().encode(chunks).tolist()
        
        ids = [f"{metadata['title']}_{i}_{str(uuid.uuid4())[:8]}" for i in range(len(chunks))]
        metadatas = [metadata for _ in range(len(chunks))]
        
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )

    def search(self, query: str, n_results: int = 5, filters: dict = None):
        query_embedding = self._get_model().encode([query]).tolist()
        
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

    def get_all_filenames(self):
        # Get all documents to extract unique filenames
        try:
            result = self.collection.get(include=['metadatas'])
            filenames = set()
            if result and result.get('metadatas'):
                for meta in result['metadatas']:
                    if meta and 'filename' in meta:
                        filenames.add(meta['filename'])
            return list(filenames)
        except Exception:
            return []

    def delete_document(self, filename: str):
        # Search by the filename metadata field for robustness across environments
        self.collection.delete(
            where={"filename": filename}
        )