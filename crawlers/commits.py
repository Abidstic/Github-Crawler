from typing import Dict, Any, List
from .base_crawler import BaseListCrawler

class CommitsCrawler(BaseListCrawler):
    """Crawler for GitHub repository commits"""
    
    @property
    def crawler_name(self) -> str:
        return "commits"
    
    @property
    def output_folder_path(self) -> str:
        return f"{self.base_folder_path}/commit"
    
    def get_api_method(self):
        """Get the GitHub client method for commits"""
        return self.github_client.get_commits
    
    def get_api_params(self) -> Dict[str, Any]:
        """Parameters for commits API call"""
        return {}  # get_commits already handles pagination
    
    async def post_process_data(self, data: List[Dict[str, Any]]):
        """Post-process commits data to track commit SHAs"""
        # Track completed commit SHAs for single commit crawler
        for commit in data:
            if 'sha' in commit:
                self.checkpoint_manager.add_completed_commit_sha(commit['sha'])
        
        self.logger.info(f"Tracked {len(data)} commit SHAs for single commit crawler")