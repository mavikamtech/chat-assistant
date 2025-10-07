from typing import List, Dict, Any
from opensearchpy import OpenSearch, RequestsHttpConnection
import os
from dotenv import load_dotenv

load_dotenv()

class RAGSearch:
    def __init__(self):
        # Only initialize OpenSearch if host is not localhost (production mode)
        self.enabled = os.getenv('OPENSEARCH_HOST', 'localhost') != 'localhost'

        if self.enabled:
            self.client = OpenSearch(
                hosts=[{
                    'host': os.getenv('OPENSEARCH_HOST'),
                    'port': int(os.getenv('OPENSEARCH_PORT', 9200))
                }],
                http_auth=(
                    os.getenv('OPENSEARCH_USER', 'admin'),
                    os.getenv('OPENSEARCH_PASSWORD', 'admin')
                ),
                use_ssl=True,
                verify_certs=False,
                connection_class=RequestsHttpConnection
            )
            self.index_name = os.getenv('OPENSEARCH_INDEX', 'cre-deals')
        else:
            print("INFO: RAG/OpenSearch disabled (localhost mode)")
            self.client = None

    async def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar deals in the vector database"""

        # Return empty results if OpenSearch is not enabled
        if not self.enabled or not self.client:
            print("INFO: RAG search skipped (OpenSearch not available)")
            return []

        # For now, use basic text search
        # In production, use embeddings for semantic search
        try:
            response = self.client.search(
                index=self.index_name,
                body={
                    'query': {
                        'multi_match': {
                            'query': query,
                            'fields': ['title', 'description', 'sponsor', 'location']
                        }
                    },
                    'size': top_k
                }
            )

            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'source': hit['_source']
                })

            return results
        except Exception as e:
            print(f"WARNING: RAG search failed: {e}")
            return []

    async def add_document(self, doc_id: str, document: Dict[str, Any]):
        """Add a document to the vector database"""

        self.client.index(
            index=self.index_name,
            id=doc_id,
            body=document
        )

# Global instance
rag_search = RAGSearch()

async def search_similar(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return await rag_search.search_similar(query, top_k)

async def add_document(doc_id: str, document: Dict[str, Any]):
    return await rag_search.add_document(doc_id, document)
