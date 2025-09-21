#!/usr/bin/env python3
"""
Database Manager with JSONB Support
"""

import os
import psycopg
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Database connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5050,
    'dbname': 'pgvector-cnrtl',
    'user': 'postgres-cnrtl',
    'password': os.getenv("POSTGRES_PASSWORD")
}


@dataclass
class SearchResult:
    """Represents a search result chunk with structured data."""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    entry_info: Dict[str, Any]
    processing_info: Dict[str, Any]
    similarity_score: float


def get_db_connection():
    """Get a database connection using context manager approach."""
    try:
        return psycopg.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def initialize_database():
    """Initialize database schema with JSONB support"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Enable extensions
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")

                # Create main chunks table with JSONB
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cnrtl_chunks (
                        id SERIAL PRIMARY KEY,
                        chunk_id VARCHAR(50) UNIQUE NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector(1024),
                        
                        -- JSONB fields for flexible metadata storage
                        metadata JSONB NOT NULL DEFAULT '{}',
                        entry_info JSONB NOT NULL DEFAULT '{}',
                        processing_info JSONB NOT NULL DEFAULT '{}',
                        
                        -- Extracted fields for performance
                        entry_type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # Create query analytics table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS query_analytics (
                        id SERIAL PRIMARY KEY,
                        query_text TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        response_metadata JSONB DEFAULT '{}',
                        user_session JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # Create indexes for JSONB fields
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_metadata 
                    ON cnrtl_chunks USING gin(metadata);
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_entry_info 
                    ON cnrtl_chunks USING gin(entry_info);
                """)

                # Create vector similarity index
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
                    ON cnrtl_chunks USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)

                conn.commit()
                logger.info("Database schema initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def store_chunks(chunks: List[Dict], embeddings: List[List[float]]):
    """Store processed chunks with embeddings using modern psycopg approach"""
    if len(chunks) != len(embeddings):
        raise ValueError("Number of chunks must match number of embeddings")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    cur.execute("""
                        INSERT INTO cnrtl_chunks (
                            chunk_id, content, embedding, metadata, 
                            entry_info, processing_info, entry_type
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            entry_info = EXCLUDED.entry_info,
                            processing_info = EXCLUDED.processing_info
                    """, (
                        chunk.get('chunk_id'),
                        chunk.get('content'),
                        embedding,
                        json.dumps(chunk.get('metadata', {})),
                        json.dumps(chunk.get('entry_info', {})),
                        json.dumps(chunk.get('processing_info', {})),
                        chunk.get('entry_type', 'unknown')
                    ))

            conn.commit()
            logger.info(f"Stored {len(chunks)} chunks in database")

    except Exception as e:
        logger.error(f"Failed to store chunks: {e}")
        raise


def search_chunks(query_embedding: List[float],
                  filters: Optional[Dict[str, Any]] = None,
                  limit: int = 10) -> List[SearchResult]:
    """Search chunks with JSONB filtering using RealDictCursor"""

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg.RealDictCursor) as cur:
                # Build WHERE clause for filters
                where_conditions = ["TRUE"]
                params = [query_embedding, query_embedding, limit]
                param_index = 4

                if filters:
                    # Build JSONB filter conditions
                    for key, value in filters.items():
                        if key == "metadata":
                            for meta_key, meta_value in value.items():
                                where_conditions.append(f"metadata->>%s = %s")
                                params.extend([meta_key, str(meta_value)])
                        elif key == "entry_info":
                            for doc_key, doc_value in value.items():
                                where_conditions.append(
                                    f"entry_info->>%s = %s")
                                params.extend([doc_key, str(doc_value)])
                        elif key == "entry_type":
                            where_conditions.append(f"entry_type = %s")
                            params.append(value)

                where_clause = " AND ".join(where_conditions)

                cur.execute(f"""
                    SELECT 
                        chunk_id, content, metadata, entry_info, processing_info,
                        1 - (embedding <=> %s::vector) as similarity_score
                    FROM cnrtl_chunks
                    WHERE {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, params)

                results = cur.fetchall()

                return [
                    SearchResult(
                        chunk_id=row['chunk_id'],
                        content=row['content'],
                        metadata=json.loads(row['metadata']),
                        entry_info=json.loads(row['entry_info']),
                        processing_info=json.loads(row['processing_info']),
                        similarity_score=float(row['similarity_score'])
                    )
                    for row in results
                ]

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def get_document_stats() -> Dict[str, Any]:
    """Get document statistics using JSONB queries with RealDictCursor"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg.RealDictCursor) as cur:
                # Total chunks
                cur.execute(
                    "SELECT COUNT(*) as total_chunks FROM cnrtl_chunks")
                total_chunks = cur.fetchone()['total_chunks']

                # Count by document type
                cur.execute("""
                    SELECT 
                        entry_info->>'work_type' as doc_type,
                        COUNT(*) as count
                    FROM cnrtl_chunks
                    GROUP BY entry_info->>'work_type'
                """)
                doc_types = {row['doc_type'] or 'unknown': row['count']
                             for row in cur.fetchall()}

                # Count by metadata fields (themes, characters, etc.)
                cur.execute("""
                    SELECT 
                        jsonb_array_elements(metadata->'themes') as theme,
                        COUNT(*) as count
                    FROM cnrtl_chunks
                    WHERE metadata ? 'themes'
                    GROUP BY jsonb_array_elements(metadata->'themes')
                    ORDER BY count DESC
                    LIMIT 10
                """)
                themes = [{'theme': row['theme'], 'count': row['count']}
                          for row in cur.fetchall()]

                return {
                    'total_chunks': total_chunks,
                    'entry_types': doc_types,
                    'popular_themes': themes
                }

    except Exception as e:
        logger.error(f"Failed to get document stats: {e}")
        return {'error': str(e)}


def log_query(query_text: str, response_data: Dict[str, Any]):
    """Log query analytics using context manager"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO query_analytics (
                        query_text, query_metadata, response_metadata
                    ) VALUES (%s, %s, %s)
                """, (
                    query_text,
                    json.dumps({
                        'query_length': len(query_text),
                        'timestamp': response_data.get('metadata', {}).get('timestamp', '')
                    }),
                    json.dumps({
                        'confidence_score': response_data.get('confidence_score', 0),
                        'response_time_ms': response_data.get('response_time_ms', 0),
                        'sources_count': len(response_data.get('sources', [])),
                        'query_type': response_data.get('metadata', {}).get('query_type', 'unknown')
                    })
                ))

            conn.commit()

    except Exception as e:
        logger.error(f"Failed to log query: {e}")


def get_analytics_summary(days: int = 7) -> Dict[str, Any]:
    """Get analytics summary using JSONB queries with RealDictCursor"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg.RealDictCursor) as cur:
                # Basic stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_queries,
                        AVG((response_metadata->>'response_time_ms')::int) as avg_response_time,
                        AVG((response_metadata->>'confidence_score')::float) as avg_confidence
                    FROM query_analytics
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '%s days'
                """ % days)

                summary = cur.fetchone()

                # Top queries
                cur.execute("""
                    SELECT query_text, COUNT(*) as frequency
                    FROM query_analytics
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '%s days'
                    GROUP BY query_text
                    ORDER BY frequency DESC
                    LIMIT 10
                """ % days)

                top_queries = [{'query': row['query_text'],
                                'frequency': row['frequency']} for row in cur.fetchall()]

                # Query types distribution
                cur.execute("""
                    SELECT 
                        response_metadata->>'query_type' as query_type,
                        COUNT(*) as count
                    FROM query_analytics
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '%s days'
                    GROUP BY response_metadata->>'query_type'
                """ % days)

                query_types = {row['query_type'] or 'unknown': row['count']
                               for row in cur.fetchall()}

                return {
                    'total_queries': summary['total_queries'],
                    'avg_response_time_ms': float(summary['avg_response_time']) if summary['avg_response_time'] else 0,
                    'avg_confidence': float(summary['avg_confidence']) if summary['avg_confidence'] else 0,
                    'top_queries': top_queries,
                    'query_types': query_types
                }

    except Exception as e:
        logger.error(f"Failed to get analytics summary: {e}")
        return {'error': str(e)}


def validate_database_connection() -> bool:
    """Validate database connection and basic functionality"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM cnrtl_chunks WHERE embedding IS NOT NULL;")
                chunk_count = cur.fetchone()[0]
                logger.info(
                    f"Database validation: {chunk_count} chunks with embeddings available")
                return True
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return False
