import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from openai import AzureOpenAI
import numpy as np
import faiss
import json
import os
from dotenv import load_dotenv
load_dotenv()

class SlidingWindowMemory:
    """Manages recent conversation context with sliding window."""
    
    def __init__(self, window_size: int = 10):
        """
        Initialize sliding window memory.
        
        Args:
            window_size: Maximum number of interactions to keep in memory
        """
        self.window_size = window_size
        self.interactions = []
    
    def add_interaction(self, interaction: Dict[str, Any]):
        """Add new interaction to sliding window."""
        self.interactions.append(interaction)
        if len(self.interactions) > self.window_size:
            self.interactions.pop(0)  # Remove oldest
    
    def get_recent_context(self, question: str, n_recent: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent interactions based on question context.
        
        Args:
            question: Current user question
            n_recent: Number of recent interactions to return
            
        Returns:
            List of recent interactions
        """
        # Handle specific temporal references
        if self._has_specific_reference(question):
            return self._get_specific_context(question)
        
        # Return general recent context
        return self.interactions[-n_recent:] if self.interactions else []
    
    def _has_specific_reference(self, question: str) -> bool:
        """Check if question has specific temporal references."""
        temporal_patterns = [
            r"\b(previous|last|earlier|before)\s+(query|question|analysis)\b",
            r"\bwe\s+(discussed|analyzed|looked at|found)\b",
            r"\b(that|this)\s+(data|result|analysis)\b",
            r"\b(show\s+more|tell\s+me\s+more|expand\s+on)\b"
        ]
        return any(re.search(pattern, question.lower()) for pattern in temporal_patterns)
    
    def _get_specific_context(self, question: str) -> List[Dict[str, Any]]:
        """Get specific context based on temporal references."""
        question_lower = question.lower()
        
        if "previous" in question_lower and len(self.interactions) >= 2:
            return self.interactions[-2:]  # Previous interaction + current context
        elif "last" in question_lower and len(self.interactions) >= 3:
            return self.interactions[-3:]  # Last few interactions
        elif any(phrase in question_lower for phrase in ["tell me more", "show more", "expand"]):
            return self.interactions[-1:] if self.interactions else []  # Last interaction
        else:
            return self.interactions[-5:] if self.interactions else []  # Recent context

class SemanticMemoryManager:
    """Manages long-term semantic memory using FAISS and Azure OpenAI embeddings."""
    
    def __init__(self):
        """
        Initialize semantic memory manager.
        """
        # Azure OpenAI configuration
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://shamal-ai-api.cognitiveservices.azure.com/")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        
        if not self.api_key:
            raise ValueError("Azure OpenAI API key is required. Set AZURE_OPENAI_API_KEY environment variable.")
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
        )
        
        # Initialize FAISS index (1536 dimensions for ada-002)
        self.dimension = 1536
        self.index = faiss.IndexFlatL2(self.dimension)  # L2 distance
        
        # Store metadata separately
        self.metadata_store = []
        self.documents_store = []
        self.id_to_index = {}  # Map from document ID to index position
        
    def create_embedding(self, text: str) -> np.ndarray:
        """
        Create embedding using Azure OpenAI API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.embedding_deployment
            )
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            print(f"Error creating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(self.dimension, dtype=np.float32)
    
    def store_interaction(self, interaction: Dict[str, Any]):
        """
        Store interaction in semantic memory.
        
        Args:
            interaction: Interaction data to store
        """
        try:
            # Create combined text for embedding
            combined_text = f"Q: {interaction['user_question']} A: {interaction['text_response']}"
            embedding = self.create_embedding(combined_text)
            
            # Prepare metadata
            metadata = {
                "id": interaction['id'],
                "timestamp": interaction['timestamp'],
                "tables_used": ",".join(interaction.get('tables_involved', [])),
                "question_type": self._classify_question_type(interaction['user_question']),
                "sql_query": interaction['sql_query'][:500],  # Truncate long SQL
                "session_id": interaction.get('session_id', ''),
                "question": interaction['user_question'],
                "response": interaction['text_response']
            }
            
            # Add to FAISS index
            self.index.add(np.array([embedding]))
            
            # Store metadata and document
            self.metadata_store.append(metadata)
            self.documents_store.append(combined_text)
            self.id_to_index[interaction['id']] = len(self.metadata_store) - 1
            
        except Exception as e:
            print(f"Error storing interaction in semantic memory: {e}")
    
    def retrieve_semantic_context(self, question: str, n_results: int = 3, 
                                exclude_session: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve semantically similar interactions.
        
        Args:
            question: Current user question
            n_results: Number of results to return
            exclude_session: Session ID to exclude from results
            
        Returns:
            List of similar interactions
        """
        try:
            if self.index.ntotal == 0:
                return []
            
            # Create embedding for the question
            query_embedding = self.create_embedding(question)
            query_embedding = np.array([query_embedding])
            
            # Search for similar vectors
            k = min(n_results * 2, self.index.ntotal)  # Get more results to filter
            distances, indices = self.index.search(query_embedding, k)
            
            # Format results
            formatted_results = []
            for i, (idx, distance) in enumerate(zip(indices[0], distances[0])):
                if idx == -1:  # FAISS returns -1 for empty results
                    continue
                    
                metadata = self.metadata_store[idx]
                
                # Skip if from excluded session
                if exclude_session and metadata.get('session_id') == exclude_session:
                    continue
                
                # Convert L2 distance to similarity score (0-1)
                # Smaller distance = higher similarity
                similarity = 1 / (1 + distance)
                
                # Only include results with good similarity
                if similarity > 0.5:
                    formatted_results.append({
                        "question": metadata.get('question', ''),
                        "response": metadata.get('response', ''),
                        "sql_query": metadata.get('sql_query', ''),
                        "tables_used": metadata.get('tables_used', '').split(',') if metadata.get('tables_used') else [],
                        "similarity": similarity,
                        "timestamp": metadata.get('timestamp', '')
                    })
                
                if len(formatted_results) >= n_results:
                    break
            
            return formatted_results
            
        except Exception as e:
            print(f"Error retrieving semantic context: {e}")
            return []
    
    def _classify_question_type(self, question: str) -> str:
        """Classify the type of question for better retrieval."""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['sum', 'total', 'aggregate', 'count']):
            return 'aggregation'
        elif any(word in question_lower for word in ['compare', 'vs', 'versus', 'difference']):
            return 'comparison'
        elif any(word in question_lower for word in ['trend', 'over time', 'monthly', 'quarterly']):
            return 'trend_analysis'
        elif any(word in question_lower for word in ['show', 'list', 'display', 'get']):
            return 'retrieval'
        elif any(word in question_lower for word in ['average', 'mean', 'median']):
            return 'statistical'
        else:
            return 'general'
    
    def clear(self):
        """Clear all stored data."""
        self.index.reset()
        self.metadata_store.clear()
        self.documents_store.clear()
        self.id_to_index.clear()

class MemoryManager:
    """Combines sliding window and semantic memory for optimal context management."""
    
    def __init__(self, window_size: int = 15,use_semantic_memory: bool = False):
        """
        Initialize hybrid memory manager.
        
        Args:
            window_size: Size of sliding window for recent interactions
            use_semantic_memory: Whether to use semantic memory for long-term context
        """
        self.session_memory = SlidingWindowMemory(window_size)
        if use_semantic_memory:
            self.semantic_memory = SemanticMemoryManager()
        self.session_id = str(uuid.uuid4())
        self.use_semantic_memory = use_semantic_memory
    
    def store_interaction(self, interaction: Dict[str, Any]):
        """Store interaction in both memory systems."""
        # Add session ID
        interaction['session_id'] = self.session_id
        
        # Store in both systems
        self.session_memory.add_interaction(interaction)
        if self.use_semantic_memory:
            self.semantic_memory.store_interaction(interaction)
    
    def get_contextual_information(self, user_question: str) -> Dict[str, Any]:
        """
        Get comprehensive contextual information for a user question.
        
        Args:
            user_question: Current user question
            
        Returns:
            Dictionary containing all context layers
        """
        context = {
            'recent_interactions': [],
            'relevant_history': [],
            'conversation_flow': "",
            'has_temporal_reference': False
        }
        
        # Check for temporal references
        context['has_temporal_reference'] = self._has_temporal_reference(user_question)
        
        # Get recent context (sliding window)
        if context['has_temporal_reference']:
            context['recent_interactions'] = self.session_memory.get_recent_context(user_question, n_recent=3)
            context['conversation_flow'] = self._build_conversation_flow(context['recent_interactions'])
        else:
            context['recent_interactions'] = self.session_memory.get_recent_context(user_question, n_recent=2)
        
        # Get semantic context (exclude current session to avoid contamination)
        if self.use_semantic_memory:
            context['relevant_history'] = self.semantic_memory.retrieve_semantic_context(
                user_question, 
                n_results=3,
                exclude_session=self.session_id
            )
        
        # Deduplicate and prioritize context
        context = self._optimize_context(context, user_question)
        
        return context
    
    def _has_temporal_reference(self, question: str) -> bool:
        """Check if question contains temporal references."""
        temporal_patterns = [
            r"\b(previous|last|earlier|before)\s+(query|question|analysis)\b",
            r"\bwe\s+(discussed|analyzed|looked at|found)\b",
            r"\b(that|this)\s+(data|result|analysis)\b",
            r"\b(show\s+more|tell\s+me\s+more|expand\s+on)\b",
            r"\bin\s+the\s+(last|previous)\s+\w+\b"
        ]
        return any(re.search(pattern, question.lower()) for pattern in temporal_patterns)
    
    def _build_conversation_flow(self, recent_interactions: List[Dict[str, Any]]) -> str:
        """Build conversation flow description from recent interactions."""
        if not recent_interactions:
            return ""
        
        flow_parts = []
        for i, interaction in enumerate(recent_interactions[-3:], 1):  # Last 3 interactions
            flow_parts.append(f"Step {i}: User asked '{interaction['user_question']}' and received analysis about {', '.join(interaction.get('tables_involved', []))}")
        
        return " → ".join(flow_parts)
    
    def _optimize_context(self, context: Dict[str, Any], user_question: str) -> Dict[str, Any]:
        """Optimize context by removing duplicates and prioritizing relevance."""
        # Remove semantic results that are too similar to recent interactions
        if context['recent_interactions'] and context['relevant_history']:
            recent_questions = [interaction['user_question'].lower() for interaction in context['recent_interactions']]
            
            filtered_history = []
            for hist in context['relevant_history']:
                # Only include if not too similar to recent interactions
                if not any(self._are_questions_similar(hist['question'].lower(), recent_q) 
                          for recent_q in recent_questions):
                    filtered_history.append(hist)
            
            context['relevant_history'] = filtered_history[:2]  # Keep top 2 unique results
        
        # Prioritize context based on question type
        if context['has_temporal_reference']:
            # For temporal references, prioritize recent interactions
            context['relevant_history'] = context['relevant_history'][:1]  # Reduce semantic context
        else:
            # For general questions, balance both types
            context['recent_interactions'] = context['recent_interactions'][:2]
            context['relevant_history'] = context['relevant_history'][:2]
        
        return context
    
    def _are_questions_similar(self, q1: str, q2: str) -> bool:
        """Check if two questions are too similar (simple heuristic)."""
        # Simple similarity check based on word overlap
        words1 = set(q1.split())
        words2 = set(q2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        overlap = len(words1.intersection(words2))
        min_length = min(len(words1), len(words2))
        
        return overlap / min_length > 0.6  # 60% word overlap threshold
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            # Clear semantic memory
            if self.use_semantic_memory:
                if hasattr(self, 'semantic_memory'):
                    self.semantic_memory.clear()
            # Clear session memory
            if hasattr(self, 'session_memory'):
                self.session_memory.interactions.clear()
        except Exception as e:
            print(f"Error during cleanup: {e}")