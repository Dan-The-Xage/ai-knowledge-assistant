"""
AI Service for Hugging Face Inference API with Mistral Models.

This service handles:
- LLM inference via Hugging Face Inference API
- Rate limiting and retry logic
- Circuit breaker pattern for reliability
- Proper RAG prompting strategy
"""

import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from cachetools import TTLCache

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import huggingface_hub
try:
    from huggingface_hub import InferenceClient
    HAS_HF_HUB = True
except ImportError:
    HAS_HF_HUB = False
    logger.warning("huggingface_hub not installed - AI service will use mock mode")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for HF API calls."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: CircuitState = CircuitState.CLOSED
    
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= settings.CIRCUIT_BREAKER_THRESHOLD:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
    
    def record_success(self):
        """Record a success and reset the circuit."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                timeout = timedelta(seconds=settings.CIRCUIT_BREAKER_TIMEOUT)
                if datetime.utcnow() - self.last_failure_time > timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker moved to HALF_OPEN state")
                    return True
            return False
        
        # HALF_OPEN state - allow one request to test
        return True


class HFInferenceError(Exception):
    """Custom exception for HF Inference API errors."""
    pass


class RateLimitError(Exception):
    """Custom exception for rate limit errors."""
    pass


class AIService:
    """
    AI Service using Hugging Face Inference API with Mistral models.
    
    Features:
    - Uses official HuggingFace InferenceClient
    - Rate limiting
    - Circuit breaker pattern
    - Response caching
    - Retry logic with exponential backoff
    """
    
    # Standard RAG prompt template following E-PRD specification
    RAG_PROMPT_TEMPLATE = """<s>[INST] You are an internal company AI assistant.
Answer ONLY using the context below.
If the answer is not found, respond: "Information not found in provided documents."

Context:
{context}

Question: {question}

Instructions:
- Be concise but comprehensive
- Cite specific documents when possible
- If the context doesn't contain relevant information, say so clearly
- Do not make up information not present in the context
[/INST]"""

    SIMPLE_CHAT_TEMPLATE = """<s>[INST] You are a helpful AI Knowledge Assistant for an internal company system.
{question} [/INST]"""

    def __init__(self):
        """Initialize the AI service."""
        self.api_token = settings.HF_API_TOKEN
        self.model_name = settings.LLM_MODEL_NAME
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker()
        
        # Response cache (TTL: 5 minutes)
        self.response_cache = TTLCache(maxsize=100, ttl=300)
        
        # Rate limiting
        self.request_timestamps: List[datetime] = []
        self.rate_limit_lock = asyncio.Lock()
        
        # Initialize HF client
        self._client = None
        self._initialized = False
        self._mock_mode = False
        
        if not HAS_HF_HUB:
            logger.warning("huggingface_hub not installed - using mock mode")
            self._mock_mode = True
        elif not self.api_token:
            logger.warning("HF_API_TOKEN not set - AI service will run in mock mode")
            self._mock_mode = True
        else:
            try:
                self._client = InferenceClient(token=self.api_token)
                self._initialized = True
                logger.info(f"AI Service initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize HF client: {e}")
                self._mock_mode = True
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        async with self.rate_limit_lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)
            
            # Remove old timestamps
            self.request_timestamps = [
                ts for ts in self.request_timestamps 
                if ts > minute_ago
            ]
            
            if len(self.request_timestamps) >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
                wait_time = (self.request_timestamps[0] - minute_ago).total_seconds()
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
                raise RateLimitError(f"Rate limit exceeded. Try again in {wait_time:.2f} seconds")
            
            self.request_timestamps.append(now)
    
    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key for a prompt."""
        import hashlib
        return hashlib.md5(prompt.encode()).hexdigest()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    async def _call_hf_api(self, prompt: str) -> str:
        """
        Call Hugging Face Inference API with retry logic.
        
        Args:
            prompt: The formatted prompt to send
            
        Returns:
            Generated text response
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise HFInferenceError("Circuit breaker is OPEN - service temporarily unavailable")
        
        # Check rate limit
        await self._check_rate_limit()
        
        # Check cache
        cache_key = self._get_cache_key(prompt)
        if cache_key in self.response_cache:
            logger.debug("Cache hit for prompt")
            return self.response_cache[cache_key]
        
        try:
            # Use HuggingFace InferenceClient for chat completion
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            response = self._client.chat_completion(
                messages=messages,
                model=self.model_name,
                max_tokens=settings.LLM_MAX_NEW_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                top_p=settings.LLM_TOP_P,
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            # Cache successful response
            self.response_cache[cache_key] = response_text
            self.circuit_breaker.record_success()
            
            return response_text
            
        except Exception as e:
            error_msg = str(e)
            self.circuit_breaker.record_failure()
            
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                raise RateLimitError(f"HF API rate limit exceeded: {error_msg}")
            
            logger.error(f"HF API error: {error_msg}")
            raise HFInferenceError(f"HF API error: {error_msg}")
    
    async def generate_answer(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an answer using RAG with retrieved context.
        
        Args:
            query: User's question
            context_docs: Retrieved document chunks
            conversation_history: Previous conversation messages
            project_id: Optional project scope
            
        Returns:
            Dict with answer, citations, confidence, and metadata
        """
        start_time = time.time()
        
        if self._mock_mode:
            return self._generate_mock_response(query, context_docs)
        
        try:
            # Prepare context from retrieved documents
            context = self._prepare_context(context_docs)
            
            # Build the prompt
            if context_docs and any(doc.get("content") for doc in context_docs):
                prompt = self._build_rag_prompt(query, context, conversation_history)
            else:
                # No context - use simple chat prompt
                prompt = self.SIMPLE_CHAT_TEMPLATE.format(question=query)
            
            # Call HF API
            response_text = await self._call_hf_api(prompt)
            
            # Extract citations
            citations = self._extract_citations(response_text, context_docs)
            
            # Calculate confidence based on retrieval scores
            confidence = self._calculate_confidence(context_docs)
            
            processing_time = time.time() - start_time
            
            return {
                "answer": response_text.strip(),
                "citations": citations,
                "confidence_score": confidence,
                "processing_time": processing_time,
                "model_used": self.model_name,
                "context_docs_used": len(context_docs),
                "cached": False
            }
            
        except RateLimitError as e:
            logger.warning(f"Rate limit error: {e}")
            return {
                "answer": "The AI service is currently experiencing high demand. Please try again in a moment.",
                "citations": [],
                "confidence_score": 0.0,
                "processing_time": time.time() - start_time,
                "model_used": self.model_name,
                "error": str(e)
            }
            
        except HFInferenceError as e:
            logger.error(f"HF Inference error: {e}")
            # Fallback: provide context-based response when HF API is unavailable
            if context_docs and any(doc.get("content") for doc in context_docs):
                fallback_answer = self._generate_context_fallback(query, context_docs)
                return {
                    "answer": fallback_answer,
                    "citations": self._extract_citations(fallback_answer, context_docs),
                    "confidence_score": 0.5,
                    "processing_time": time.time() - start_time,
                    "model_used": "fallback (HF API unavailable)",
                    "error": "AI service temporarily unavailable - showing relevant document excerpts"
                }
            return {
                "answer": "The AI service is temporarily unavailable due to network issues. Please try again when your internet connection is restored.",
                "citations": [],
                "confidence_score": 0.0,
                "processing_time": time.time() - start_time,
                "model_used": self.model_name,
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"Unexpected error generating answer: {e}")
            return self._generate_mock_response(query, context_docs, error=str(e))
    
    def _prepare_context(self, context_docs: List[Dict[str, Any]]) -> str:
        """
        Prepare context string from retrieved documents.
        
        Args:
            context_docs: List of retrieved document chunks
            
        Returns:
            Formatted context string
        """
        if not context_docs:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(context_docs[:settings.MAX_RETRIEVAL_DOCS]):
            content = doc.get("content", "")
            if not content:
                continue
                
            metadata = doc.get("metadata", {})
            
            # Build document reference
            doc_name = metadata.get("filename", f"Document {i+1}")
            page = metadata.get("page_number", "")
            section = metadata.get("section_title", "")
            
            header = f"[Source: {doc_name}"
            if page:
                header += f", Page {page}"
            if section:
                header += f", Section: {section}"
            header += "]"
            
            context_parts.append(f"{header}\n{content}")
        
        return "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."
    
    def _build_rag_prompt(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build the RAG prompt for Mistral.
        
        Args:
            query: User's question
            context: Prepared context from documents
            conversation_history: Previous messages
            
        Returns:
            Formatted prompt string
        """
        return self.RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=query
        )
    
    def _extract_citations(
        self,
        response: str,
        context_docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract citation information from context documents used."""
        citations = []
        
        for doc in context_docs:
            metadata = doc.get("metadata", {})
            similarity = doc.get("similarity_score", 0.0)
            
            # Only cite docs with good similarity scores
            if similarity >= settings.MIN_SIMILARITY_SCORE:
                citations.append({
                    "document_id": metadata.get("document_id"),
                    "filename": metadata.get("filename", "Unknown"),
                    "page_number": metadata.get("page_number"),
                    "section_title": metadata.get("section_title"),
                    "chunk_index": doc.get("chunk_index"),
                    "similarity_score": similarity
                })
        
        return citations
    
    def _calculate_confidence(self, context_docs: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on retrieved documents."""
        if not context_docs:
            return 0.5  # Base confidence for general chat
        
        # Average similarity of retrieved documents
        scores = [doc.get("similarity_score", 0.0) for doc in context_docs]
        if not scores:
            return 0.5
            
        avg_score = sum(scores) / len(scores)
        
        # Boost confidence if multiple relevant docs found
        relevance_bonus = min(len([s for s in scores if s > 0.7]) * 0.05, 0.15)
        
        return min(avg_score + relevance_bonus, 1.0)
    
    def _generate_context_fallback(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """
        Generate a fallback response using document context when HF API is unavailable.
        This provides useful information from retrieved documents without AI generation.
        """
        if not context_docs:
            return "No relevant documents found to answer your question. Please try a different query."
        
        # Get the most relevant content
        relevant_content = []
        for i, doc in enumerate(context_docs[:3]):  # Top 3 most relevant
            content = doc.get("content", "").strip()
            if content:
                metadata = doc.get("metadata", {})
                filename = metadata.get("filename", "Document")
                page = metadata.get("page_number")
                
                source = f"[{filename}"
                if page:
                    source += f", Page {page}"
                source += "]"
                
                # Truncate long content
                if len(content) > 500:
                    content = content[:500] + "..."
                
                relevant_content.append(f"{source}:\n{content}")
        
        if not relevant_content:
            return "I found some documents but couldn't extract readable content. Please try rephrasing your question."
        
        response = "**Note: AI service temporarily unavailable. Showing relevant document excerpts:**\n\n"
        response += "\n\n---\n\n".join(relevant_content)
        response += "\n\n*For AI-generated answers, please ensure your internet connection is active.*"
        
        return response
    
    def _generate_mock_response(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a mock response when API is unavailable."""
        
        if error:
            answer = f"I encountered an error: {error}. "
        else:
            answer = ""
        
        # Generate contextual mock response
        query_lower = query.lower()
        
        if "hello" in query_lower or "hi" in query_lower:
            answer += "Hello! I'm your AI Knowledge Assistant. I can help you find information from your company's documents. What would you like to know?"
        elif "help" in query_lower or "what can you do" in query_lower or "purpose" in query_lower:
            answer += "I'm an AI Knowledge Assistant designed to help you find information from organizational documents. You can ask me questions about policies, procedures, projects, and any documents that have been uploaded to the system."
        elif context_docs and any(doc.get("content") for doc in context_docs):
            sample_content = context_docs[0].get("content", "")[:200]
            answer += f"Based on the documents, here's relevant information: '{sample_content}...'"
        elif "policy" in query_lower or "procedure" in query_lower:
            answer += "For policy questions, please ensure relevant documents are uploaded to the system. I can only answer based on documents that have been added."
        elif "excel" in query_lower or "spreadsheet" in query_lower or "data" in query_lower:
            answer += "For data analysis, please upload your Excel files and I'll help analyze them with statistics, trends, and anomaly detection."
        else:
            if self._mock_mode:
                answer += "I'm currently running in demo mode. Please configure the HF_API_TOKEN environment variable to enable full AI capabilities."
            else:
                answer += "I don't have enough context to answer that question. Please try uploading relevant documents or rephrasing your question."
        
        return {
            "answer": answer,
            "citations": [],
            "confidence_score": 0.5,
            "processing_time": 0.1,
            "model_used": "mock" if self._mock_mode else self.model_name,
            "context_docs_used": len(context_docs),
            "mock_mode": self._mock_mode
        }
    
    async def stream_answer(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream answer generation for real-time responses.
        """
        # Generate complete answer first
        result = await self.generate_answer(query, context_docs, conversation_history)
        answer = result.get("answer", "")
        
        # Simulate streaming by yielding words
        words = answer.split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.03)  # Small delay for streaming effect
    
    def is_ready(self) -> bool:
        """Check if AI service is ready."""
        return self._initialized or self._mock_mode
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the AI service."""
        return {
            "initialized": self._initialized,
            "mock_mode": self._mock_mode,
            "model": self.model_name,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "cache_size": len(self.response_cache),
            "requests_last_minute": len(self.request_timestamps)
        }


# Global instance
ai_service = AIService()
