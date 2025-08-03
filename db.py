import pyodbc
import pandas as pd
import threading
from typing import Dict, List, Any, Optional
import os
import urllib
from dotenv import load_dotenv
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import logging

logger = logging.getLogger(__name__)

load_dotenv()

class DatabaseManager:
    """Thread-safe Azure SQL database manager for multi-table financial analysis."""
    
    def __init__(self):
        """Initialize Azure SQL database manager."""
        self.connection_string = os.getenv('ConnectionString')
        if not self.connection_string:
            logger.error("Database connection string not found. Set ConnectionString in .env file.")
            raise ValueError("Database connection string not found. Set ConnectionString in .env file.")
        logger.info("Initializing DatabaseManager.")
        self._create_sqlalchemy_engine()
        self._local = threading.local()
        logger.info("DatabaseManager initialized.")

    def _create_sqlalchemy_engine(self):
        """Create SQLAlchemy engine from connection string."""
        logger.debug("Creating SQLAlchemy engine.")
        # Parse ODBC connection string
        conn_params = {}
        for param in self.connection_string.split(';'):
            if '=' in param:
                key, value = param.split('=', 1)
                conn_params[key.strip()] = value.strip()
        
        # Extract connection parameters
        server = conn_params.get('Server', '')
        database = conn_params.get('Database', '')
        username = conn_params.get('Uid', '')
        password = conn_params.get('Pwd', '')
        
        params = urllib.parse.quote_plus(os.getenv('ConnectionString', ''))
        conn_str = 'mssql+pyodbc:///?odbc_connect={}'.format(params)
        # Create engine
        self.engine = create_engine(conn_str, pool_pre_ping=True, pool_size=5, max_overflow=10)
        logger.info("SQLAlchemy engine created.")

    def _get_connection(self) -> pyodbc.Connection:
        """Get a thread-local Azure SQL connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            logger.debug("Creating new thread-local pyodbc connection.")
            self._local.connection = pyodbc.connect(
                self.connection_string
            )
            self._local.connection.autocommit = True
            logger.info("Thread-local pyodbc connection established.")
        return self._local.connection

    def get_all_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        logger.info("Fetching all table names from database.")
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = cursor.fetchall()
        table_list = [table[0] for table in tables]
        logger.debug(f"Tables found: {table_list}")
        return table_list

    def get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive metadata for a table."""
        logger.info(f"Fetching metadata for table: {table_name}")
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, table_name)
        columns_info = cursor.fetchall()
        
        # Get row count
        cursor.execute(f'SELECT COUNT(*) FROM [{table_name}]')
        row_count = cursor.fetchone()[0]
        
        # Get primary key information
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = ? AND CONSTRAINT_NAME LIKE '%PK%'
        """, table_name)
        pk_columns = [row[0] for row in cursor.fetchall()]
        
        # Build metadata structure
        columns = []
        for col in columns_info:
            col_info = {
                "name": col[0],
                "type": col[1],
                "nullable": col[2] == 'YES',
                "primary_key": col[0] in pk_columns,
                "default_value": col[3]
            }
            
            # Get sample values for text columns
            if col[1] in ['varchar', 'nvarchar', 'text', 'ntext'] and col[0] not in pk_columns:
                try:
                    cursor.execute(f"""
                        SELECT DISTINCT TOP 3 [{col[0]}]
                        FROM [{table_name}] 
                        WHERE [{col[0]}] IS NOT NULL 
                    """)
                    sample_values = [row[0] for row in cursor.fetchall()]
                    if sample_values:
                        col_info["sample_values"] = sample_values
                except Exception:
                    pass  # Skip if error getting sample values
            
            columns.append(col_info)
        
        logger.debug(f"Metadata for table {table_name}: {columns}")
        return {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns
        }

    def get_sample_head(self, table_name: str, limit: int = 3) -> pd.DataFrame:
        """Get sample data from table head."""
        logger.info(f"Fetching sample head for table: {table_name}, limit: {limit}")
        query = f'SELECT TOP {limit} * FROM [{table_name}]'
        return self.execute_query(query)

    def get_database_metadata_for_llm(self) -> str:
        """Get comprehensive database metadata formatted for LLM consumption."""
        logger.info("Fetching database metadata for LLM.")
        tables = self.get_all_tables()
        if not tables:
            logger.warning("No tables found in database.")
            return "No tables found in database."
        metadata_parts = []
        metadata_parts.append("DATABASE SCHEMA:")
        metadata_parts.append("=" * 50)
        for table_name in tables:
            try:
                table_meta = self.get_table_metadata(table_name)
                sample_data = self.get_sample_head(table_name, 2)
                metadata_parts.append(f"\nTable: {table_name} ({table_meta['row_count']} rows)")
                metadata_parts.append("Columns:")
                for col in table_meta['columns']:
                    col_desc = f"  - {col['name']} ({col['type']})"
                    if col['primary_key']:
                        col_desc += " [PRIMARY KEY]"
                    if not col['nullable']:
                        col_desc += " [NOT NULL]"
                    metadata_parts.append(col_desc)
                    if 'sample_values' in col and col['sample_values']:
                        sample_str = ", ".join(map(str, col['sample_values'][:3]))
                        metadata_parts.append(f"    Sample values: {sample_str}")
                if not sample_data.empty:
                    metadata_parts.append("\n  Sample records:")
                    for i, (_, record) in enumerate(sample_data.iterrows()):
                        record_dict = record.to_dict()
                        metadata_parts.append(f"    Record {i+1}: {record_dict}")
            except Exception as e:
                logger.error(f"Error fetching metadata for table {table_name}: {str(e)}")
                metadata_parts.append(f"\nTable: {table_name} (Error: {str(e)})")
        return "\n".join(metadata_parts)

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame."""
        logger.info(f"Executing query: {query[:200]}...")
        try:
            result = pd.read_sql(query, self.engine)
            logger.debug(f"Query executed successfully. Result shape: {result.shape}")
            return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            print(f"Error executing query: {e}")
            raise

    def close_connection(self):
        """Close the thread-local connection."""
        logger.info("Closing database connections.")
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.debug("Thread-local pyodbc connection closed.")
        if hasattr(self, 'engine'):
            self.engine.dispose()
            logger.debug("SQLAlchemy engine disposed.")

    def __del__(self):
        """Cleanup connections when object is destroyed."""
        try:
            self.close_connection()
        except Exception as e:
            logger.error(f"Error during DatabaseManager cleanup: {str(e)}")
            pass