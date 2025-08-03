import os
from typing import Dict, Any, Optional, Tuple, List
from openai import AzureOpenAI
from dotenv import load_dotenv
from db import DatabaseManager
import re
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class SQLGenerator:
    """Generate SQL queries from natural language using Azure OpenAI API for Azure SQL Server with plan generation."""
    
    def __init__(self):
        """
        Initialize the SQL Generator with Azure OpenAI API.
        """
        # Azure OpenAI configuration
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://shamal-ai-api.cognitiveservices.azure.com/")
        self.deployment =os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        if not self.api_key:
            logger.error("Azure OpenAI API key is missing.")
            raise ValueError("Azure OpenAI API key is required. Set AZURE_OPENAI_API_KEY environment variable.")
            
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
        )
        
        self.db_manager = DatabaseManager()
        
        # Cache for actual column values to improve prompt accuracy
        self._column_value_cache = {}
        logger.info("SQLGenerator initialized.")

    def _get_actual_column_values(self, table_name: str, column_name: str, limit: int = 10) -> List[str]:
        """Get actual values from database for better prompt accuracy."""
        cache_key = f"{table_name}.{column_name}"
        logger.debug(f"Fetching actual column values for {cache_key}")
        if cache_key not in self._column_value_cache:
            try:
                # Use TOP instead of LIMIT for SQL Server
                query = f'SELECT DISTINCT TOP {limit} [{column_name}] FROM [{table_name}] WHERE [{column_name}] IS NOT NULL'
                result = self.db_manager.execute_query(query)
                self._column_value_cache[cache_key] = result[column_name].tolist() if not result.empty else []
                logger.info(f"Fetched values for {cache_key}: {self._column_value_cache[cache_key]}")
            except Exception as e:
                logger.warning(f"Failed to fetch values for {cache_key}: {str(e)}")
                self._column_value_cache[cache_key] = []
        return self._column_value_cache[cache_key]
    
    def generate_plan(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"Generating execution plan for question: {question}")
        # Build comprehensive context
        if context is None:
            schema_info = self.db_manager.get_database_metadata_for_llm()
            context_sections = {
                'database_schema': schema_info,
                'recent_interactions': [],
                'relevant_history': [],
                'conversation_flow': ""
            }
        else:
            context_sections = context
        
        # Create plan generation prompt
        plan_prompt = self._build_optimized_plan_prompt(question, context_sections)
        logger.debug(f"Plan prompt sent to LLM: {plan_prompt}...")
        try:
            # Generate plan using Azure OpenAI
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert SQL query planner for financial data analysis.
                        Your task is to create detailed execution plans for converting natural language questions 
                        into SQL queries, Considering the nature of NLP queries, 
                        if you encounter ambigious user prompts then you should ask for clarification."""
                    },
                    {
                        "role": "user",
                        "content": plan_prompt
                    }
                ],
                model=self.deployment,
                temperature=0.7,
                max_tokens=1024,
                top_p=0.9
            )
            
            if response.choices and response.choices[0].message.content:
                plan = response.choices[0].message.content.strip()
                logger.info(f"Execution plan generated: {plan}...")
                return plan
            else:
                logger.warning("No plan generated from Azure OpenAI API.")
                return "No plan generated from Azure OpenAI API"
                
        except Exception as e:
            logger.error(f"Error generating plan with Azure OpenAI API: {str(e)}")
            return f"Error generating plan with Azure OpenAI API: {str(e)}"
    
    def generate_sql(self, question: str, plan: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        logger.info(f"Generating SQL for question: {question}")
        logger.debug(f"Using execution plan: {plan}...")
        # Build comprehensive context
        if context is None:
            schema_info = self.db_manager.get_database_metadata_for_llm()
            context_sections = {
                'database_schema': schema_info,
                'recent_interactions': [],
                'relevant_history': [],
                'conversation_flow': ""
            }
        else:
            context_sections = context
        
        # Create enhanced prompt with plan
        prompt = self._build_optimized_sql_prompt(question, plan, context_sections)
        logger.debug(f"SQL prompt sent to LLM: {prompt}...")
        try:
            # Generate response using Azure OpenAI
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Azure SQL Server query generator. Generate precise T-SQL queries based on execution plans and natural language questions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.deployment,
                temperature=0.5,
                max_tokens=2048,
                top_p=0.9
            )
            
            if response.choices and response.choices[0].message.content:
                sql_query, explanation = self._parse_response(response.choices[0].message.content)
                logger.info(f"SQL query generated: {sql_query}...")
                logger.debug(f"SQL explanation: {explanation}...")
                return sql_query, explanation
            else:
                logger.warning("No response generated from Azure OpenAI API.")
                return "", "No response generated from Azure OpenAI API"
                
        except Exception as e:
            logger.error(f"Error generating SQL with Azure OpenAI API: {str(e)}")
            return "", f"Error generating SQL with Azure OpenAI API: {str(e)}"
    
    def _build_optimized_plan_prompt(self, question: str, context_sections: Dict[str, Any]) -> str:
        logger.debug("Building optimized plan prompt.")
        
        prompt_parts = []
        
        try:
            business_units = self._get_actual_column_values("entity_business_units", "business_unit")
            real_estate_types = self._get_actual_column_values("entity_business_units", "additional_mapping")
        except:
            business_units = ['Skydive Dubai', 'Five Guys', 'Leasing']
            real_estate_types = ['Residential', 'Commercial', 'Land', 'Retail']
        
        prompt_parts.append(f"""You are an expert SQL query planner for Azure SQL Server financial database. Create a detailed execution plan for the user's question.

AZURE SQL SERVER DATABASE SCHEMA:
================================

1. FINANCIAL_DATA TABLE (Main fact table - contains all financial transactions):
   Primary Key: [financial_data_id] BIGINT
   
   Time Dimensions:
   • [year] INT - Year as integer (2023, 2024, etc.)
   • [month] NVARCHAR(10) - Month in 'YYYY-MM' format ('2023-01', '2023-02', etc.)
   
   Version & Scenario:
   • [version] NVARCHAR(20) - Data version ('Actual', 'Budget', 'Forecast')
   • [scenario] NVARCHAR(50) - Scenario name (usually 'Working Version')
   • [currency] NVARCHAR(10) - Currency code ('AED')
   
   Organization Hierarchy:
   • [entity] NVARCHAR(100) - Legal entity name (e.g., 'Skydive Dubai LLC')
   • [gl_accounts] INT - General ledger account code
   • [department] NVARCHAR(100) - Department name
   • [location] NVARCHAR(100) - Physical location
   • [property] NVARCHAR(100) - Property identifier
   • [project] NVARCHAR(100) - Project name
   • [job_assignment] NVARCHAR(50) - Job assignment
   
   Measures:
   • [measure] NVARCHAR(20) - Measure type (always 'Amount')
   • [value] DECIMAL(28,6) - Financial amount
   • [created_date] DATETIME2 - Record creation timestamp

2. GL_ACCOUNTS TABLE (Chart of accounts - defines account categories):
   Primary Key: [gl_account_id] INT
   
   • [gl_accounts] INT - Account code (links to financial_data)
   • [gl_description] NVARCHAR(255) - Account description
   • [pl_main_category] NVARCHAR(100) - P&L main category (e.g., 'Revenue', 'Direct Cost')
   • [pl_sub_category] NVARCHAR(100) - P&L subcategory for detailed classification
   • [created_date] DATETIME2 - Record creation timestamp

3. ENTITY_BUSINESS_UNITS TABLE (Maps entities to business units):
   Primary Key: [entity_id] INT
   
   • [entity] NVARCHAR(100) - Entity name (links to financial_data)
   • [business_unit] NVARCHAR(50) - Business unit (e.g., 'Skydive Dubai', 'Five Guys')
   • [additional_mapping] NVARCHAR(50) - Additional classification (e.g., 'Residential', 'Commercial')
   • [created_date] DATETIME2 - Record creation timestamp

KEY RELATIONSHIPS:
==================
• financial_data.[gl_accounts] → gl_accounts.[gl_accounts]
• financial_data.[entity] → entity_business_units.[entity]

P&L CATEGORY MAPPINGS (from gl_accounts table):
===============================================
• Revenue: [pl_main_category] LIKE '%Revenue%'
• Direct Costs: [pl_main_category] LIKE '%Direct%'
• G&A: [pl_main_category] LIKE '%General%' OR LIKE '%Admin%'
• Payroll: [pl_main_category] LIKE '%Payroll%'
• Marketing: [pl_main_category] LIKE '%Marketing%'
• Corporate Allocation: [pl_main_category] LIKE '%Corporate%'
• Depreciation: [pl_main_category] LIKE '%Depreciation%'
• Other: [pl_main_category] LIKE '%Other%'

FINANCIAL CALCULATIONS:
======================
• Gross Profit = Revenue - Direct Costs
• Total OpEx = G&A + Payroll + Marketing + Corporate Allocation
• EBITDA = Gross Profit - Total OpEx
• Net Profit = EBITDA - Depreciation - Other Expenses

TIME PERIOD EXAMPLES:
====================
• Full Year 2023: [year] = 2023
• Q1 2023: [month] IN ('2023-01', '2023-02', '2023-03')
• May 2023: [month] = '2023-05'
• YTD 2023 (up to May): [month] BETWEEN '2023-01' AND '2023-05'

BUSINESS UNITS (from entity_business_units):
{', '.join(business_units) if business_units else 'Skydive Dubai, Five Guys, Leasing'}

PROPERTY TYPES (additional_mapping):
{', '.join(real_estate_types) if real_estate_types else 'Residential, Commercial, Land, Retail'}""")
        
        # Add current schema if available
        if context_sections.get('database_schema'):
            prompt_parts.append(f"\nCURRENT DATABASE CONTENT:\n{context_sections['database_schema']}")
        
        # Recent conversation context
        if context_sections.get('recent_interactions'):
            prompt_parts.append("\nRECENT CONVERSATION CONTEXT:")
            for interaction in context_sections['recent_interactions'][-2:]:
                prompt_parts.append(f"Previous Q: {interaction.get('user_question', '')}")
                prompt_parts.append(f"Previous SQL: {interaction.get('sql_query', '')}...")
        
        # Current question
        prompt_parts.append(f"\nUSER QUESTION: {question}")
        
        prompt_parts.append("""
CREATE EXECUTION PLAN:
=====================
Provide a step-by-step plan with these sections:

1. **Question Analysis**: What metrics/data is the user asking for?
2. **Time Period**: Identify specific time filters needed
3. **Entity/Business Unit Scope**: Which entities or business units are involved?
4. **Required Tables**: Which tables need to be joined?
5. **P&L Categories**: Which account categories are needed?
6. **Calculations**: What calculations need to be performed?
7. **Grouping**: How should results be grouped?
8. **Filters**: What WHERE conditions are required?
9. **Expected Output**: What columns should be in the result?

Be specific with Azure SQL Server syntax requirements.""")
        
        prompt_parts.append("""\nNote: 
        "1.Do not use LIMIT clause, use TOP instead. Use square brackets for table/column names.
        2.Do not make views or CTEs, use direct table joins.
        """)
        return "\n".join(prompt_parts)
        
    def _build_optimized_sql_prompt(self, question: str, plan: str, context_sections: Dict[str, Any]) -> str:
        logger.debug("Building optimized SQL prompt.")
        
        prompt_parts = []
        
        # Comprehensive system instruction with working templates
        prompt_parts.append("""You are an expert Azure SQL Server T-SQL query generator. Generate ONLY valid T-SQL queries.

CRITICAL AZURE SQL SERVER RULES:
================================
1. Table/Column names: Use square brackets [table_name], [column_name]
2. String values: Use single quotes 'value'
3. No LIMIT clause - use TOP instead
4. Case-insensitive by default
5. Date/time literals need proper formatting
6. [month] is NVARCHAR storing 'YYYY-MM', [year] is INT

WORKING QUERY TEMPLATES:
=======================

1. SIMPLE AGGREGATION:
```sql
SELECT 
    SUM(fd.[value]) as total_amount
FROM financial_data fd
WHERE fd.[version] = 'Actual'
    AND fd.[year] = 2023
    AND fd.[month] IN ('2023-01', '2023-02', '2023-03');
```

2. REVENUE BY BUSINESS UNIT:
```sql
SELECT 
    ebu.[business_unit],
    SUM(fd.[value]) as revenue
FROM financial_data fd
    INNER JOIN entity_business_units ebu ON fd.[entity] = ebu.[entity]
    INNER JOIN gl_accounts gl ON fd.[gl_accounts] = gl.[gl_accounts]
WHERE fd.[version] = 'Actual'
    AND fd.[year] = 2023
    AND gl.[pl_main_category] LIKE '%Revenue%'
GROUP BY ebu.[business_unit]
ORDER BY revenue DESC;
```

3. COMPLETE P&L ANALYSIS:
```sql
SELECT 
    ebu.[business_unit],
    
    -- Revenue
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%Revenue%' 
        THEN fd.[value] ELSE 0 END) as revenue,
    
    -- Direct Cost
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%Direct%' 
        THEN fd.[value] ELSE 0 END) as direct_cost,
    
    -- Gross Profit
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%Revenue%' 
        THEN fd.[value] 
        WHEN gl.[pl_main_category] LIKE '%Direct%' 
        THEN -fd.[value] 
        ELSE 0 END) as gross_profit,
    
    -- Operating Expenses
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%General%' 
        OR gl.[pl_main_category] LIKE '%Admin%' 
        THEN fd.[value] ELSE 0 END) as g_and_a,
    
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%Payroll%' 
        THEN fd.[value] ELSE 0 END) as payroll,
    
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%Marketing%' 
        THEN fd.[value] ELSE 0 END) as marketing,
    
    -- EBITDA (Revenue - Direct Cost - OpEx)
    SUM(CASE 
        WHEN gl.[pl_main_category] LIKE '%Revenue%' THEN fd.[value]
        WHEN gl.[pl_main_category] LIKE '%Direct%' 
            OR gl.[pl_main_category] LIKE '%General%'
            OR gl.[pl_main_category] LIKE '%Admin%'
            OR gl.[pl_main_category] LIKE '%Payroll%'
            OR gl.[pl_main_category] LIKE '%Marketing%'
            OR gl.[pl_main_category] LIKE '%Corporate%' THEN -fd.[value]
        ELSE 0 END) as ebitda

FROM financial_data fd
    INNER JOIN gl_accounts gl ON fd.[gl_accounts] = gl.[gl_accounts]
    INNER JOIN entity_business_units ebu ON fd.[entity] = ebu.[entity]
WHERE fd.[version] = 'Actual'
    AND fd.[year] = 2023
    AND fd.[month] BETWEEN '2023-01' AND '2023-12'
GROUP BY ebu.[business_unit]
ORDER BY ebu.[business_unit];
```

4. MONTHLY TREND ANALYSIS:
```sql
SELECT 
    fd.[month],
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%Revenue%' 
        THEN fd.[value] ELSE 0 END) as revenue,
    SUM(CASE WHEN gl.[pl_main_category] LIKE '%Direct%' 
        THEN fd.[value] ELSE 0 END) as direct_cost
FROM financial_data fd
    INNER JOIN gl_accounts gl ON fd.[gl_accounts] = gl.[gl_accounts]
WHERE fd.[version] = 'Actual'
    AND fd.[year] = 2023
GROUP BY fd.[month]
ORDER BY fd.[month];
```

5. FILTERING EXAMPLES:
```sql
-- By Business Unit
WHERE ebu.[business_unit] = 'Skydive Dubai'

-- By Property Type
WHERE ebu.[additional_mapping] = 'Residential'

-- By Time Period (remember: [month] is NVARCHAR 'YYYY-MM', [year] is INT)
WHERE fd.[year] = 2023 AND fd.[month] = '2023-05'  -- May 2023
WHERE fd.[year] = 2023 AND fd.[month] IN ('2023-01', '2023-02', '2023-03')  -- Q1 2023
WHERE fd.[year] = 2023 AND fd.[month] BETWEEN '2023-01' AND '2023-06'  -- H1 2023

-- By Entity
WHERE fd.[entity] = 'Skydive Dubai LLC'

-- By Department
WHERE fd.[department] = 'Operations'
```""")
        
        # Add execution plan
        prompt_parts.append(f"\nEXECUTION PLAN:\n{plan}")
        
        # Add recent context if available
        if context_sections.get('recent_interactions'):
            prompt_parts.append("\nRECENT QUERIES FOR CONTEXT:")
            for interaction in context_sections['recent_interactions'][-1:]:
                prompt_parts.append(f"Previous SQL: {interaction.get('sql_query', '')}...")
        
        # Current question
        prompt_parts.append(f"\nCURRENT QUESTION: {question}")
        
        prompt_parts.append("""
GENERATE SQL QUERY:
==================
1. Follow the execution plan exactly
2. Use appropriate template from above
3. Include proper JOINs (use INNER JOIN for required tables)
4. Add WHERE conditions for version='Actual' and appropriate time filters
5. Remember: [month] is NVARCHAR ('YYYY-MM'), [year] is INT
6. Use GROUP BY for all non-aggregated columns
7. Add ORDER BY for better readability
8. DO NOT include semicolon at the end

RESPONSE FORMAT:
```sql
[Your T-SQL query here without semicolon]
```

EXPLANATION:
[Brief explanation of the query logic and any calculations]""")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str) -> Tuple[str, str]:
        logger.debug("Parsing response from LLM for SQL and explanation.")
        logger.debug(f"Raw LLM response: {response}...")
        # Look for SQL code blocks first
        sql_blocks = re.findall(r"```sql(.*?)```", response, re.DOTALL | re.IGNORECASE)
        
        if sql_blocks:
            # Extract the SQL from the first code block
            sql_query = sql_blocks[0].strip()
            
            # Find the explanation section
            explanation_match = re.search(r"EXPLANATION:\s*(.*?)(?:\n\n|\Z)", response, re.DOTALL | re.IGNORECASE)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
            else:
                # Try to find explanation after the SQL block
                parts = response.split("```", 2)
                if len(parts) > 2:
                    explanation = parts[2].strip()
                    # Remove "EXPLANATION:" prefix if present
                    explanation = re.sub(r"^EXPLANATION:\s*", "", explanation, flags=re.IGNORECASE)
                else:
                    explanation = "SQL query generated successfully."
        else:
            # If no SQL code blocks, try to find SQL statements
            lines = response.split('\n')
            sql_lines = []
            explanation_lines = []
            
            in_sql = False
            for line in lines:
                line_stripped = line.strip().upper()
                # Check for SQL statement start
                if (line_stripped.startswith('SELECT') or 
                    line_stripped.startswith('WITH') or 
                    in_sql):
                    in_sql = True
                    sql_lines.append(line)
                    # Check for end of SQL statement
                    if line.strip().endswith(';'):
                        in_sql = False
                elif not in_sql:
                    explanation_lines.append(line)
            
            if sql_lines:
                sql_query = '\n'.join(sql_lines)
                explanation = '\n'.join(explanation_lines).strip()
                # Clean up explanation
                explanation = re.sub(r"^EXPLANATION:\s*", "", explanation, flags=re.IGNORECASE)
                if not explanation:
                    explanation = "SQL query generated successfully."
            else:
                # No clear SQL found, return the whole thing as explanation
                sql_query = ""
                explanation = response.strip()
        
        # Clean up the SQL query
        sql_query = self._clean_sql_query(sql_query)
        
        logger.debug(f"Parsed SQL: {sql_query}...")
        logger.debug(f"Parsed explanation: {explanation}...")
        return sql_query, explanation
    
    def _clean_sql_query(self, sql_query: str) -> str:
        logger.debug(f"Cleaning SQL query: {sql_query}...")
        if not sql_query:
            return sql_query
            
        # Remove extra whitespace and normalize
        sql_query = re.sub(r'\s+', ' ', sql_query.strip())
        
        # Remove comments that might interfere
        sql_query = re.sub(r'--.*', '', sql_query)
        
        # Remove any trailing semicolons with spaces
        sql_query = sql_query.rstrip(' ;').strip()
        
        # Add a single semicolon at the end
        if not sql_query.endswith(';'):
            sql_query += ';'
            
        logger.debug(f"Cleaned SQL query: {sql_query}...")
        return sql_query
    
    def validate_sql_syntax(self, sql_query: str) -> Tuple[bool, str]:
        logger.info("Validating SQL syntax.")
        logger.debug(f"Validating SQL: {sql_query}...")
        try:
            # Basic checks first
            if not sql_query.strip():
                return False, "Empty query"
            
            if not sql_query.strip().upper().startswith(('SELECT', 'WITH')):
                return False, "Query must start with SELECT or WITH"
            
            # Remove the semicolon for validation - Azure SQL parseonly doesn't like it
            query_for_validation = sql_query.rstrip(';').strip()
            
            # For Azure SQL Server, we can't use EXPLAIN QUERY PLAN
            # Instead, we'll use SET PARSEONLY ON to validate syntax
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            try:
                # Enable parse-only mode
                cursor.execute("SET PARSEONLY ON")
                # Try to parse the query
                cursor.execute(query_for_validation)
                # Disable parse-only mode
                cursor.execute("SET PARSEONLY OFF")
                logger.info("SQL syntax is valid.")
                return True, "Query syntax is valid"
            except Exception as e:
                cursor.execute("SET PARSEONLY OFF")
                logger.warning(f"SQL syntax validation failed: {str(e)}")
                raise e
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"SQL validation error: {error_msg}")
            # Clean up error message to remove driver details
            # Extract just the SQL Server error message
            if '[Microsoft][ODBC Driver' in error_msg:
                # Extract the actual error message
                match = re.search(r'\[SQL Server\](.*?)(\(\d+\))', error_msg)
                if match:
                    error_msg = match.group(1).strip()
            
            error_msg_lower = error_msg.lower()
            
            # Provide specific guidance for common errors
            if "invalid column name" in error_msg_lower:
                # Extract column name if possible
                col_match = re.search(r"'([^']+)'", error_msg)
                col_name = col_match.group(1) if col_match else "unknown"
                return False, f"Column '{col_name}' not found. Check column names and use square brackets."
            elif "invalid object name" in error_msg_lower:
                # Extract table name if possible
                table_match = re.search(r"'([^']+)'", error_msg)
                table_name = table_match.group(1) if table_match else "unknown"
                return False, f"Table '{table_name}' not found. Check table names."
            elif "incorrect syntax near" in error_msg_lower:
                # Extract the problematic syntax
                syntax_match = re.search(r"near '([^']+)'", error_msg_lower)
                near_text = syntax_match.group(1) if syntax_match else "unknown"
                if near_text == ';':
                    return False, "Remove semicolon from the query"
                elif near_text == ',':
                    return False, "Check for extra or missing commas in the query"
                else:
                    return False, f"Syntax error near '{near_text}'"
            elif "conversion failed" in error_msg_lower:
                if "nvarchar" in error_msg_lower and "int" in error_msg_lower:
                    return False, "Data type mismatch: [month] is NVARCHAR ('YYYY-MM'), not INT"
                else:
                    return False, f"Data type conversion error: {error_msg}"
            else:
                # Generic error - clean it up
                return False, f"SQL error: {error_msg}"
    
    def _parse_fix_response(self, response: str) -> Tuple[str, str]:
        logger.debug("Parsing fix response from LLM.")
        logger.debug(f"Raw fix response: {response}...")
        # Look for SQL code blocks first
        sql_blocks = re.findall(r"```sql(.*?)```", response, re.DOTALL | re.IGNORECASE)
        if sql_blocks:
            # Extract the SQL from the first code block
            fixed_query = sql_blocks[0].strip()
            
            # Find the explanation section
            explanation_match = re.search(r"EXPLANATION:\s*(.*?)(?:\n\n|\Z)", response, re.DOTALL | re.IGNORECASE)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
            else:
                # Try to find explanation after the SQL block
                parts = response.split("```", 2)
                if len(parts) > 2:
                    explanation = parts[2].strip()
                    # Remove "EXPLANATION:" prefix if present
                    explanation = re.sub(r"^EXPLANATION:\s*", "", explanation, flags=re.IGNORECASE)
                else:
                    explanation = "SQL query fixed successfully."
        else:
            # If no SQL code blocks, try to find SQL statements
            lines = response.split('\n')
            sql_lines = []
            explanation_lines = []

            in_sql = False
            for line in lines:
                line_stripped = line.strip().upper()
                # Check for SQL statement start
                if (line_stripped.startswith('SELECT') or 
                    line_stripped.startswith('WITH') or 
                    in_sql
                ):
                    in_sql = True
                    sql_lines.append(line)
                    # Check for end of SQL statement
                    if line.strip().endswith(';'):
                        in_sql = False
                elif not in_sql:
                    explanation_lines.append(line)
            if sql_lines:
                fixed_query = '\n'.join(sql_lines)
                explanation = '\n'.join(explanation_lines).strip()
                # Clean up explanation
                explanation = re.sub(r"^EXPLANATION:\s*", "", explanation, flags=re.IGNORECASE)
                if not explanation:
                    explanation = "SQL query fixed successfully."
            else:
                # No clear SQL found, return the whole thing as explanation
                fixed_query = ""
                explanation = response.strip()
        # Clean up the fixed SQL query
        fixed_query = self._clean_sql_query(fixed_query)
        logger.debug(f"Parsed fixed SQL: {fixed_query}...")
        logger.debug(f"Parsed fix explanation: {explanation}...")
        return fixed_query, explanation
    
    def fix_sql_query(self, original_query: str, error_message: str, original_question: str, max_attempts: int = 3) -> Tuple[str, str, bool]:
        for attempt in range(max_attempts):
            logger.info(f"Query Fix Attempt {attempt + 1}/{max_attempts}")
            logger.debug(f"Original query: {original_query}...")
            logger.debug(f"Error message: {error_message}")
            # Build query fixer prompt
            fix_prompt = self._build_query_fixer_prompt(
                original_query, 
                error_message, 
                original_question,
                attempt
            )
            
            try:
                # Generate fix using Azure OpenAI
                response = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert Azure SQL Server query debugger. Fix SQL queries that have errors."
                        },
                        {
                            "role": "user",
                            "content": fix_prompt
                        }
                    ],
                    model=self.deployment,
                    temperature=0.4,
                    max_tokens=1024,
                    top_p=0.9
                )
                
                if response.choices and response.choices[0].message.content:
                    # Parse the fixed query
                    fixed_query, fix_explanation = self._parse_fix_response(response.choices[0].message.content)
                    logger.debug(f"Fixed query attempt {attempt+1}: {fixed_query}...")
                    logger.debug(f"Fix explanation: {fix_explanation}...")
                    if fixed_query:
                        # Test the fixed query
                        is_valid, validation_message = self.validate_sql_syntax(fixed_query)
                        logger.debug(f"Validation result: {is_valid}, message: {validation_message}")
                        if is_valid:
                            try:
                                # Execute the fixed query to ensure it runs
                                data = self.db_manager.execute_query(fixed_query)
                                logger.info(f"Fixed query executed successfully on attempt {attempt+1}")
                            except Exception as e:
                                validation_message = str(e)
                                logger.warning(f"Execution of fixed query failed: {validation_message}")
                                is_valid = False
                        if is_valid:
                            logger.info(f"Query fixed successfully on attempt {attempt + 1}")
                            print(f"✅ Query fixed successfully on attempt {attempt + 1}")
                            return fixed_query, fix_explanation, True
                        else:
                            logger.warning(f"Fix attempt {attempt + 1} still has errors: {validation_message}")
                            print(f"❌ Fix attempt {attempt + 1} still has errors: {validation_message}")
                            error_message = validation_message
                            original_query = fixed_query
            except Exception as e:
                logger.error(f"Fix attempt {attempt + 1} failed: {str(e)}")
                print(f"❌ Fix attempt {attempt + 1} failed: {str(e)}")
                continue
        logger.error(f"Could not fix query after {max_attempts} attempts")
        print(f"❌ Could not fix query after {max_attempts} attempts")
        return original_query, "Could not fix the query automatically", False

    def _build_query_fixer_prompt(self, failed_query: str, error_message: str, original_question: str, attempt_number: int) -> str:
        logger.debug("Building query fixer prompt.")
        
        prompt_parts = []
        
        prompt_parts.append(f"""Fix this Azure SQL Server query that has an error.

ORIGINAL QUESTION: {original_question}

FAILED QUERY:
{failed_query}

ERROR MESSAGE:
{error_message}

DATABASE SCHEMA REMINDERS:
=========================
FINANCIAL_DATA columns:
- [year] INT (not string!) - Use: [year] = 2023
- [month] NVARCHAR(10) - Format 'YYYY-MM' - Use: [month] = '2023-01' or [month] IN ('2023-01', '2023-02')
- [version], [entity], [department], etc. are NVARCHAR - need quotes
- [gl_accounts] INT - no quotes needed
- [value] DECIMAL(28,6)

GL_ACCOUNTS columns:
- [gl_accounts] INT
- [pl_main_category] NVARCHAR - Use LIKE for matching

ENTITY_BUSINESS_UNITS columns:
- [entity] NVARCHAR
- [business_unit] NVARCHAR
- [additional_mapping] NVARCHAR

COMMON FIXES:
============
1. Data Type Issues:
   ❌ [month] IN (1, 2, 3)
   ✅ [month] IN ('2023-01', '2023-02', '2023-03')
   
   ❌ [year] = '2023'
   ✅ [year] = 2023

2. Syntax Issues:
   ❌ Query ending with semicolon in validation
   ✅ Remove semicolon for validation
   
   ❌ Missing comma in SELECT list
   ✅ Add comma between columns
   
   ❌ Extra comma before FROM
   ✅ Remove trailing comma

3. Column Names:
   ❌ Wrong case or missing brackets
   ✅ Use [column_name] with correct case

4. Table Joins:
   ❌ Missing required joins
   ✅ Add INNER JOIN for gl_accounts and entity_business_units

5. GROUP BY:
   ❌ Missing non-aggregated columns
   ✅ Include all SELECT columns that aren't in SUM/COUNT/etc.

RESPONSE FORMAT:
===============
```sql
[Fixed query WITHOUT semicolon]
```

""")
        return "\n".join(prompt_parts)

    def get_data(
        self,
        question: str, 
        context: Optional[Dict[str, Any]] = None, 
    ) -> Tuple[str, str]:
        logger.info(f"Getting data for question: {question}")
        # Initialize variables
        sql_results = None
        sql_query = ""
        explanation = ""
        
        # Generate execution plan
        plan = self.generate_plan(question, context)
        logger.debug(f"Generated plan: {plan}...")
        # Generate SQL query using the plan
        sql_query, explanation = self.generate_sql(question, plan, context)
        logger.debug(f"Generated SQL: {sql_query}...")
        logger.debug(f"SQL explanation: {explanation}...")
        if not sql_query:
            for attempt in range(3):
                logger.warning(f"Retrying SQL generation, attempt {attempt + 1}/3")
                print(f"🔄 Retrying SQL generation, attempt {attempt + 1}/3")
                plan = self.generate_plan(question, context)
                logger.debug(f"Retry plan: {plan}...")
                sql_query, explanation = self.generate_sql(question, plan, context)
                logger.debug(f"Retry SQL: {sql_query}...")
                logger.debug(f"Retry explanation: {explanation}...")
                if sql_query:
                    break
            else:
                logger.error("Failed to generate SQL query after multiple attempts")
                return None, "", "Failed to generate SQL query after multiple attempts"
        is_valid, validation_error = self.validate_sql_syntax(sql_query)
        logger.debug(f"SQL validation result: {is_valid}, message: {validation_error}")
        if not is_valid:
            logger.warning(f"SQL validation failed: {validation_error}")
            print(f"⚠️ SQL validation failed: {validation_error}")
            fixed_query, fix_explanation, is_fixed = self.fix_sql_query(
                sql_query, 
                validation_error, 
                question
            )
            logger.debug(f"Fixed SQL: {fixed_query}...")
            logger.debug(f"Fix explanation: {fix_explanation}...")
            logger.debug(f"Is fixed: {is_fixed}")
            if is_fixed:
                sql_query = fixed_query
                explanation = fix_explanation
                logger.info("SQL query fixed successfully")
                print("✅ SQL query fixed successfully")
            else:
                logger.error(f"SQL validation failed: {validation_error}")
                return None, sql_query, f"SQL validation failed: {validation_error}"
        try:
            sql_results = self.db_manager.execute_query(sql_query)
            logger.info("SQL query executed successfully")
            logger.debug(f"SQL results: {str(sql_results.head(3)) if hasattr(sql_results, 'head') else str(sql_results)}")
            print("✅ SQL query executed successfully")
        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}")
            print(f"❌ SQL execution failed: {str(e)}")
            fixed_query, fix_explanation, is_fixed = self.fix_sql_query(
                sql_query, 
                str(e), 
                question
            )
            logger.debug(f"Fixed SQL after execution error: {fixed_query}...")
            logger.debug(f"Fix explanation after execution error: {fix_explanation}...")
            logger.debug(f"Is fixed after execution error: {is_fixed}")
            if is_fixed:
                try:
                    sql_results = self.db_manager.execute_query(fixed_query)
                    sql_query = fixed_query
                    explanation = fix_explanation
                    logger.info("Fixed SQL query executed successfully")
                    logger.debug(f"Fixed SQL results: {str(sql_results.head(3)) if hasattr(sql_results, 'head') else str(sql_results)}")
                    print("✅ Fixed SQL query executed successfully")
                except Exception as retry_error:
                    logger.error(f"Error executing fixed SQL query: {str(retry_error)}")
                    return None, fixed_query, f"Error executing fixed SQL query: {str(retry_error)}"
            else:
                logger.error(f"Error executing SQL query: {str(e)}")
                return None, sql_query, f"Error executing SQL query: {str(e)}"
        except Exception as e:
            print(f"❌ SQL execution failed: {str(e)}")
            fixed_query, fix_explanation, is_fixed = self.fix_sql_query(
                sql_query, 
                str(e), 
                question
            )
            if is_fixed:
                try:
                    sql_results = self.db_manager.execute_query(fixed_query)
                    sql_query = fixed_query
                    explanation = fix_explanation
                    print("✅ Fixed SQL query executed successfully")
                except Exception as retry_error:
                    return None, fixed_query, f"Error executing fixed SQL query: {str(retry_error)}"
            else:
                return None, sql_query, f"Error executing SQL query: {str(e)}"
        
        return sql_results, sql_query, explanation
    