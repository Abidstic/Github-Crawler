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
            # Estimate total items
            total_items = await self.estimate_total_items()
            
            # Initialize progress tracking
            crawler_checkpoint = self.checkpoint_manager.init_crawler(self.crawler_name, total_items)
            
            if self.progress_tracker:
                self.progress_tracker.init_crawler(self.crawler_name, total_items)
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
        
        # Update progress tracker
        if self.progress_tracker:
            if completed > 0 or failed > 0 or skipped > 0:
                self.progress_tracker.increment_crawler_progress(
                    self.crawler_name, completed, failed, skipped
                )
    
    async def save_data_async(self, data: Any, file_path: str, item_identifier: str = None):
        """Save data to file with error handling and progress updates"""
        try:
            await write_json_file_async(file_path, data)
            self.update_progress(completed=1)
            
            if item_identifier:
                self.logger.debug(f"Saved {item_identifier} to {file_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to save data to {file_path}: {e}")
            self.update_progress(failed=1, failed_item=item_identifier or file_path)
            raise
    
    def should_skip_existing(self, file_path: str) -> bool:
        """Check if file already exists and should be skipped"""
        if os.path.exists(file_path):
            self.update_progress(skipped=1, skipped_item=file_path)
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
    """Base class for crawlers that fetch paginated lists"""
    
    @abc.abstractmethod
    def get_api_method(self):
        """Get the GitHub client method to use for this crawler"""
        pass
    
    @abc.abstractmethod  
    def get_api_params(self) -> Dict[str, Any]:
        """Get additional parameters for the API call"""
        pass
    
    async def estimate_total_items(self) -> int:
        """Estimate by making a single API call to check pagination"""
        try:
            # Make a small request to get total count estimate
            method = self.get_api_method()
            params = {**self.get_api_params(), 'per_page': 1, 'page': 1}
            
            if hasattr(method, '__self__'):  # Bound method
                response = await method(**params)
            else:  # Function
                response = await method(self.repo_owner, self.repo_name, **params)
            
            # GitHub doesn't provide total count, so we estimate
            # This is a rough estimate - actual total will be determined during crawling
            return 1000  # Default estimate
            
        except Exception as e:
            self.logger.warning(f"Failed to estimate total items: {e}")
            return 1000  # Fallback estimate
    
    async def crawl_implementation(self) -> None:
        """Implementation for paginated list crawling"""
        method = self.get_api_method()
        params = self.get_api_params()
        
        if hasattr(method, '__self__'):  # Bound method
            data = await method(**params)
        else:  # Function  
            data = await method(self.repo_owner, self.repo_name, **params)
        
        # Update actual total
        if self.progress_tracker:
            self.progress_tracker.init_crawler(self.crawler_name, len(data))
        
        # Save all data in one file with page number
        file_path = f"{self.output_folder_path}/all_data.json"
        await self.save_data_async(data, file_path, f"{self.crawler_name}_all")