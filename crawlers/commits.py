from typing import Dict, Any, List
from .base_crawler import BaseListCrawler
from config import config

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
        """Parameters for commits API call. When the crawl limiter is active,
        scope commits to the date range of the selected PRs so repository
        commits stay relevant to the same crawl instead of pulling full history.
        
        Uses the checkpoint's persisted limit (set when PRs were actually
        crawled) rather than the current config, so resume stays consistent
        even if a later run answers the interactive prompt differently."""
        applied_limit, _ = self.checkpoint_manager.get_crawl_limit()
        if applied_limit and applied_limit > 0:
            since, until = self.checkpoint_manager.get_pr_date_range()
            if since and until:
                self.logger.info(f"Scoping commits to PR date range: {since} to {until}")
                return {'since': since, 'until': until}
        return {}  # get_commits already handles pagination
    
    async def post_process_data(self, data: List[Dict[str, Any]]):
        """Post-process commits data to track commit SHAs"""
        # Track completed commit SHAs for single commit crawler
        for commit in data:
            if 'sha' in commit:
                self.checkpoint_manager.add_completed_commit_sha(commit['sha'])
        
        self.logger.info(f"Tracked {len(data)} commit SHAs for single commit crawler")