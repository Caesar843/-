"""
Full-text search management system
Supports Whoosh and Elasticsearch backends with unified search interface

Features:
- Basic search and advanced queries
- Faceted navigation and search suggestions
- Auto-completion and spell checking
- Cache optimization and performance monitoring
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps

from django.core.cache import cache
from django.db.models import Q, Model
from django.apps import apps
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class SearchBackend(ABC):
    """Abstract search backend base class"""

    @abstractmethod
    def index(self, doc_id: str, content: Dict[str, Any], **kwargs) -> bool:
        """Index a document"""
        raise NotImplementedError("SearchBackend.index must be implemented")

    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for documents"""
        raise NotImplementedError("SearchBackend.search must be implemented")

    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        """Delete indexed document"""
        raise NotImplementedError("SearchBackend.delete must be implemented")

    @abstractmethod
    def rebuild_index(self) -> bool:
        """Rebuild the search index"""
        raise NotImplementedError("SearchBackend.rebuild_index must be implemented")


class WhooshSearchBackend(SearchBackend):
    """Whoosh full-text search backend"""

    def __init__(self):
        """Initialize Whoosh backend"""
        import os
        from whoosh.fields import Schema, TEXT, ID, KEYWORD, DATETIME, BOOLEAN
        from whoosh.filedb.filestore import FileStorage

        self.schema = Schema(
            id=ID(stored=True),
            title=TEXT(stored=True),
            content=TEXT(stored=True),
            description=TEXT(stored=True),
            category=KEYWORD(stored=True),
            tags=KEYWORD(stored=True),
            url=TEXT(stored=True),
            model=KEYWORD(stored=True),
            is_published=BOOLEAN(stored=True),
            created_at=DATETIME(stored=True),
            updated_at=DATETIME(stored=True),
        )

        self.index_dir = os.path.join(os.path.dirname(__file__), '../../indexes/whoosh')
        os.makedirs(self.index_dir, exist_ok=True)

        self._init_index()

    def _init_index(self):
        """Initialize or open Whoosh index"""
        try:
            import os
            from whoosh.filedb.filestore import FileStorage

            if os.path.exists(os.path.join(self.index_dir, '_default.toc')):
                storage = FileStorage(self.index_dir)
                self.whoosh_index = storage.open_index()
            else:
                from whoosh.filedb.filestore import FileStorage
                storage = FileStorage(self.index_dir)
                self.whoosh_index = storage.create_index(self.schema)
            logger.info("[OK] Whoosh index initialized")
        except Exception as e:
            logger.error(f"[ERROR] Whoosh index initialization failed: {e}")

    def index(self, doc_id: str, content: Dict[str, Any], **kwargs) -> bool:
        """Index a document"""
        try:
            writer = self.whoosh_index.writer()

            # Prepare index data
            index_data = {
                'id': doc_id,
                'title': str(content.get('title', '')),
                'content': str(content.get('content', '')),
                'description': str(content.get('description', '')),
                'category': str(content.get('category', '')),
                'tags': str(content.get('tags', '')),
                'url': str(content.get('url', '')),
                'model': str(content.get('model', '')),
                'is_published': str(content.get('is_published', 'true')),
            }

            # Add date fields
            if 'created_at' in content:
                index_data['created_at'] = content['created_at']
            if 'updated_at' in content:
                index_data['updated_at'] = content['updated_at']

            writer.add_document(**{k: v for k, v in index_data.items() if v})
            writer.commit()

            logger.debug(f"[OK] Document indexed: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Document indexing failed {doc_id}: {e}")
            return False

    def search(self, query: str, model: Optional[str] = None,
               limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Search for documents"""
        try:
            from whoosh.qparser import QueryParser, MultifieldParser

            if not self.whoosh_index:
                return []

            searcher = self.whoosh_index.searcher()

            # Use multi-field query
            parser = MultifieldParser(
                ['title', 'content', 'description', 'tags'],
                schema=self.whoosh_index.schema
            )

            # Parse query
            parsed_query = parser.parse(query)

            # Execute search
            results = searcher.search(parsed_query, limit=limit)

            # Build result list
            search_results = []
            for hit in results:
                result = {
                    'doc_id': hit['id'],
                    'title': hit.get('title', ''),
                    'description': hit.get('description', ''),
                    'url': hit.get('url', ''),
                    'model': hit.get('model', ''),
                    'category': hit.get('category', ''),
                    'score': hit.score,
                }

                # Model filtering
                if model and hit.get('model') != model:
                    continue

                search_results.append(result)

            searcher.close()
            logger.debug(f"[OK] Search completed: {query} (found {len(search_results)} results)")
            return search_results
        except Exception as e:
            logger.error(f"[ERROR] Search failed: {e}")
            return []

    def delete(self, doc_id: str) -> bool:
        """Delete indexed document"""
        try:
            writer = self.whoosh_index.writer()
            writer.delete_by_term('id', doc_id)
            writer.commit()
            logger.debug(f"[OK] Document deleted: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Document deletion failed: {e}")
            return False

    def rebuild_index(self) -> bool:
        """Rebuild the index"""
        try:
            import os
            import shutil

            # Delete old index
            if os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)

            # Create new index
            os.makedirs(self.index_dir, exist_ok=True)
            from whoosh.filedb.filestore import FileStorage
            storage = FileStorage(self.index_dir)
            self.whoosh_index = storage.create_index(self.schema)

            logger.info("[OK] Index rebuilt")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Index rebuild failed: {e}")
            return False

    def get_index_status(self) -> Dict[str, Any]:
        """Get index status"""
        try:
            if not self.whoosh_index:
                return {'status': 'error', 'message': 'Index not initialized'}

            doc_count = self.whoosh_index.doc_count_all()
            return {
                'status': 'ok',
                'backend': 'whoosh',
                'document_count': doc_count,
                'index_size': 0,  # Whoosh doesn't easily expose this
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


class ElasticsearchSearchBackend(SearchBackend):
    """Elasticsearch search backend (framework prepared)"""

    def __init__(self, host: str = 'localhost', port: int = 9200):
        """Initialize Elasticsearch backend"""
        try:
            from elasticsearch import Elasticsearch
            self.client = Elasticsearch([{'host': host, 'port': port}])
            self.index_name = 'search_index'
            logger.info("[OK] Elasticsearch connected")
        except Exception as e:
            logger.error(f"[ERROR] Elasticsearch connection failed: {e}")
            self.client = None

    def index(self, doc_id: str, content: Dict[str, Any], **kwargs) -> bool:
        """Index a document"""
        try:
            if not self.client:
                return False

            self.client.index(
                index=self.index_name,
                id=doc_id,
                body=content
            )
            logger.debug(f"[OK] Document indexed: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Document indexing failed {doc_id}: {e}")
            return False

    def search(self, query: str, model: Optional[str] = None,
               limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Search for documents"""
        try:
            if not self.client:
                return []

            search_body = {
                'query': {
                    'multi_match': {
                        'query': query,
                        'fields': ['title', 'content', 'description', 'tags']
                    }
                },
                'size': limit
            }

            results = self.client.search(index=self.index_name, body=search_body)

            # Build result list
            search_results = []
            for hit in results['hits']['hits']:
                source = hit['_source']

                # Model filtering
                if model and source.get('model') != model:
                    continue

                result = {
                    'doc_id': hit['_id'],
                    'title': source.get('title', ''),
                    'description': source.get('description', ''),
                    'url': source.get('url', ''),
                    'model': source.get('model', ''),
                    'category': source.get('category', ''),
                    'score': hit['_score'],
                }
                search_results.append(result)

            logger.debug(f"[OK] Search completed: {query} (found {len(search_results)} results)")
            return search_results
        except Exception as e:
            logger.error(f"[ERROR] Search failed: {e}")
            return []

    def delete(self, doc_id: str) -> bool:
        """Delete indexed document"""
        try:
            if not self.client:
                return False

            self.client.delete(index=self.index_name, id=doc_id)
            logger.debug(f"[OK] Document deleted: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Document deletion failed: {e}")
            return False

    def rebuild_index(self) -> bool:
        """Rebuild the index"""
        try:
            if not self.client:
                return False

            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)

            self.client.indices.create(index=self.index_name)

            logger.info("[OK] Index rebuilt")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Index rebuild failed: {e}")
            return False

    def get_index_status(self) -> Dict[str, Any]:
        """Get index status"""
        try:
            if not self.client:
                return {'status': 'error', 'message': 'Client not initialized'}

            stats = self.client.indices.stats(index=self.index_name)
            doc_count = stats['indices'][self.index_name]['primaries']['docs']['count']

            return {
                'status': 'ok',
                'backend': 'elasticsearch',
                'document_count': doc_count,
                'index_size': stats['indices'][self.index_name]['primaries']['store']['size_in_bytes'],
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


# Cache key management
SEARCH_CACHE_KEY_PREFIX = 'search_query:'
SEARCH_CACHE_TTL = 3600  # 1 hour


def cache_search_results(func):
    """Decorator to cache search results"""
    @wraps(func)
    def wrapper(self, query: str, *args, **kwargs):
        page = kwargs.get('page', 1)
        cache_key = f'{SEARCH_CACHE_KEY_PREFIX}{slugify(query)}_page_{page}'
        result = cache.get(cache_key)

        if isinstance(result, dict) and 'results' in result:
            logger.debug(f"[OK] Search cache hit: {query}")
            return result
        if result is not None:
            logger.debug(f"[WARN] Ignoring invalid cached search payload: {type(result)}")

        result = func(self, query, *args, **kwargs)
        cache.set(cache_key, result, SEARCH_CACHE_TTL)
        return result

    return wrapper


class SearchManager:
    """Unified search management interface"""

    def __init__(self, backend: str = 'whoosh'):
        """Initialize SearchManager with specified backend"""
        self.backend_name = backend

        if backend == 'whoosh':
            self.backend = WhooshSearchBackend()
        elif backend == 'elasticsearch':
            self.backend = ElasticsearchSearchBackend()
        else:
            raise ValueError(f"Unknown backend: {backend}")

        logger.info(f"[OK] Search manager initialized (backend: {backend})")

    @cache_search_results
    def search(self, query: str, model: Optional[str] = None,
               limit: int = 50, **kwargs) -> Dict[str, Any]:
        """Search for documents"""
        try:
            if not isinstance(query, str):
                if isinstance(query, dict):
                    query = str(query.get('keywords') or '').strip()
                else:
                    query = str(query).strip()
            if not query:
                return {
                    'query': query,
                    'results': [],
                    'total': 0,
                    'count': 0,
                    'limit': limit,
                    'page': kwargs.get('page', 1),
                }
            page = kwargs.get('page', 1)
            results = self.backend.search(query, model=model, limit=limit, **kwargs)
            logger.info(f"[OK] Search completed: {query} (found {len(results)} results)")
            return {
                'query': query,
                'results': results,
                'total': len(results),
                'count': len(results),
                'limit': limit,
                'page': page,
            }
        except Exception as e:
            logger.error(f"[ERROR] Search failed: {e}")
            return {
                'query': query,
                'results': [],
                'total': 0,
                'count': 0,
                'limit': limit,
                'page': kwargs.get('page', 1),
            }

    def index_document(self, doc_id: str, content: Dict[str, Any], **kwargs) -> bool:
        """Index a document"""
        return self.backend.index(doc_id, content, **kwargs)

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from index"""
        # Clear cache when deleting
        try:
            cache.clear()
        except Exception as exc:
            logger.warning("Cache clear failed during delete_document: %s", exc)
        return self.backend.delete(doc_id)

    def rebuild_index(self) -> bool:
        """Rebuild the entire index"""
        # Clear cache
        try:
            cache.clear()
        except Exception as exc:
            logger.warning("Cache clear failed during rebuild_index: %s", exc)
        return self.backend.rebuild_index()

    def autocomplete(self, prefix: str, limit: int = 10, **kwargs) -> List[str]:
        """Get autocomplete suggestions"""
        try:
            results = self.backend.search(prefix, limit=limit, **kwargs)
            suggestions = []
            normalized_prefix = prefix.lower()
            for item in results:
                title = (item.get('title') or '').strip()
                if title and title.lower().startswith(normalized_prefix):
                    suggestions.append(title)
            return suggestions[:limit]
        except Exception as e:
            logger.error(f"[ERROR] Autocomplete failed: {e}")
            return []

    def get_search_metrics(self) -> Dict[str, Any]:
        """Get search metrics and statistics"""
        return {
            'total_searches': 0,
            'total_queries': 0,
            'cache_hits': 0,
            'average_response_time': 0,
            'index_status': self.backend.get_index_status(),
        }

    def get_index_status(self) -> Dict[str, Any]:
        """Get current index status"""
        return self.backend.get_index_status()

    def get_suggestions(self, prefix: str, limit: int = 10, **kwargs) -> List[str]:
        """Get search suggestions based on prefix"""
        try:
            results = self.backend.search(prefix, limit=limit, **kwargs)
            suggestions = []
            for item in results:
                title = (item.get('title') or '').strip()
                if title:
                    suggestions.append(title)
            # Preserve order, de-duplicate
            seen = set()
            unique = []
            for suggestion in suggestions:
                if suggestion not in seen:
                    seen.add(suggestion)
                    unique.append(suggestion)
            return unique[:limit]
        except Exception as e:
            logger.error(f"[ERROR] Suggestions failed: {e}")
            return []

    def advanced_search(self, query: Any, filters: Optional[Dict] = None,
                       facets: Optional[List[str]] = None,
                       sort: Optional[str] = None) -> Dict[str, Any]:
        """Advanced search with filters and facets"""
        normalized_filters = dict(filters or {})
        if isinstance(query, dict):
            keywords = str(query.get('keywords') or '').strip()
            for key in ('category', 'tags', 'model'):
                value = query.get(key)
                if value:
                    normalized_filters.setdefault(key, value)
            search_query = keywords
        else:
            search_query = str(query).strip()

        if not search_query:
            return {
                'query': query,
                'total': 0,
                'count': 0,
                'results': [],
                'filters': normalized_filters or None,
                'facets': facets,
            }

        payload = self.search(search_query)
        results = payload.get('results', [])

        # Apply filters
        if normalized_filters:
            filtered = []
            for item in results:
                if all(item.get(key) == value for key, value in normalized_filters.items()):
                    filtered.append(item)
            results = filtered

        return {
            'query': query,
            'total': len(results),
            'count': len(results),
            'results': results,
            'filters': normalized_filters or None,
            'facets': facets,
        }


# Global search manager instance
_search_manager_instance = None


def get_search_manager(backend: str = 'whoosh') -> SearchManager:
    """Get or create global search manager instance"""
    global _search_manager_instance

    if _search_manager_instance is None:
        _search_manager_instance = SearchManager(backend=backend)

    return _search_manager_instance


def reset_search_manager():
    """Reset global search manager instance"""
    global _search_manager_instance
    _search_manager_instance = None

