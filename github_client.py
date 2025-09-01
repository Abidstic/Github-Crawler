import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from config import config
from rate_limiter import RateLimiter
from progress_tracker import get_progress_tracker

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    def __init__(self, status_code: int, message: str, response_data: Any = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"GitHub API Error {status_code}: {message}")

class GitHubClient:
    """Async GitHub API client with intelligent rate limiting"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(config)
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers=config.headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a single API request with rate limiting"""
        if not self.session:
            raise RuntimeError("GitHubClient must be used as async context manager")
        
        # Wait if rate limit requires it
        await self.rate_limiter.wait_if_needed()
        
        params = params or {}
        retry_count = 0
        
        while retry_count < config.max_retries:
            try:
                # Record the request
                self.rate_limiter.record_request()
                
                async with self.session.get(url, params=params) as response:
                    # Update rate limit status from headers
                    self.rate_limiter.update_from_headers(dict(response.headers))
                    
                    # Update progress tracker with rate limit info
                    try:
                        progress_tracker = get_progress_tracker()
                        progress_tracker.update_rate_limit(
                            self.rate_limiter.get_status_summary()
                        )
                    except RuntimeError:
                        pass  # Progress tracker not initialized yet
                    
                    if response.status == 200:
                        return await response.json()
                    
                    elif response.status == 403:
                        # Rate limit exceeded
                        wait_time = self.rate_limiter.handle_rate_limit_error(
                            dict(response.headers)
                        )
                        self.logger.warning(f"Rate limited. Waiting {wait_time/60:.1f} minutes")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    elif response.status == 404:
                        # Resource not found
                        raise GitHubAPIError(
                            404, f"Resource not found: {url}", 
                            await response.text()
                        )
                    
                    elif response.status >= 500:
                        # Server error - retry
                        retry_count += 1
                        delay = min(
                            config.base_backoff_delay * (2 ** retry_count),
                            config.max_backoff_delay
                        )
                        self.logger.warning(
                            f"Server error {response.status}. Retrying in {delay}s "
                            f"(attempt {retry_count}/{config.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    
                    else:
                        # Other client errors
                        error_text = await response.text()
                        raise GitHubAPIError(
                            response.status, 
                            f"API request failed: {error_text}",
                            error_text
                        )
            
            except aiohttp.ClientError as e:
                retry_count += 1
                delay = min(
                    config.base_backoff_delay * (2 ** retry_count),
                    config.max_backoff_delay
                )
                self.logger.warning(
                    f"Network error: {e}. Retrying in {delay}s "
                    f"(attempt {retry_count}/{config.max_retries})"
                )
                await asyncio.sleep(delay)
        
        # All retries exhausted
        raise GitHubAPIError(500, f"Failed after {config.max_retries} retries")
    
    async def get_paginated_data(self, base_url: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Fetch all pages of paginated data"""
        all_data = []
        page = 1
        params = params or {}
        
        while True:
            current_params = {
                **params,
                'page': page,
                'per_page': config.items_per_page
            }
            
            try:
                data = await self.make_request(base_url, current_params)
                
                if not data or len(data) == 0:
                    break
                
                all_data.extend(data)
                page += 1
                
                # Log progress
                self.logger.debug(f"Fetched page {page-1}, got {len(data)} items")
                
            except GitHubAPIError as e:
                if e.status_code == 404:
                    # No more pages
                    break
                raise
        
        return all_data
    
    async def get_pull_requests(self, repo_owner: str, repo_name: str) -> List[Dict[str, Any]]:
        """Get all pull requests for a repository"""
        url = f"{config.base_url}/repos/{repo_owner}/{repo_name}/pulls"
        return await self.get_paginated_data(url, {'state': 'all'})
    
    async def get_commits(self, repo_owner: str, repo_name: str) -> List[Dict[str, Any]]:
        """Get all commits for a repository"""
        url = f"{config.base_url}/repos/{repo_owner}/{repo_name}/commits"
        return await self.get_paginated_data(url)
    
    async def get_pull_files(self, repo_owner: str, repo_name: str, pull_number: int) -> List[Dict[str, Any]]:
        """Get files for a specific pull request"""
        url = f"{config.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pull_number}/files"
        return await self.get_paginated_data(url)
    
    async def get_pull_reviews(self, repo_owner: str, repo_name: str, pull_number: int) -> List[Dict[str, Any]]:
        """Get reviews for a specific pull request"""
        url = f"{config.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pull_number}/reviews"
        return await self.get_paginated_data(url)
    
    async def get_pull_commits(self, repo_owner: str, repo_name: str, pull_number: int) -> List[Dict[str, Any]]:
        """Get commits for a specific pull request"""
        url = f"{config.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pull_number}/commits"
        return await self.get_paginated_data(url)
    
    async def get_pull_review_comments(self, repo_owner: str, repo_name: str, pull_number: int) -> List[Dict[str, Any]]:
        """Get review comments for a specific pull request"""
        url = f"{config.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pull_number}/comments"
        return await self.get_paginated_data(url)
    
    async def get_single_commit(self, repo_owner: str, repo_name: str, commit_sha: str) -> Dict[str, Any]:
        """Get detailed data for a single commit"""
        url = f"{config.base_url}/repos/{repo_owner}/{repo_name}/commits/{commit_sha}"
        return await self.make_request(url)
    
    async def batch_get_single_commits(self, repo_owner: str, repo_name: str, 
                                     commit_shas: List[str], batch_size: int = None) -> Dict[str, Dict[str, Any]]:
        """Get multiple single commits in parallel batches"""
        if batch_size is None:
            batch_size = min(config.max_concurrent_requests, len(commit_shas))
        
        results = {}
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(commit_shas), batch_size):
            batch = commit_shas[i:i + batch_size]
            
            # Check if we have enough rate limit for this batch
            await self.rate_limiter.wait_if_needed(len(batch))
            
            # Process batch in parallel
            tasks = [
                self.get_single_commit(repo_owner, repo_name, sha)
                for sha in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for sha, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to fetch commit {sha}: {result}")
                    results[sha] = None
                else:
                    results[sha] = result
        
        return results