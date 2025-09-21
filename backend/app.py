#!/usr/bin/env python3
"""
Capstone RAG System - Flask Backend
Main application entry point with API endpoints
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import json
from typing import Dict, Any

# Import our services
from services import database_manager
from services import search_engine
from services import llm_integration
from services import analytics
from services import document_processor
from services.database_manager import SearchResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
PROJECT_TYPE = "literature"  # Default project type


@app.before_request
def initialize_services():
    """Initialize all services on startup"""
    try:
        # Initialize database
        database_manager.initialize_database()
        logger.info("Database initialized successfully")

        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

# API Routes


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # TODO: Add actual health checks for services
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': 'connected',
                'search_engine': 'ready',
                'llm_integration': 'ready'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/api/query', methods=['POST'])
def handle_query():
    """Main query endpoint for RAG system"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        options = data.get('options', {})

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        logger.info(f"Processing query: {query[:100]}...")

        # Process query through RAG pipeline
        result = process_rag_query(query, options)

        # Log analytics
        analytics.log_query(query, result)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        return jsonify({
            'error': 'Query processing failed',
            'details': str(e)
        }), 500


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get system analytics and statistics"""
    try:
        analytics_data = analytics.get_analytics_summary()
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Analytics retrieval failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/stats', methods=['GET'])
def get_document_stats():
    """Get document statistics"""
    try:
        stats = database_manager.get_document_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Entry stats retrieval failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/search', methods=['POST'])
def search_documents():
    """Search documents with filters"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        filters = data.get('filters', {})

        results = search_engine.search_documents(query, filters)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Entry search failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/upload', methods=['POST'])
def upload_documents():
    """Upload and process new documents"""
    try:
        # TODO: Implement document upload and processing
        return jsonify({
            'message': 'Entry upload not yet implemented',
            'status': 'pending'
        })
    except Exception as e:
        logger.error(f"Entry upload failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/processing/status', methods=['GET'])
def get_processing_status():
    """Get document processing status"""
    try:
        # TODO: Implement processing status tracking
        return jsonify({
            'status': 'idle',
            'processed_documents': 0,
            'pending_documents': 0
        })
    except Exception as e:
        logger.error(f"Processing status retrieval failed: {e}")
        return jsonify({'error': str(e)}), 500

# Helper Functions


def validate_system() -> Dict[str, Any]:
    """Validate system components before processing queries"""
    try:
        # Test database connectivity
        if not database_manager.validate_database_connection():
            return {"status": "failed", "error": "database_connection"}

        # Test embedding service
        embedding = search_engine.get_embedding("test query")
        if not embedding:
            return {"status": "failed", "error": "embedding_service"}

        return {
            "status": "passed",
            "database_connected": True,
            "embedding_service": True,
            "embedding_dimensions": len(embedding)
        }
    except Exception as e:
        logger.error(f"System validation failed: {e}")
        return {"status": "failed", "error": str(e)}


def process_rag_query(query: str, options: dict) -> dict:
    """Process a query through the complete RAG pipeline"""

    start_time = datetime.now()

    try:
        # Step 1: Search for relevant documents
        search_results = search_engine.search_documents(query, options)

        if not search_results:
            return {
                'answer': "I couldn't find any relevant information in the documents. Please try rephrasing your question or contact support for assistance.",
                'sources': [],
                'confidence_score': 0.0,
                'response_time_ms': 0,
                'metadata': {
                    'query_type': 'no_results',
                    'search_results_count': 0
                }
            }

        # Step 2: Generate response using LLM
        response = llm_integration.generate_response(
            query, search_results, options)

        # Step 3: Calculate response time
        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Step 4: Build final result
        result = {
            'answer': response.get('answer', 'No response generated'),
            'sources': response.get('sources', []),
            'confidence_score': response.get('confidence', 0.0),
            'response_time_ms': response_time_ms,
            'metadata': {
                'query_type': response.get('query_type', 'general'),
                'search_results_count': len(search_results),
                'model_used': response.get('model', 'unknown'),
                'tokens_used': response.get('tokens_used', 0)
            }
        }

        return result

    except Exception as e:
        logger.error(f"RAG processing failed: {e}")
        return {
            'answer': f"I encountered an error processing your query: {str(e)}",
            'sources': [],
            'confidence_score': 0.0,
            'response_time_ms': 0,
            'metadata': {
                'error': str(e),
                'query_type': 'error'
            }
        }

# Error Handlers


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# Main execution
if __name__ == '__main__':
    # Initialize services
    initialize_services()

    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
