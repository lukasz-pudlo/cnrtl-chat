#!/usr/bin/env python3
"""
LLM Integration Service
Functional approach for LLM queries and response generation
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from .database_manager import SearchResult

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama2"


def generate_response(query: str, search_results: List[SearchResult], options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate response using LLM with search results as context
    """
    if not options:
        options = {}

    try:
        # Build context from search results
        context = build_context(search_results)

        # Create prompt
        prompt = create_prompt(query, context, options)

        # Generate response
        response = call_llm(prompt, options)

        # Extract sources
        sources = extract_sources(search_results)

        # Calculate confidence
        confidence = calculate_confidence(search_results, response)

        return {
            'answer': response,
            'sources': sources,
            'confidence': confidence,
            'query_type': classify_query(query),
            'model': options.get('model', DEFAULT_MODEL),
            'tokens_used': len(prompt.split()) + len(response.split())
        }

    except Exception as e:
        logger.error(f"LLM response generation failed: {e}")
        return {
            'answer': f"I apologize, but I encountered an error generating a response: {str(e)}",
            'sources': [],
            'confidence': 0.0,
            'query_type': 'error',
            'model': options.get('model', DEFAULT_MODEL),
            'tokens_used': 0
        }


def build_context(search_results: List[SearchResult]) -> str:
    """
    Build context string from search results
    """
    if not search_results:
        return "No relevant information found."

    context_parts = []
    for i, result in enumerate(search_results[:5]):  # Limit to top 5 results
        source_info = f"[Source {i+1}: {result.entry_info.get('title', 'Entry')}]"
        content = result.content
        context_parts.append(f"{source_info}\n{content}\n")

    return "\n".join(context_parts)


def create_prompt(query: str, context: str, options: Dict[str, Any]) -> str:
    """
    Create prompt for LLM

    TODO: Implement prompt engineering:
    - Project-specific prompts
    - Few-shot examples
    - Dynamic prompt selection
    """
    project_type = options.get('project_type', 'general')

    # TODO: Create project-specific system prompts
    system_prompts = {
        'literature': """You are a literary analysis assistant. Help users understand themes, characters, and literary devices in literature.""",
        'documentation': """You are a technical documentation assistant. Help users understand APIs, code examples, and technical concepts.""",
        'research': """You are a research assistant. Help users understand academic papers, methodologies, and research concepts.""",
        'custom': """You are a specialized assistant for the user's custom domain. Help users understand and work with their specific content and use cases.""",
        'general': """You are a helpful assistant that answers questions based on provided context."""
    }

    system_prompt = system_prompts.get(project_type, system_prompts['general'])

    user_prompt = f"""Context:
{context}

Question: {query}

Please provide a helpful answer based on the context above. Remember to cite sources using [Source X] notation."""

    return f"{system_prompt}\n\n{user_prompt}"


def call_llm(prompt: str, options: Dict[str, Any]) -> str:
    """
    Call LLM service

    TODO: Implement advanced LLM features:
    - Multiple model support
    - Response streaming
    - Retry logic
    - Fallback models
    """
    try:
        payload = {
            "model": options.get('model', DEFAULT_MODEL),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": options.get('temperature', 0.1),
                "max_tokens": options.get('max_tokens', 1000)
            }
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result.get("response", "No response generated")

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"Error generating response: {str(e)}"


def extract_sources(search_results: List[SearchResult]) -> List[Dict[str, Any]]:
    """
    Extract source information from search results

    TODO: Implement source enrichment:
    - Additional metadata
    - Source ranking
    - Duplicate detection
    """
    sources = []

    for i, result in enumerate(search_results):
        source = {
            'source_id': i + 1,
            'title': result.entry_info.get('title', 'Entry'),
            'category': result.entry_info.get('work_type', 'unknown'),
            'author': result.entry_info.get('author', 'Unknown'),
            'excerpt': result.content[:200] + "...",
            'similarity_score': result.similarity_score,
            'chunk_id': result.chunk_id,
            'metadata': result.metadata
        }
        sources.append(source)

    return sources


def calculate_confidence(search_results: List[SearchResult], response: str) -> float:
    """
    Calculate confidence score for the response

    TODO: Implement sophisticated confidence scoring:
    - Multiple confidence factors
    - Machine learning models
    - Historical performance
    """
    if not search_results:
        return 0.0

    # Base confidence on search result quality
    avg_similarity = sum(
        r.similarity_score for r in search_results) / len(search_results)

    # Adjust based on response length and content
    response_length = len(response.split())
    if response_length < 10:
        confidence = avg_similarity * 0.5
    elif response_length < 50:
        confidence = avg_similarity * 0.8
    else:
        confidence = avg_similarity

    # Check for uncertainty indicators
    uncertainty_words = ['not sure', 'unclear',
                         'might be', 'possibly', 'i don\'t know']
    if any(word in response.lower() for word in uncertainty_words):
        confidence *= 0.7

    return min(1.0, max(0.0, confidence))


def classify_query(query: str) -> str:
    """
    Classify query type

    TODO: Implement advanced query classification:
    - Machine learning models
    - Intent recognition
    - Context-aware classification
    """
    query_lower = query.lower()

    if any(word in query_lower for word in ['what is', 'what are', 'define']):
        return 'factual'
    elif any(word in query_lower for word in ['how do', 'how to', 'steps']):
        return 'procedural'
    elif any(word in query_lower for word in ['compare', 'difference', 'versus']):
        return 'comparative'
    elif any(word in query_lower for word in ['why', 'explain', 'reason']):
        return 'explanatory'
    else:
        return 'general'


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts

    TODO: Implement batch embedding generation
    """
    # TODO: Implement batch embedding generation
    return []


def validate_response(response: str, query: str) -> bool:
    """
    Validate LLM response quality

    TODO: Implement response validation:
    - Fact checking
    - Source verification
    - Quality metrics
    """
    # TODO: Implement response validation
    return True
