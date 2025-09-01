import os
import json
import asyncio
from typing import Dict, Any, List
from .base_crawler import BaseCrawler
from utils import get_all_pull_numbers
from github_client import GitHubAPIError

class PRDependenciesCrawler(BaseCrawler):
    """Crawler for pull request dependencies (files, reviews, commits, comments)"""
    
    def __init__(self, repo_owner: str, repo_name: str, github_client, checkpoint_manager, dependency_type: str):
        super().__init__(repo_owner, repo_name, github_client, checkpoint_manager)
        self.dependency_type = dependency_type
        self.pull_numbers = []
        
        # API method mapping
        self.api_methods = {
            'files': self.github_client.get_pull_files,
            'reviews': self.github_client.get_pull_reviews,
            'commits': self.github_client.get_pull_commits,
            'comments': self.github_client.get_pull_review_comments
        }
    
    @property
    def crawler_name(self) -> str:
        return f"pr_{self.dependency_type}"
    
    @property
    def output_folder_path(self) -> str:
        return f"{self.base_folder_path}/pull"
    
    async def estimate_total_items(self) -> int:
        """Estimate based on number of pull requests"""
        pull_folder = f"{self.base_folder_path}/pull"
        
        # Try to get PR numbers from the all_data.json file
        all_data_file = f"{pull_folder}/all_data.json"
        if os.path.exists(all_data_file):
            try:
                with open(all_data_file, 'r') as f:
                    pull_requests = json.load(f)
                self.pull_numbers = [pr['number'] for pr in pull_requests if 'number' in pr]
                self.logger.info(f"Found {len(self.pull_numbers)} PR numbers from all_data.json")
            except Exception as e:
                self.logger.error(f"Failed to read PR numbers from all_data.json: {e}")
                self.pull_numbers = []
        else:
            self.logger.warning(f"Pull requests data file not found: {all_data_file}")
            self.pull_numbers = []
        
        return len(self.pull_numbers)
    
    async def crawl_implementation(self) -> None:
        """Crawl dependencies for all pull requests"""
        if not self.pull_numbers:
            self.logger.warning(f"No PR numbers found for {self.dependency_type} crawling")
            return
            
        self.logger.info(f"Starting {self.dependency_type} crawl for {len(self.pull_numbers)} PRs")
        
        # Get API method
        api_method = self.api_methods[self.dependency_type]
        
        # Process PRs in parallel batches
        batch_size = min(10, len(self.pull_numbers))  # Conservative parallel processing
        
        async def process_pr_batch(pr_batch: List[int]):
            """Process a batch of PRs"""
            tasks = []
            for pr_number in pr_batch:
                # Check if this specific PR's dependency already exists
                output_folder = f"{self.output_folder_path}/{pr_number}/{self.dependency_type}"
                output_file = f"{output_folder}/all_data.json"
                
                if os.path.exists(output_file):
                    self.update_progress(skipped=1, skipped_item=str(pr_number))
                    continue
                
                tasks.append(self._crawl_single_pr(pr_number, api_method))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process all batches
        await self.process_in_batches(
            self.pull_numbers, 
            batch_size,
            process_pr_batch,
            f"Crawling PR {self.dependency_type}"
        )
    
    async def _crawl_single_pr(self, pr_number: int, api_method):
        """Crawl dependency data for a single PR"""
        output_folder = f"{self.output_folder_path}/{pr_number}/{self.dependency_type}"
        output_file = f"{output_folder}/all_data.json"
        
        # Skip if already exists
        if os.path.exists(output_file):
            self.update_progress(skipped=1, skipped_item=str(pr_number))
            return
        
        try:
            # Fetch data for this PR
            data = await api_method(self.repo_owner, self.repo_name, pr_number)
            
            # Create folder and save data (even if empty list)
            os.makedirs(output_folder, exist_ok=True)
            await self.save_data_async(data, output_file, f"PR_{pr_number}_{self.dependency_type}")
            
            self.logger.debug(f"Completed {self.dependency_type} for PR {pr_number}: {len(data)} items")
            
        except GitHubAPIError as e:
            if e.status_code == 404:
                # PR might not have this type of data (normal) - save empty data
                self.logger.debug(f"No {self.dependency_type} found for PR {pr_number} (404)")
                os.makedirs(output_folder, exist_ok=True)
                await self.save_data_async([], output_file, f"PR_{pr_number}_{self.dependency_type}")
            else:
                self.logger.error(f"API error for PR {pr_number} {self.dependency_type}: {e}")
                self.update_progress(failed=1, failed_item=f"PR_{pr_number}")
                
        except Exception as e:
            self.logger.error(f"Failed to process PR {pr_number} {self.dependency_type}: {e}")
            self.update_progress(failed=1, failed_item=f"PR_{pr_number}")

# Factory functions for each dependency type
class PRFilesCrawler(PRDependenciesCrawler):
    def __init__(self, repo_owner: str, repo_name: str, github_client, checkpoint_manager):
        super().__init__(repo_owner, repo_name, github_client, checkpoint_manager, 'files')

class PRReviewsCrawler(PRDependenciesCrawler):
    def __init__(self, repo_owner: str, repo_name: str, github_client, checkpoint_manager):
        super().__init__(repo_owner, repo_name, github_client, checkpoint_manager, 'reviews')

class PRCommitsCrawler(PRDependenciesCrawler):
    def __init__(self, repo_owner: str, repo_name: str, github_client, checkpoint_manager):
        super().__init__(repo_owner, repo_name, github_client, checkpoint_manager, 'commits')

class PRCommentsCrawler(PRDependenciesCrawler):
    def __init__(self, repo_owner: str, repo_name: str, github_client, checkpoint_manager):
        super().__init__(repo_owner, repo_name, github_client, checkpoint_manager, 'comments')