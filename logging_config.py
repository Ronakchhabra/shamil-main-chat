import logging
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError


class AzureBlobDirectHandler(logging.Handler):
    """
    A simple handler that writes logs directly to Azure Blob Storage.
    Creates hourly log files and appends to them in real-time.
    """
    
    def __init__(self,
                 connection_string=None,
                 account_url=None,
                 credential=None,
                 container_name='logs',
                 blob_prefix='app'):
        """
        Initialize the Azure Blob handler.
        
        Parameters:
        connection_string: Azure Storage connection string
        account_url: Azure Storage account URL
        credential: Azure credential object
        container_name: Name of the blob container
        blob_prefix: Prefix for blob names
        """
        super().__init__()
        
        self.container_name = container_name
        self.blob_prefix = blob_prefix
        self.current_blob_name = None
        self.current_blob_client = None
        self.current_hour = None
        
        # Initialize BlobServiceClient
        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif account_url:
            if credential:
                self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
            else:
                self.blob_service_client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        else:
            raise ValueError("Either connection_string or account_url must be provided")
        
        # Ensure container exists
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Create the container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                print(f"Created container: {self.container_name}")
        except ResourceExistsError:
            pass
        except Exception as e:
            print(f"Error ensuring container exists: {e}")
    
    def _get_blob_client(self):
        """Get the blob client for the current hour."""
        current_time = datetime.utcnow()
        current_hour = current_time.strftime('%Y%m%d_%H')
        
        # Check if we need a new blob (new hour)
        if self.current_hour != current_hour:
            self.current_hour = current_hour
            
            # Generate new blob name
            year = current_time.strftime('%Y')
            month = current_time.strftime('%m')
            day = current_time.strftime('%d')
            self.current_blob_name = f"logs/{year}/{month}/{day}/{self.blob_prefix}_{current_hour}.log"
            
            # Get blob client
            self.current_blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=self.current_blob_name
            )
        
        return self.current_blob_client
    
    def emit(self, record):
        """Emit a log record to Azure Blob Storage."""
        # Skip Azure SDK logs to prevent infinite loops
        if record.name.startswith('azure'):
            return
            
        try:
            # Format the log record
            log_entry = self.format(record) + '\n'
            
            # Get blob client for current hour
            blob_client = self._get_blob_client()
            
            # Try to append to existing blob
            try:
                # For append blobs
                blob_client.append_block(log_entry.encode('utf-8'))
            except Exception:
                # If not an append blob or doesn't exist, try different approach
                try:
                    # Create as append blob
                    blob_client.create_append_blob(
                        content_settings=ContentSettings(content_type='text/plain')
                    )
                    blob_client.append_block(log_entry.encode('utf-8'))
                except ResourceExistsError:
                    # Blob exists but isn't append blob, download and re-upload
                    try:
                        existing_content = blob_client.download_blob().readall()
                    except:
                        existing_content = b""
                    
                    new_content = existing_content + log_entry.encode('utf-8')
                    blob_client.upload_blob(
                        new_content,
                        overwrite=True,
                        content_settings=ContentSettings(content_type='text/plain')
                    )
                
        except Exception as e:
            # Don't use logging to prevent recursion
            print(f"Error writing to blob: {e}")
            # Don't call handleError to prevent potential loops


def setup_logging(
    log_level=logging.INFO,
    log_to_file=True,
    log_to_console=True,
    log_to_blob=True,
    # Azure configuration
    account_url=None,
    connection_string=None,
    container_name='logs',
    credential=None,
    # Local file configuration
    log_dir="logs"
):
    """
    Setup logging configuration with Azure Blob Storage support.
    
    Parameters:
    log_level: Logging level (default: INFO)
    log_to_file: Whether to log to local file (default: True)
    log_to_console: Whether to log to console (default: True)
    log_to_blob: Whether to log to Azure Blob Storage (default: True)
    account_url: Azure Storage account URL
    connection_string: Azure Storage connection string
    container_name: Blob container name for logs
    credential: Azure credential object
    log_dir: Local directory for log files
    """
    
    # CRITICAL: Prevent Azure SDK logs from creating infinite loops
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)
    logging.getLogger('azure.core').setLevel(logging.WARNING)
    
    # Create logs directory if needed
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
    
    # Generate base log filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H")
    log_file = os.path.join(log_dir, f"shamal_chatbot_{timestamp}.log")
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handlers = []
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # Local file handler
    if log_to_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Azure Blob Storage handler
    if log_to_blob and (account_url or connection_string):
        try:
            blob_handler = AzureBlobDirectHandler(
                connection_string=connection_string,
                account_url=account_url,
                credential=credential,
                container_name=container_name,
                blob_prefix='chatbot'
            )
            blob_handler.setLevel(log_level)
            blob_handler.setFormatter(formatter)
            handlers.append(blob_handler)
            
            print(f"Azure Blob Storage handler initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize Azure Blob Storage handler: {e}")
            import traceback
            traceback.print_exc()
    
    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Prevent duplicate logging
    root_logger.propagate = False
    
    # Log initialization message
    if handlers:
        logging.info(f"Logging initialized. Handlers: {[type(h).__name__ for h in handlers]}")
        logging.info(f"Azure Blob Storage enabled: {log_to_blob and (account_url or connection_string)}")


# Example usage
if __name__ == "__main__":
    import os
    
    # Example 1: Using connection string
    connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    if connection_string:
        setup_logging(
            log_level=logging.INFO,
            connection_string=connection_string,
            container_name='logs',
            log_to_console=True,
            log_to_blob=True
        )
    else:
        print("Set AZURE_STORAGE_CONNECTION_STRING environment variable")
        setup_logging(
            log_level=logging.INFO,
            log_to_console=True,
            log_to_blob=False
        )
    
    # Test logging
    logger = logging.getLogger(__name__)
    logger.info("Application started")
    logger.warning("This is a warning")
    logger.error("This is an error")
    
    # Test with different loggers
    app_logger = logging.getLogger('myapp')
    app_logger.info("App specific log entry")
    
    db_logger = logging.getLogger('database')
    db_logger.debug("Database connection established")