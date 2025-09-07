from typing import Dict, Any, List
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
    
    async def post_process_data(self, data: List[Dict[str, Any]]):
        """Post-process pull requests data to track PR numbers"""
        # Track completed pull numbers for dependency crawlers
        for pr in data:
            if 'number' in pr:
                self.checkpoint_manager.add_completed_pull_number(pr['number'])
        
        self.logger.info(f"Tracked {len(data)} pull request numbers for dependency crawlers")