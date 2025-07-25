import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Generator, Tuple
import pandas as pd
from openai import AzureOpenAI
from db import DatabaseManager
from sql_gen import SQLGenerator
from memory import MemoryManager
import re
from dotenv import load_dotenv
import os
load_dotenv()

class FinancialDataChatbot:
    """
    Advanced financial data chatbot with hybrid context management.
    Combines sliding window memory and semantic memory for optimal context handling.
    """
    
    def __init__(self):
        """
        Initialize the chatbot with hybrid memory system.
        """
        # Azure OpenAI configuration
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://shamal-ai-api.cognitiveservices.azure.com/")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        if not self.api_key:
            raise ValueError("Azure OpenAI API key is required. Set AZURE_OPENAI_API_KEY environment variable.")
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
        )
        
        # Initialize core components
        self.db_manager = DatabaseManager()
        self.sql_generator = SQLGenerator()
        self.memory_manager = MemoryManager()
        
        # Session tracking
        self.session_id = str(uuid.uuid4())
        self.conversation_started = datetime.now()
        
        print(f"✅ Financial Data Chatbot initialized with Azure OpenAI")
        print(f"📊 Database tables: {', '.join(self.db_manager.get_all_tables())}")
        print(f"🔗 Session ID: {self.session_id}")
    
    def process_query(self, user_question: str) -> Dict[str, Any]:
        """
        Process user query through the complete pipeline.
        
        Args:
            user_question: User's question in natural language
            
        Returns:
            Dictionary containing the complete response and metadata
        """
        try:
            # Step 1: Get contextual information from hybrid memory
            print("🔍 Retrieving contextual information...")
            context = self.memory_manager.get_contextual_information(user_question)
            
            # Step 2: Add database schema to context
            context['database_schema'] = self.db_manager.get_database_metadata_for_llm()
            
            # Step 3: Generate SQL query with enhanced context
            print("🔧 Generating SQL query...")
            sql_results,sql_query, sql_explanation = self.sql_generator.get_data(user_question, context)
            if not sql_query or sql_results is None:
                return self._create_error_response(
                    user_question,
                    "Failed to generate a valid SQL query",
                    "The SQL query could not be generated based on the provided context."
                )
            tables_involved = []
            if sql_query:
                tables_involved = self._extract_tables_from_sql(sql_query)

            # Step 6: Generate natural language response
            print("📝 Generating final response...")
            final_response = self._generate_final_response(
                user_question, sql_query, sql_results, context
            )
            
            # Step 7: Store interaction in memory
            interaction = {
                'id': str(uuid.uuid4()),
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat(),
                'user_question': user_question,
                'sql_query': sql_query,
                'sql_results': sql_results.to_dict('records') if not sql_results.empty else [],
                'text_response': final_response,
                'tables_involved': tables_involved,
                'context_used': {
                    'has_temporal_reference': context.get('has_temporal_reference', False),
                    'recent_interactions_count': len(context.get('recent_interactions', [])),
                    'semantic_matches_count': len(context.get('relevant_history', []))
                }
            }
            
            self.memory_manager.store_interaction(interaction)
            
            # Step 8: Return complete response
            return {
                'success': True,
                'response': final_response,
                'sql_query': sql_query,
                'sql_explanation': sql_explanation,
                'results_count': len(sql_results),
                'tables_used': tables_involved,
                'context_info': interaction['context_used'],
                'session_id': self.session_id
            }
            
        except Exception as e:
            return self._create_error_response(
                user_question,
                f"Unexpected error: {str(e)}",
                "System error occurred during processing"
            )
    
    def process_query_with_progress(self, user_question: str) -> Generator[Tuple[str, str, Optional[Dict[str, Any]]], None, None]:
        """
        Process user query through the complete pipeline with progress updates.
        
        Args:
            user_question: User's question in natural language
            
        Yields:
            Tuple of (status, message, partial_result)
            
        Returns:
            Final result dictionary
        """
        try:
            yield ("initializing", "Starting analysis...", None)
            
            # Step 1: Get contextual information from hybrid memory
            yield ("retrieving_context", "Retrieving contextual information...", None)
            context = self.memory_manager.get_contextual_information(user_question)
            
            # Step 2: Add database schema to context
            yield ("loading_schema", "Loading database schema...", None)
            context['database_schema'] = self.db_manager.get_database_metadata_for_llm()
            
            # Step 3: Generate execution plan
            yield ("analyzing_question", "Analyzing your question and requirements...", None)
            plan = self.sql_generator.generate_plan(user_question, context)
            
            # Step 4: Generate SQL query
            yield ("generating_sql", "Generating SQL query from your request...", None)
            sql_query, sql_explanation = self.sql_generator.generate_sql(user_question, plan, context)
            
            # Step 5: Handle SQL generation failure with retries
            if not sql_query:
                yield ("retrying_generation", "Initial attempt failed, trying alternative approach...", None)
                
                for attempt in range(3):
                    plan = self.sql_generator.generate_plan(user_question, context)
                    sql_query, sql_explanation = self.sql_generator.generate_sql(user_question, plan, context)
                    if sql_query:
                        break
                else:
                    yield ("error", "Failed to generate SQL query after multiple attempts", None)
                    return self._create_error_response(user_question, "Failed to generate a valid SQL query")
            
            # Step 6: Validate SQL syntax
            yield ("validating_sql", "Validating SQL query syntax...", None)
            is_valid, validation_error = self.sql_generator.validate_sql_syntax(sql_query)
            
            is_fixing = False  # Flag to track if we're in fixing mode
            
            if not is_valid:
                is_fixing = True
                yield ("fixing_sql", "SQL validation failed, fixing query...", None)
                
                fixed_query, fix_explanation, is_fixed = self.sql_generator.fix_sql_query(
                    sql_query, 
                    validation_error, 
                    user_question
                )
                
                if is_fixed:
                    sql_query = fixed_query
                    sql_explanation = fix_explanation
                    is_fixing = False
                else:
                    yield ("error", f"SQL validation failed: {validation_error}", None)
                    return self._create_error_response(user_question, f"SQL validation failed: {validation_error}")
            
            # Step 7: Execute SQL query
            yield ("executing_query", "Executing query against database...", None)
            
            try:
                sql_results = self.db_manager.execute_query(sql_query)
                
            except Exception as e:
                if not is_fixing:  # Only show fixing message if we haven't already been fixing
                    is_fixing = True
                    yield ("fixing_execution", "Query execution failed, fixing and retrying...", None)
                
                fixed_query, fix_explanation, is_fixed = self.sql_generator.fix_sql_query(
                    sql_query, 
                    str(e), 
                    user_question
                )
                
                if is_fixed:
                    try:
                        sql_results = self.db_manager.execute_query(fixed_query)
                        sql_query = fixed_query
                        sql_explanation = fix_explanation
                        is_fixing = False
                    except Exception as retry_error:
                        yield ("error", f"Error executing fixed SQL query: {str(retry_error)}", None)
                        return self._create_error_response(user_question, f"Error executing fixed SQL query: {str(retry_error)}")
                else:
                    yield ("error", f"Error executing SQL query: {str(e)}", None)
                    return self._create_error_response(user_question, f"Error executing SQL query: {str(e)}")
            
            tables_involved = self._extract_tables_from_sql(sql_query) if sql_query else []
            
            # Step 8: Generate natural language response
            yield ("generating_response", "Generating AI response...", None)
            final_response = self._generate_final_response(user_question, sql_query, sql_results, context)
            
            # Step 9: Store interaction in memory
            yield ("storing_memory", "Storing interaction in memory...", None)
            interaction = {
                'id': str(uuid.uuid4()),
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat(),
                'user_question': user_question,
                'sql_query': sql_query,
                'sql_results': sql_results.to_dict('records') if not sql_results.empty else [],
                'text_response': final_response,
                'tables_involved': tables_involved,
                'context_used': {
                    'has_temporal_reference': context.get('has_temporal_reference', False),
                    'recent_interactions_count': len(context.get('recent_interactions', [])),
                    'semantic_matches_count': len(context.get('relevant_history', []))
                }
            }
            
            self.memory_manager.store_interaction(interaction)
            
            # Step 10: Final result
            final_result = {
                'success': True,
                'response': final_response,
                'sql_query': sql_query,
                'sql_explanation': sql_explanation,
                'results_count': len(sql_results),
                'tables_used': tables_involved,
                'context_info': interaction['context_used'],
                'session_id': self.session_id
            }
            
            yield ("completed", "Analysis completed successfully!", final_result)
            return final_result
            
        except Exception as e:
            error_result = self._create_error_response(user_question, f"Unexpected error: {str(e)}")
            yield ("error", f"Error: {str(e)}", error_result)
            return error_result

    def _generate_final_response(self, user_question: str, sql_query: str, 
                               sql_results: pd.DataFrame, context: Dict[str, Any]) -> str:
        """Generate natural language response from SQL results."""
        
        # Build context for response generation
        response_prompt = self._build_response_prompt(user_question, sql_query, sql_results, context)
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """You are a financial data analyst assistant. Your task is to provide clear, accurate, and insightful responses based on SQL query results.

IMPORTANT GUIDELINES:
1. Base your response ONLY on the provided SQL results
2. Do not make up or assume any data not present in the results
3. Provide specific numbers, percentages, and insights when available
4. If results are empty, clearly state that no data was found
5. Use professional but accessible language
6. Include relevant context from previous analysis when appropriate
7. If you don't have enough information, say so clearly
8. If clarification is needed, ask specific questions to gather more information about the user's intent.
9. Do not round off numbers unless explicitly asked
10. If the user asks for a summary, provide a concise overview of key findings
11. If the user asks for a detailed analysis, provide a comprehensive breakdown of the data
12. If the user asks for a comparison, highlight differences and similarities clearly"""
                    },
                    {
                        "role": "user",
                        "content": response_prompt
                    }
                ],
                model=self.deployment,
                temperature=0.7,
                max_tokens=1024,
                top_p=0.95
            )
            
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                return "I was able to retrieve the data, but couldn't generate a proper response."
        except Exception as e:
            # Fallback response
            print(f"⚠️ Error generating response: {str(e)}")
            return self._create_fallback_response(sql_results, user_question)
    
    def _build_response_prompt(self, user_question: str, sql_query: str, 
                             sql_results: pd.DataFrame, context: Dict[str, Any]) -> str:
        """Build prompt for natural language response generation."""
        
        prompt_parts = []
        
        # Context information
        if context.get('recent_interactions'):
            prompt_parts.append("RECENT CONVERSATION CONTEXT:")
            for interaction in context['recent_interactions'][-2:]:  # Last 2 interactions
                prompt_parts.append(f"Previous Q: {interaction['user_question']}")
                prompt_parts.append(f"Previous A: {interaction['text_response'][:200]}...")
        
        if context.get('relevant_history'):
            prompt_parts.append("\nRELEVANT HISTORICAL CONTEXT:")
            for hist in context['relevant_history'][:1]:  # Top 1 historical match
                prompt_parts.append(f"Similar past analysis: {hist['response'][:150]}...")
        
        # Current analysis
        prompt_parts.append(f"\nCURRENT USER QUESTION: {user_question}")
        prompt_parts.append(f"\nSQL QUERY EXECUTED: {sql_query}")
        
        # Results data
        if sql_results.empty:
            prompt_parts.append("\nSQL RESULTS: No data found")
        else:
            prompt_parts.append(f"\nSQL RESULTS ({len(sql_results)} rows):")
            if len(sql_results) <= 10:
                prompt_parts.append(sql_results.to_string(index=False))
            else:
                prompt_parts.append("First 10 rows:")
                prompt_parts.append(sql_results.head(10).to_string(index=False))
                prompt_parts.append(f"... and {len(sql_results) - 10} more rows")
        
        # Response instructions
        prompt_parts.append("""
RESPONSE INSTRUCTIONS:
- Provide a clear, conversational response that directly answers the user's question
- Include specific numbers and insights from the data
- If this builds on previous analysis, acknowledge that connection
- If no data was found, explain what that means
- Keep the response concise but informative
- Use bullet points or formatting only when it improves clarity""")
        
        return "\n".join(prompt_parts)
    
    def _create_fallback_response(self, sql_results: pd.DataFrame, user_question: str) -> str:
        """Create a basic fallback response when AI generation fails."""
        if sql_results.empty:
            return f"I executed your query but found no data matching your criteria for: {user_question}"
        
        result_summary = f"I found {len(sql_results)} records"
        if len(sql_results.columns) > 0:
            result_summary += f" with information about: {', '.join(sql_results.columns[:5])}"
        
        return f"{result_summary}. The data has been retrieved successfully, but I'm having trouble generating a detailed analysis at the moment."
    
    def _extract_tables_from_sql(self, sql_query: str) -> List[str]:
        """Extract table names from SQL query."""
        # Simple regex to find table names after FROM and JOIN
        pattern = r'\b(?:FROM|JOIN)\s+["`]?(\w+)["`]?'
        matches = re.findall(pattern, sql_query, re.IGNORECASE)
        return list(set(matches))  # Remove duplicates
    
    def _create_error_response(self, user_question: str, error_message: str, 
                             explanation: str = "", sql_query: str = "") -> Dict[str, Any]:
        """Create error response structure."""
        # Clean up error message to remove driver details
        cleaned_error = error_message
        if '[Microsoft][ODBC Driver' in error_message:
            # Extract just the SQL Server error
            import re
            match = re.search(r'\[SQL Server\](.*?)(?:\(\d+\)|\Z)', error_message)
            if match:
                cleaned_error = match.group(1).strip()
            else:
                # Fallback - remove the driver part
                cleaned_error = error_message.split(']')[-1].strip()
        
        return {
            'success': False,
            'response': f"I encountered an issue processing your question: {cleaned_error}",
            'error': cleaned_error,
            'sql_query': sql_query,
            'sql_explanation': explanation,
            'user_question': user_question,
            'session_id': self.session_id
        }
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation session."""
        recent_interactions = self.memory_manager.session_memory.interactions
        
        return {
            'session_id': self.session_id,
            'started_at': self.conversation_started.isoformat(),
            'total_queries': len(recent_interactions),
            'tables_accessed': list(set([
                table for interaction in recent_interactions 
                for table in interaction.get('tables_involved', [])
            ])),
            'query_types': [
                interaction.get('context_used', {}).get('query_type', 'unknown')
                for interaction in recent_interactions
            ]
        }
    
    def clear_session(self):
        """Clear current session and start fresh."""
        self.memory_manager = MemoryManager()
        self.session_id = str(uuid.uuid4())
        self.conversation_started = datetime.now()
        print(f"🔄 Session cleared. New session ID: {self.session_id}")

# Utility function for easy chatbot instantiation
def create_chatbot() -> FinancialDataChatbot:
    """
    Create and initialize a new chatbot instance.
    
    Returns:
        Initialized chatbot instance
    """
    return FinancialDataChatbot()
