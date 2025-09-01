import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CrawlerConfig:
    """Configuration for GitHub crawler"""
    
    # GitHub API settings
    github_token: str = os.environ.get('GH_TOKEN')
    base_url: str = 'https://api.github.com'
    
    # Rate limiting settings
    max_requests_per_hour: int = 4800  # Conservative limit (GitHub allows 5000)
    rate_limit_buffer: int = 200       # Keep this many requests as buffer
    max_concurrent_requests: int = 10  # Parallel requests limit
    
    # Retry settings
    max_retries: int = 3
    base_backoff_delay: float = 60.0   # Base delay in seconds
    max_backoff_delay: float = 300.0   # Max delay (5 minutes)
    
    # File settings
    base_folder: str = 'crawled-data'
    items_per_page: int = 100          # GitHub API max
    
    # Progress settings
    progress_update_interval: float = 1.0  # Update progress every second
    
    # Checkpoint settings
    checkpoint_interval: int = 50      # Save checkpoint every N operations
    
    def __post_init__(self):
        if not self.github_token:
            raise ValueError("GitHub token is required. Set GH_TOKEN environment variable.")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Standard GitHub API headers"""
        return {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {self.github_token}',
            'X-GitHub-Api-Version': '2022-11-28'
        }

# Global config instance
config = CrawlerConfig()

# Crawler types and their dependencies
CRAWLER_SEQUENCE = [
    'pull_requests',    # Must be first (foundation)
    'commits',          # Must be second (foundation)
    'pr_files',         # Can be parallel
    'pr_reviews',       # Can be parallel  
    'pr_commits',       # Can be parallel
    'pr_comments',      # Can be parallel
    'single_commits',   # Must be last (depends on all previous)
]

PARALLEL_CRAWLERS = {
    'pr_dependencies': ['pr_files', 'pr_reviews', 'pr_commits', 'pr_comments']
}