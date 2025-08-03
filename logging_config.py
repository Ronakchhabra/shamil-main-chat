import logging
import os
import threading
import queue
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
import time


class AzureBlobTimedRotatingHandler(TimedRotatingFileHandler):
    """
    A handler that writes logs to Azure Blob Storage with hourly rotation.
    Extends TimedRotatingFileHandler to upload completed log files to Azure Blob Storage.
    """
    
    def __init__(self, 
                 filename,
                 account_url=None,
                 container_name='logs',
                 credential=None,
                 connection_string=None,
                 when='H',  # Hourly rotation by default
                 interval=1,
                 backupCount=0,
                 encoding=None,
                 delay=False,
                 utc=True,
                 atTime=None,
                 errors=None,
                 upload_queue_size=100):
        """
        Initialize the Azure Blob Storage timed rotating handler.
        
        Parameters:
        filename: Base filename for logs
        account_url: Azure Storage account URL (e.g., https://<account>.blob.core.windows.net)
        container_name: Name of the blob container for logs
        credential: Azure credential object (DefaultAzureCredential, managed identity, etc.)
        connection_string: Alternative to account_url+credential, provide full connection string
        when: Type of interval ('H' for hours, 'D' for days, etc.)
        interval: Rotation interval
        backupCount: Number of backups to keep locally (0 = unlimited)
        encoding: File encoding
        delay: Delay file opening until first emit
        utc: Use UTC time for rotation
        atTime: Specific time for rotation
        errors: Error handling mode
        upload_queue_size: Size of the upload queue
        """
        # Initialize the parent TimedRotatingFileHandler
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime, errors)
        
        # Azure Blob Storage configuration
        self.container_name = container_name
        self.upload_queue = queue.Queue(maxsize=upload_queue_size)
        self.upload_thread = None
        self.stop_upload_thread = threading.Event()
        
        # Initialize BlobServiceClient
        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif account_url and credential:
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        elif account_url:
            # Use DefaultAzureCredential if no credential provided
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        else:
            raise ValueError("Either connection_string or account_url must be provided")
        
        # Create container if it doesn't exist
        self._ensure_container_exists()
        
        # Start the upload thread
        self._start_upload_thread()
    
    def _ensure_container_exists(self):
        """Create the container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.create_container()
            logging.info(f"Created container: {self.container_name}")
        except ResourceExistsError:
            logging.info(f"Container already exists: {self.container_name}")
        except Exception as e:
            logging.error(f"Error ensuring container exists: {e}")
    
    def _start_upload_thread(self):
        """Start the background thread for uploading logs to Azure."""
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()
    
    def _upload_worker(self):
        """Worker thread that uploads completed log files to Azure Blob Storage."""
        while not self.stop_upload_thread.is_set():
            try:
                # Wait for a file to upload (timeout to check stop signal)
                filepath = self.upload_queue.get(timeout=1)
                if filepath:
                    self._upload_to_blob(filepath)
                    # Delete local file after successful upload
                    try:
                        os.remove(filepath)
                        logging.info(f"Deleted local file: {filepath}")
                    except Exception as e:
                        logging.error(f"Error deleting local file {filepath}: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error in upload worker: {e}")
    
    def _upload_to_blob(self, filepath):
        """Upload a file to Azure Blob Storage."""
        try:
            # Generate blob name with directory structure (e.g., logs/2025/01/app_20250103_14.log)
            timestamp = datetime.utcnow()
            blob_name = self._generate_blob_name(filepath, timestamp)
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            # Upload the file
            with open(filepath, 'rb') as data:
                blob_client.upload_blob(
                    data, 
                    overwrite=True,
                    content_settings=ContentSettings(content_type='text/plain')
                )
            
            logging.info(f"Successfully uploaded {filepath} to blob: {blob_name}")
            
        except Exception as e:
            logging.error(f"Error uploading {filepath} to blob storage: {e}")
            # Re-queue the file for retry
            try:
                self.upload_queue.put(filepath, block=False)
            except queue.Full:
                logging.error(f"Upload queue is full, cannot retry upload for {filepath}")
    
    def _generate_blob_name(self, filepath, timestamp):
        """Generate a blob name with directory structure."""
        basename = os.path.basename(filepath)
        # Create a directory structure: logs/YYYY/MM/DD/filename
        year = timestamp.strftime('%Y')
        month = timestamp.strftime('%m')
        day = timestamp.strftime('%d')
        return f"logs/{year}/{month}/{day}/{basename}"
    
    def doRollover(self):
        """Override doRollover to queue file for upload after rotation."""
        # Get the current log file path before rotation
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Get the filename that will be rotated
        current_time = int(time.time())
        dst_now = time.localtime(current_time)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            time_tuple = time.gmtime(t)
        else:
            time_tuple = time.localtime(t)
            dst_then = time_tuple[-1]
            if dst_now != dst_then:
                if dst_now:
                    addend = 3600
                else:
                    addend = -3600
                time_tuple = time.localtime(t + addend)
        
        # Generate the rotated filename
        dfn = self.rotation_filename(self.baseFilename + "." + time.strftime(self.suffix, time_tuple))
        
        # Perform the rotation
        if os.path.exists(dfn):
            os.remove(dfn)
        
        self.rotate(self.baseFilename, dfn)
        
        # Queue the rotated file for upload
        if os.path.exists(dfn):
            try:
                self.upload_queue.put(dfn, block=False)
                logging.info(f"Queued {dfn} for upload to Azure Blob Storage")
            except queue.Full:
                logging.error(f"Upload queue is full, cannot queue {dfn}")
        
        # Continue with normal rollover process
        if not self.delay:
            self.stream = self._open()
        
        new_rollover_at = self.computeRollover(current_time)
        while new_rollover_at <= current_time:
            new_rollover_at = new_rollover_at + self.interval
        
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dst_at_rollover = time.localtime(new_rollover_at)[-1]
            if dst_now != dst_at_rollover:
                if not dst_now:
                    addend = -3600
                else:
                    addend = 3600
                new_rollover_at += addend
        
        self.rolloverAt = new_rollover_at
    
    def close(self):
        """Close the handler and stop the upload thread."""
        # Stop the upload thread
        self.stop_upload_thread.set()
        if self.upload_thread:
            self.upload_thread.join(timeout=5)
        
        # Upload any remaining files in the queue
        while not self.upload_queue.empty():
            try:
                filepath = self.upload_queue.get_nowait()
                if filepath:
                    self._upload_to_blob(filepath)
            except queue.Empty:
                break
        
        # Call parent close
        super().close()


class AzureBlobAppendHandler(logging.Handler):
    """
    A handler that appends log records directly to an Azure Blob Storage append blob.
    Creates a new blob hourly and appends log records in real-time.
    """
    
    def __init__(self,
                 account_url=None,
                 container_name='logs',
                 blob_prefix='app',
                 credential=None,
                 connection_string=None):
        """
        Initialize the Azure Blob append handler.
        
        Parameters:
        account_url: Azure Storage account URL
        container_name: Name of the blob container
        blob_prefix: Prefix for blob names
        credential: Azure credential object
        connection_string: Alternative to account_url+credential
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
        elif account_url and credential:
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        elif account_url:
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        else:
            raise ValueError("Either connection_string or account_url must be provided")
        
        # Ensure container exists
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Create the container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.create_container()
        except ResourceExistsError:
            pass
        except Exception as e:
            logging.error(f"Error ensuring container exists: {e}")
    
    def _get_or_create_blob(self):
        """Get the current blob client, creating a new one if needed."""
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
            
            # Create append blob if it doesn't exist
            try:
                self.current_blob_client.create_append_blob(
                    content_settings=ContentSettings(content_type='text/plain')
                )
                logging.info(f"Created new append blob: {self.current_blob_name}")
            except ResourceExistsError:
                logging.info(f"Append blob already exists: {self.current_blob_name}")
            except Exception as e:
                logging.error(f"Error creating append blob: {e}")
                raise
        
        return self.current_blob_client
    
    def emit(self, record):
        """Emit a log record to Azure Blob Storage."""
        try:
            # Format the log record
            log_entry = self.format(record) + '\n'
            
            # Get or create the current blob
            blob_client = self._get_or_create_blob()
            
            # Append the log entry
            if blob_client:
                blob_client.append_block(log_entry.encode('utf-8'))
                
        except Exception as e:
            # Avoid infinite recursion by not using logging here
            self.handleError(record)


def setup_logging(
    log_level=logging.INFO,
    log_to_file=True,
    log_to_console=False,
    log_to_blob=True,
    append_to_blob=False,
    # Azure configuration
    account_url=None,
    connection_string=None,
    container_name='logs',
    credential=None,
    # Local file configuration
    local_backup=True,
    log_dir="logs"
):
    """
    Setup logging configuration with Azure Blob Storage support.
    
    Parameters:
    log_level: Logging level (default: INFO)
    log_to_file: Whether to log to local file (default: True)
    log_to_console: Whether to log to console (default: False)
    log_to_blob: Whether to log to Azure Blob Storage (default: True)
    append_to_blob: Use append blob for real-time logging (default: False)
    account_url: Azure Storage account URL
    connection_string: Azure Storage connection string
    container_name: Blob container name for logs
    credential: Azure credential object
    local_backup: Keep local file backup when using blob storage
    log_dir: Local directory for log files
    """
    
    # Create logs directory if needed
    if log_to_file or local_backup:
        os.makedirs(log_dir, exist_ok=True)
    
    # Generate base log filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H")
    log_file = os.path.join(log_dir, f"shamal_chatbot_{timestamp}.log")
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    # Prevent Azure SDK logs from creating infinite loops
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    
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
    
    # Azure Blob Storage handler
    if log_to_blob and (account_url or connection_string):
        try:
            if append_to_blob:
                # Use real-time append blob handler
                blob_handler = AzureBlobAppendHandler(
                    account_url=account_url,
                    container_name=container_name,
                    blob_prefix='chatbot',
                    credential=credential,
                    connection_string=connection_string
                )
            else:
                # Use timed rotating handler with blob upload
                blob_handler = AzureBlobTimedRotatingHandler(
                    filename=log_file,
                    account_url=account_url,
                    container_name=container_name,
                    credential=credential,
                    connection_string=connection_string,
                    when='H',  # Hourly rotation
                    interval=1,
                    backupCount=0 if not local_backup else 24,  # Keep 24 hours locally if backup enabled
                    encoding='utf-8',
                    utc=True
                )
            
            blob_handler.setLevel(log_level)
            blob_handler.setFormatter(formatter)
            handlers.append(blob_handler)
            
        except Exception as e:
            print(f"Failed to initialize Azure Blob Storage handler: {e}")
            # Fall back to file handler
            log_to_file = True
    
    # Local file handler (if not using blob or as backup)
    if log_to_file and not (log_to_blob and (account_url or connection_string)):
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='H',  # Hourly rotation
            interval=1,
            backupCount=24,  # Keep 24 hours of logs
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Prevent duplicate logging
    root_logger.propagate = False
    
    logging.info(f"Logging initialized. Azure Blob Storage: {log_to_blob}, Append mode: {append_to_blob}")
