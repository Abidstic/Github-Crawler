from typing import Dict, Any
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
    
    async def crawl_implementation(self) -> None:
        """Crawl all repository commits"""
        self.logger.info("Starting commits crawl")
        
        # Fetch all commits
        commits = await self.github_client.get_commits(
            self.repo_owner, self.repo_name
        )
        
        # Update actual total
        actual_total = len(commits)
        self.checkpoint_manager.init_crawler(self.crawler_name, actual_total)
        
        if self.progress_tracker:
            self.progress_tracker.init_crawler(self.crawler_name, actual_total)
        
        # Save all commits
        file_path = f"{self.output_folder_path}/all_data.json"
        await self.save_data_async(commits, file_path, "all_commits")
        
        # Track completed commit SHAs for single commit crawler
        for commit in commits:
            if 'sha' in commit:
                self.checkpoint_manager.add_completed_commit_sha(commit['sha'])
        
        self.logger.info(f"Completed crawling {actual_total} commits")