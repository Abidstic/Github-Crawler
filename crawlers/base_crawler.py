import abc
import os
import logging
from typing import Dict, Any, List, Optional
from config import config
from utils import write_json_file_async, ensure_folder_structure
from progress_tracker import get_progress_tracker
from checkpoint_manager import CheckpointManager

class BaseCrawler(abc.ABC):
    """Abstract base class for all GitHub crawlers"""
    
    def __init__(self, repo_owner: str, repo_name: str, github_client, checkpoint_manager: CheckpointManager):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_client = github_client
        self.checkpoint_manager = checkpoint_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Folder structure
        self.folder_name = f"{repo_owner}-{repo_name}"
        self.base_folder_path = f"{config.base_folder}/{self.folder_name}"
        
        # Progress tracking
        try:
            self.progress_tracker = get_progress_tracker()
        except RuntimeError:
            self.progress_tracker = None
    
    @property
    @abc.abstractmethod
    def crawler_name(self) -> str:
        """Name of this crawler for progress tracking"""
        pass
    
    @property
    @abc.abstractmethod
    def output_folder_path(self) -> str:
        """Folder path where this crawler saves data"""
        pass
    
    @abc.abstractmethod
    async def estimate_total_items(self) -> int:
        """Estimate total number of items to crawl"""
        pass
    
    @abc.abstractmethod
    async def crawl_implementation(self) -> None:
        """Actual crawling implementation"""
        pass
    
    async def crawl(self) -> None:
        """Main crawling method with progress tracking and checkpointing"""
        # Check if already completed
        if self.checkpoint_manager.is_crawler_completed(self.crawler_name):
            self.logger.info(f"{self.crawler_name} already completed, skipping")
            return
        
        # Update progress tracker
        if self.progress_tracker:
            self.progress_tracker.update_operation(f"Starting {self.crawler_name}")
        
        try:
            # Estimate total items (for initial display)
            estimated_total = await self.estimate_total_items()
            
            # Initialize progress tracking with estimate
            if self.progress_tracker:
                self.progress_tracker.init_crawler(self.crawler_name, estimated_total)
                self.progress_tracker.update_operation(f"Crawling {self.crawler_name}")
            
            # Ensure output folder exists
            ensure_folder_structure(self.base_folder_path)
            os.makedirs(self.output_folder_path, exist_ok=True)
            
            # Run the actual crawling implementation
            await self.crawl_implementation()
            
            # Mark as completed
            self.checkpoint_manager.complete_crawler(self.crawler_name)
            
            if self.progress_tracker:
                self.progress_tracker.complete_crawler(self.crawler_name)
            
            self.logger.info(f"{self.crawler_name} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to crawl {self.crawler_name}: {e}")
            raise
    
    def update_progress(self, completed: int = 0, failed: int = 0, skipped: int = 0, 
                       failed_item: str = None, skipped_item: str = None):
        """Update progress in both checkpoint and progress tracker"""
        
        # Update checkpoint
        if failed_item or skipped_item or completed > 0:
            self.checkpoint_manager.update_crawler_progress(
                self.crawler_name, completed, failed_item, skipped_item
            )
        
        # Update progress tracker with thread safety
        if self.progress_tracker:
            if completed > 0 or failed > 0 or skipped > 0:
                with self.progress_tracker._lock:
                    self.progress_tracker.increment_crawler_progress(
                        self.crawler_name, completed, failed, skipped
                    )
    
    def set_total_and_complete_progress(self, actual_total: int):
        """Set actual total and mark all as completed (for bulk operations)"""
        # Update checkpoint manager
        self.checkpoint_manager.init_crawler(self.crawler_name, actual_total)
        self.checkpoint_manager.update_crawler_progress(self.crawler_name, actual_total)
        
        # Update progress tracker
        if self.progress_tracker:
            self.progress_tracker.init_crawler(self.crawler_name, actual_total)
            self.progress_tracker.update_crawler_progress(
                self.crawler_name, completed=actual_total
            )
    
    async def save_data_async(self, data: Any, file_path: str, item_identifier: str = None):
        """Save data to file with error handling and progress updates"""
        try:
            await write_json_file_async(file_path, data)
            
            if item_identifier:
                self.logger.debug(f"Saved {item_identifier} to {file_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to save data to {file_path}: {e}")
            if self.progress_tracker:
                with self.progress_tracker._lock:
                    self.progress_tracker.increment_crawler_progress(
                        self.crawler_name, failed=1
                    )
            raise
    
    def should_skip_existing(self, file_path: str) -> bool:
        """Check if file already exists and should be skipped"""
        if os.path.exists(file_path):
            if self.progress_tracker:
                with self.progress_tracker._lock:
                    self.progress_tracker.increment_crawler_progress(
                        self.crawler_name, skipped=1
                    )
            return True
        return False
    
    async def process_in_batches(self, items: List[Any], batch_size: int, 
                               process_func, description: str = "Processing"):
        """Process items in batches with progress updates"""
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        for i, batch_start in enumerate(range(0, len(items), batch_size)):
            batch = items[batch_start:batch_start + batch_size]
            
            if self.progress_tracker:
                self.progress_tracker.update_operation(
                    f"{description} batch {i+1}/{total_batches}"
                )
            
            # Process batch
            await process_func(batch)
            
            # Save checkpoint periodically
            if (i + 1) % config.checkpoint_interval == 0:
                self.checkpoint_manager.save_checkpoint()

class BaseListCrawler(BaseCrawler):
    """Base class for crawlers that fetch complete datasets at once"""
    
    @abc.abstractmethod
    def get_api_method(self):
        """Get the GitHub client method to use for this crawler"""
        pass
    
    def get_api_params(self) -> Dict[str, Any]:
        """Get additional parameters for the API call (default: none)"""
        return {}
    
    async def estimate_total_items(self) -> int:
        """Provide initial estimate for display purposes"""
        # Return conservative estimate that will be updated during actual crawling
        return 1000
    
    async def crawl_implementation(self) -> None:
        """Implementation for complete dataset crawling with proper progress tracking"""
        # Get the API method
        method = self.get_api_method()
        
        # Update progress tracker to show we're fetching data
        if self.progress_tracker:
            self.progress_tracker.update_operation(f"Fetching all {self.crawler_name} data")
        
        # Call the method to get all data at once
        if hasattr(method, '__self__'):  # Bound method
            data = await method()
        else:  # Function  
            data = await method(self.repo_owner, self.repo_name)
        
        # Now we know the actual total
        actual_total = len(data)
        self.logger.info(f"Retrieved {actual_total} items for {self.crawler_name}")
        
        # Update progress tracking with actual totals
        if self.progress_tracker:
            self.progress_tracker.init_crawler(self.crawler_name, actual_total)
            self.progress_tracker.update_operation(f"Saving {actual_total} {self.crawler_name} items")
        
        # Save all data to file
        file_path = f"{self.output_folder_path}/all_data.json"
        
        try:
            await write_json_file_async(file_path, data)
            
            # Update progress to show all items completed
            self.set_total_and_complete_progress(actual_total)
            
            self.logger.info(f"Successfully saved {actual_total} items to {file_path}")
            
            # Perform any post-processing (can be overridden by subclasses)
            await self.post_process_data(data)
            
        except Exception as e:
            self.logger.error(f"Failed to save {self.crawler_name} data: {e}")
            # Mark all as failed
            if self.progress_tracker:
                self.progress_tracker.init_crawler(self.crawler_name, actual_total)
                self.progress_tracker.update_crawler_progress(
                    self.crawler_name, failed=actual_total
                )
            raise
    
    async def post_process_data(self, data: List[Dict[str, Any]]):
        """Post-process data after saving (override in subclasses if needed)"""
        # Default: no post-processing
        pass