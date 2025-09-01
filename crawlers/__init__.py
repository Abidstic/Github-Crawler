"""
GitHub Crawlers Package

This package contains all the specialized crawlers for different types of GitHub data.
"""

from .base_crawler import BaseCrawler, BaseListCrawler
from .pull_requests import PullRequestsCrawler
from .commits import CommitsCrawler
from .pr_dependencies import (
    PRDependenciesCrawler,
    PRFilesCrawler, 
    PRReviewsCrawler,
    PRCommitsCrawler,
    PRCommentsCrawler
)
from .single_commits import SingleCommitsCrawler

# Crawler registry for easy instantiation
CRAWLER_CLASSES = {
    'pull_requests': PullRequestsCrawler,
    'commits': CommitsCrawler,
    'pr_files': PRFilesCrawler,
    'pr_reviews': PRReviewsCrawler,
    'pr_commits': PRCommitsCrawler,
    'pr_comments': PRCommentsCrawler,
    'single_commits': SingleCommitsCrawler,
}

def create_crawler(crawler_type: str, repo_owner: str, repo_name: str, github_client, checkpoint_manager):
    """Factory function to create crawler instances"""
    if crawler_type not in CRAWLER_CLASSES:
        raise ValueError(f"Unknown crawler type: {crawler_type}. Available: {list(CRAWLER_CLASSES.keys())}")
    
    crawler_class = CRAWLER_CLASSES[crawler_type]
    return crawler_class(repo_owner, repo_name, github_client, checkpoint_manager)

__all__ = [
    'BaseCrawler',
    'BaseListCrawler', 
    'PullRequestsCrawler',
    'CommitsCrawler',
    'PRDependenciesCrawler',
    'PRFilesCrawler',
    'PRReviewsCrawler', 
    'PRCommitsCrawler',
    'PRCommentsCrawler',
    'SingleCommitsCrawler',
    'CRAWLER_CLASSES',
    'create_crawler'
]