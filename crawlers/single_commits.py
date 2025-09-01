import os
import asyncio
from typing import List, Set, Dict, Any
from .base_crawler import BaseCrawler
from utils import get_all_unique_commit_shas, get_existing_single_commits
from github_client import GitHubAPIError
from config import config

class SingleCommitsCrawler(BaseCrawler):
    """Crawler for detailed individual commit data"""
    
    def __init__(self, repo_owner: str, repo_name: str, github_client, checkpoint_manager):
        super().__init__(repo_owner, repo_name, github_client, checkpoint_manager)
        self.all_commit_shas: List[str] = []
        self.existing_commits: Set[str] = set()
        self.remaining_commits: List[str] = []
    
    @property
    def crawler_name(self) -> str:
        return "single_commits"
    
    @property
    def output_folder_path(self) -> str:
        return f"{self.base_folder_path}/commit/all"
    
    async def estimate_total_items(self) -> int:
        """Estimate based on unique commit SHAs minus already existing ones"""
        # Get all unique commit SHAs from previous crawls
        self.all_commit_shas = get_all_unique_commit_shas(self.base_folder_path)
        
        # Get already processed commits
        self.existing_commits = get_existing_single_commits(self.output_folder_path)
        
        # Calculate remaining
        remaining_shas = set(self.all_commit_shas) - self.existing_commits
        self.remaining_commits = sorted(list(remaining_shas))
        
        self.logger.info(f"Found {len(self.all_commit_shas)} total commits, "
                        f"{len(self.existing_commits)} already processed, "
                        f"{len(self.remaining_commits)} remaining")
        
        return len(self.remaining_commits)
    
    async def crawl_implementation(self) -> None:
        """Crawl detailed data for all unique commits"""
        if not self.remaining_commits:
            self.logger.info("No commits to process")
            return
        
        self.logger.info(f"Starting single commits crawl for {len(self.remaining_commits)} commits")
        
        # Determine optimal batch size based on rate limit
        rate_limit_status = self.github_client.rate_limiter.get_status_summary()
        
        # Conservative batch size based on remaining rate limit
        if rate_limit_status['remaining'] < 500:
            batch_size = 5  # Very conservative
        elif rate_limit_status['remaining'] < 1000:
            batch_size = 10  # Moderate
        else:
            batch_size = min(20, config.max_concurrent_requests)  # Aggressive
        
        self.logger.info(f"Using batch size: {batch_size}")
        
        # Process commits in batches
        await self.process_in_batches(
            self.remaining_commits,
            batch_size, 
            self._process_commit_batch,
            "Processing commit batches"
        )
    
    async def _process_commit_batch(self, commit_batch: List[str]):
        """Process a batch of commits in parallel"""
        # Use GitHub client's batch method for optimal performance
        results = await self.github_client.batch_get_single_commits(
            self.repo_owner, self.repo_name, commit_batch
        )
        
        # Save results
        save_tasks = []
        for commit_sha, commit_data in results.items():
            if commit_data is None:
                self.update_progress(failed=1, failed_item=commit_sha)
                continue
            
            file_path = f"{self.output_folder_path}/{commit_sha}.json"
            save_tasks.append(
                self._save_single_commit(commit_sha, commit_data, file_path)
            )
        
        # Save all files in this batch
        if save_tasks:
            await asyncio.gather(*save_tasks, return_exceptions=True)
    
    async def _save_single_commit(self, commit_sha: str, commit_data: Dict[str, Any], file_path: str):
        """Save single commit data"""
        try:
            await self.save_data_async(commit_data, file_path, commit_sha)
            self.checkpoint_manager.add_completed_commit_sha(commit_sha)
            
        except Exception as e:
            self.logger.error(f"Failed to save commit {commit_sha}: {e}")
            self.update_progress(failed=1, failed_item=commit_sha)