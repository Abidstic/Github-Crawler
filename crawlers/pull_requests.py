from typing import Dict, Any
from .base_crawler import BaseListCrawler

class PullRequestsCrawler(BaseListCrawler):
    """Crawler for GitHub pull requests"""
    
    @property
    def crawler_name(self) -> str:
        return "pull_requests"
    
    @property
    def output_folder_path(self) -> str:
        return f"{self.base_folder_path}/pull"
    
    def get_api_method(self):
        """Get the GitHub client method for pull requests"""
        return self.github_client.get_pull_requests
    
    def get_api_params(self) -> Dict[str, Any]:
        """Parameters for pull requests API call"""
        return {}  # get_pull_requests already handles state='all' and pagination
    
    async def crawl_implementation(self) -> None:
        """Crawl all pull requests"""
        self.logger.info("Starting pull requests crawl")
        
        # Fetch all pull requests
        pull_requests = await self.github_client.get_pull_requests(
            self.repo_owner, self.repo_name
        )
        
        # Update actual total
        actual_total = len(pull_requests)
        self.checkpoint_manager.init_crawler(self.crawler_name, actual_total)
        
        if self.progress_tracker:
            self.progress_tracker.init_crawler(self.crawler_name, actual_total)
        
        # Save all pull requests
        file_path = f"{self.output_folder_path}/all_data.json"
        await self.save_data_async(pull_requests, file_path, "all_pull_requests")
        
        # Track completed pull numbers for dependency crawlers
        for pr in pull_requests:
            if 'number' in pr:
                self.checkpoint_manager.add_completed_pull_number(pr['number'])
        
        self.logger.info(f"Completed crawling {actual_total} pull requests")