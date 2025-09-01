import json
import os
import time
from typing import Dict, Any, Set, List
from dataclasses import dataclass, asdict
from config import config

@dataclass
class CrawlerCheckpoint:
    """Checkpoint data for a specific crawler"""
    crawler_name: str
    completed: bool = False
    total_items: int = 0
    processed_items: int = 0
    failed_items: List[str] = None
    skipped_items: List[str] = None
    last_update: float = 0
    
    def __post_init__(self):
        if self.failed_items is None:
            self.failed_items = []
        if self.skipped_items is None:
            self.skipped_items = []
        if self.last_update == 0:
            self.last_update = time.time()

@dataclass  
class MasterCheckpoint:
    """Master checkpoint containing all crawler states"""
    repo_owner: str
    repo_name: str
    start_time: float
    last_update: float
    crawlers: Dict[str, CrawlerCheckpoint] = None
    completed_pull_numbers: Set[int] = None
    completed_commit_shas: Set[str] = None
    
    def __post_init__(self):
        if self.crawlers is None:
            self.crawlers = {}
        if self.completed_pull_numbers is None:
            self.completed_pull_numbers = set()
        if self.completed_commit_shas is None:
            self.completed_commit_shas = set()

class CheckpointManager:
    """Manages crawling checkpoints for resume capability"""
    
    def __init__(self, repo_owner: str, repo_name: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.checkpoint_file = self._get_checkpoint_path()
        self.checkpoint: MasterCheckpoint = self._load_or_create_checkpoint()
        
    def _get_checkpoint_path(self) -> str:
        """Get path to checkpoint file"""
        folder_name = f"{self.repo_owner}-{self.repo_name}"
        base_path = f"{config.base_folder}/{folder_name}"
        os.makedirs(base_path, exist_ok=True)
        return f"{base_path}/.checkpoint.json"
    
    def _load_or_create_checkpoint(self) -> MasterCheckpoint:
        """Load existing checkpoint or create new one"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                
                # Convert sets back from lists
                data['completed_pull_numbers'] = set(data.get('completed_pull_numbers', []))
                data['completed_commit_shas'] = set(data.get('completed_commit_shas', []))
                
                # Reconstruct crawler checkpoints
                crawlers = {}
                for name, crawler_data in data.get('crawlers', {}).items():
                    crawlers[name] = CrawlerCheckpoint(**crawler_data)
                data['crawlers'] = crawlers
                
                return MasterCheckpoint(**data)
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logging.warning(f"Failed to load checkpoint: {e}. Creating new one.")
        
        # Create new checkpoint
        return MasterCheckpoint(
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            start_time=time.time(),
            last_update=time.time()
        )
    
    def save_checkpoint(self):
        """Save current checkpoint to file"""
        try:
            # Convert to serializable format
            data = asdict(self.checkpoint)
            
            # Convert sets to lists for JSON serialization
            data['completed_pull_numbers'] = list(self.checkpoint.completed_pull_numbers)
            data['completed_commit_shas'] = list(self.checkpoint.completed_commit_shas)
            
            # Convert crawler checkpoints
            data['crawlers'] = {
                name: asdict(crawler) 
                for name, crawler in self.checkpoint.crawlers.items()
            }
            
            data['last_update'] = time.time()
            
            # Atomic write
            temp_file = f"{self.checkpoint_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            os.rename(temp_file, self.checkpoint_file)
            
        except Exception as e:
            logging.error(f"Failed to save checkpoint: {e}")
    
    def init_crawler(self, crawler_name: str, total_items: int) -> CrawlerCheckpoint:
        """Initialize or get existing crawler checkpoint"""
        if crawler_name not in self.checkpoint.crawlers:
            self.checkpoint.crawlers[crawler_name] = CrawlerCheckpoint(
                crawler_name=crawler_name,
                total_items=total_items
            )
        else:
            # Update total items if changed
            self.checkpoint.crawlers[crawler_name].total_items = total_items
        
        return self.checkpoint.crawlers[crawler_name]
    
    def update_crawler_progress(self, crawler_name: str, processed: int = 0, 
                              failed_item: str = None, skipped_item: str = None):
        """Update crawler progress"""
        if crawler_name not in self.checkpoint.crawlers:
            self.checkpoint.crawlers[crawler_name] = CrawlerCheckpoint(crawler_name=crawler_name)
        
        crawler = self.checkpoint.crawlers[crawler_name]
        
        if processed > 0:
            crawler.processed_items += processed
        
        if failed_item:
            if failed_item not in crawler.failed_items:
                crawler.failed_items.append(failed_item)
        
        if skipped_item:
            if skipped_item not in crawler.skipped_items:
                crawler.skipped_items.append(skipped_item)
        
        crawler.last_update = time.time()
    
    def complete_crawler(self, crawler_name: str):
        """Mark crawler as completed"""
        if crawler_name in self.checkpoint.crawlers:
            self.checkpoint.crawlers[crawler_name].completed = True
            self.checkpoint.crawlers[crawler_name].last_update = time.time()
    
    def is_crawler_completed(self, crawler_name: str) -> bool:
        """Check if crawler is already completed"""
        return (crawler_name in self.checkpoint.crawlers and 
                self.checkpoint.crawlers[crawler_name].completed)
    
    def add_completed_pull_number(self, pull_number: int):
        """Track completed pull request"""
        self.checkpoint.completed_pull_numbers.add(pull_number)
    
    def add_completed_commit_sha(self, commit_sha: str):
        """Track completed commit"""
        self.checkpoint.completed_commit_shas.add(commit_sha)
    
    def is_pull_completed(self, pull_number: int) -> bool:
        """Check if pull request is already processed"""
        return pull_number in self.checkpoint.completed_pull_numbers
    
    def is_commit_completed(self, commit_sha: str) -> bool:
        """Check if commit is already processed"""
        return commit_sha in self.checkpoint.completed_commit_shas
    
    def get_incomplete_crawlers(self) -> List[str]:
        """Get list of incomplete crawler names"""
        from config import CRAWLER_SEQUENCE
        
        incomplete = []
        for crawler_name in CRAWLER_SEQUENCE:
            if not self.is_crawler_completed(crawler_name):
                incomplete.append(crawler_name)
        
        return incomplete
    
    def get_resume_summary(self) -> Dict[str, Any]:
        """Get summary of what needs to be resumed"""
        summary = {
            'repo': f"{self.repo_owner}/{self.repo_name}",
            'total_runtime': time.time() - self.checkpoint.start_time,
            'incomplete_crawlers': self.get_incomplete_crawlers(),
            'completed_pulls': len(self.checkpoint.completed_pull_numbers),
            'completed_commits': len(self.checkpoint.completed_commit_shas),
            'crawler_details': {}
        }
        
        for name, crawler in self.checkpoint.crawlers.items():
            summary['crawler_details'][name] = {
                'completed': crawler.completed,
                'progress': f"{crawler.processed_items}/{crawler.total_items}",
                'failed_count': len(crawler.failed_items),
                'skipped_count': len(crawler.skipped_items)
            }
        
        return summary
    
    def cleanup_checkpoint(self):
        """Remove checkpoint file (call after successful completion)"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
        except Exception as e:
            logging.error(f"Failed to cleanup checkpoint: {e}")