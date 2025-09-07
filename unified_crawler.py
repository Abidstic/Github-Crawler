import asyncio
import logging
import signal
import sys
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from config import config, CRAWLER_SEQUENCE, PARALLEL_CRAWLERS
from github_client import GitHubClient
from checkpoint_manager import CheckpointManager
from progress_tracker import init_progress_tracker, get_progress_tracker
from crawlers import create_crawler
from utils import validate_crawled_data, cleanup_empty_folders, get_folder_size_mb

class UnifiedCrawler:
    """Main crawler orchestrator that runs all crawlers in optimal sequence"""
    
    def __init__(self, repo_owner: str, repo_name: str, resume: bool = True):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.resume = resume
        
        # Initialize managers
        self.checkpoint_manager = CheckpointManager(repo_owner, repo_name)
        self.progress_tracker = init_progress_tracker(repo_owner, repo_name)
        self.github_client: Optional[GitHubClient] = None
        
        # Set base folder path
        self.base_folder_path = f"{config.base_folder}/{repo_owner}-{repo_name}"
        
        # State tracking
        self.is_running = False
        self.graceful_shutdown = False
        
        # Setup logging with reduced console output during progress display
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_logging(self):
        """Setup logging configuration with reduced console output during display"""
        log_folder = f"{config.base_folder}/{self.repo_owner}-{self.repo_name}/logs"
        os.makedirs(log_folder, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f"{log_folder}/unified_crawler_{timestamp}.log"
        
        # Clear any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # File handler with detailed logging
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler with minimal output during progress display
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)  # Only show errors on console
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info("Received shutdown signal. Initiating graceful shutdown...")
            self.graceful_shutdown = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def crawl_complete_repository(self) -> None:
        """Crawl all data for the repository"""
        self.is_running = True
        
        try:
            # Start progress display
            await self.progress_tracker.start_display()
            
            # Initialize GitHub client
            async with GitHubClient() as github_client:
                self.github_client = github_client
                
                if self.resume:
                    await self._print_resume_summary()
                
                # Phase 1: Foundation crawlers (sequential)
                await self._run_foundation_crawlers()
                
                if self.graceful_shutdown:
                    return
                
                # Phase 2: PR dependencies (parallel)
                await self._run_pr_dependencies_parallel()
                
                if self.graceful_shutdown:
                    return
                
                # Phase 3: Single commits (intelligent batching)
                await self._run_single_commits_crawler()
                
                # Final validation and cleanup
                await self._finalize_crawling()
        
        except Exception as e:
            self.logger.error(f"Crawling failed: {e}")
            raise
        
        finally:
            self.is_running = False
            # Save final checkpoint
            self.checkpoint_manager.save_checkpoint()
            
            # Stop progress display
            await self.progress_tracker.stop_display()
    
    async def _print_resume_summary(self):
        """Print resume summary if continuing previous crawl"""
        summary = self.checkpoint_manager.get_resume_summary()
        
        if summary['incomplete_crawlers']:
            self.logger.info("Resuming previous crawl:")
            self.logger.info(f"Repository: {summary['repo']}")
            self.logger.info(f"Previous runtime: {summary['total_runtime']/3600:.1f} hours")
            self.logger.info(f"Incomplete crawlers: {', '.join(summary['incomplete_crawlers'])}")
        else:
            self.logger.info("All crawlers previously completed. Running validation...")
    
    async def _run_foundation_crawlers(self) -> None:
        """Run foundation crawlers that other crawlers depend on"""
        foundation_crawlers = ['pull_requests', 'commits']
        
        for crawler_name in foundation_crawlers:
            if self.graceful_shutdown:
                break
                
            if self.checkpoint_manager.is_crawler_completed(crawler_name):
                self.logger.info(f"{crawler_name} already completed, skipping")
                continue
            
            self.logger.info(f"Starting {crawler_name} crawler")
            crawler = create_crawler(
                crawler_name, self.repo_owner, self.repo_name, 
                self.github_client, self.checkpoint_manager
            )
            
            await crawler.crawl()
            self.checkpoint_manager.save_checkpoint()
    
    async def _run_pr_dependencies_parallel(self) -> None:
        """Run PR dependency crawlers in parallel"""
        pr_dependency_crawlers = PARALLEL_CRAWLERS['pr_dependencies']
        
        # Check which ones need to run
        pending_crawlers = [
            crawler_name for crawler_name in pr_dependency_crawlers
            if not self.checkpoint_manager.is_crawler_completed(crawler_name)
        ]
        
        if not pending_crawlers:
            self.logger.info("All PR dependency crawlers already completed")
            return
        
        self.logger.info(f"Starting {len(pending_crawlers)} PR dependency crawlers in parallel")
        
        # Create crawler instances
        crawler_tasks = []
        for crawler_name in pending_crawlers:
            if self.graceful_shutdown:
                break
                
            crawler = create_crawler(
                crawler_name, self.repo_owner, self.repo_name,
                self.github_client, self.checkpoint_manager
            )
            crawler_tasks.append(crawler.crawl())
        
        # Run all PR dependency crawlers in parallel
        if crawler_tasks:
            await asyncio.gather(*crawler_tasks, return_exceptions=True)
            self.checkpoint_manager.save_checkpoint()
    
    async def _run_single_commits_crawler(self) -> None:
        """Run single commits crawler with intelligent batching"""
        crawler_name = 'single_commits'
        
        if self.checkpoint_manager.is_crawler_completed(crawler_name):
            self.logger.info("Single commits crawler already completed")
            return
        
        if self.graceful_shutdown:
            return
        
        self.logger.info("Starting single commits crawler")
        crawler = create_crawler(
            crawler_name, self.repo_owner, self.repo_name,
            self.github_client, self.checkpoint_manager
        )
        
        await crawler.crawl()
        self.checkpoint_manager.save_checkpoint()
    
    async def _finalize_crawling(self):
        """Perform final validation and cleanup"""
        if self.graceful_shutdown:
            self.logger.info("Crawling interrupted. Data saved with checkpoint for resume.")
            return
        
        self.progress_tracker.update_operation("Finalizing and validating data...")
        
        # Validate crawled data
        validation_results = validate_crawled_data(self.base_folder_path)
        
        if validation_results['valid']:
            self.logger.info("Data validation passed")
            
            # Cleanup
            cleanup_empty_folders(self.base_folder_path)
            
            # Print final summary
            folder_size = get_folder_size_mb(self.base_folder_path)
            self.logger.info(f"Crawling completed! Data size: {folder_size:.1f} MB")
            
            # Remove checkpoint file since everything is complete
            self.checkpoint_manager.cleanup_checkpoint()
            
        else:
            self.logger.error("Data validation failed:")
            for error in validation_results['errors']:
                self.logger.error(f"  - {error}")
            
            for warning in validation_results['warnings']:
                self.logger.warning(f"  - {warning}")
    
    def get_crawling_summary(self) -> Dict[str, Any]:
        """Get summary of crawling status"""
        # Get fresh checkpoint data
        checkpoint_summary = self.checkpoint_manager.get_resume_summary()
    
        # Update with current progress tracker data if available
        if self.progress_tracker:
            for crawler_name, stats in self.progress_tracker.stats.items():
                if crawler_name in checkpoint_summary.get('crawler_details', {}):
                    checkpoint_summary['crawler_details'][crawler_name].update({
                        'progress': f"{stats.completed}/{stats.total}",
                        'completed': stats.is_complete
                    })
        
        return {
            'repository': f"{self.repo_owner}/{self.repo_name}",
            'is_running': self.is_running,
            'resume_available': os.path.exists(self.checkpoint_manager.checkpoint_file),
            'checkpoint_summary': checkpoint_summary,
            'base_folder': self.base_folder_path,
            'data_size_mb': get_folder_size_mb(self.base_folder_path)
        }

# Factory function for easy instantiation
def create_unified_crawler(repo_owner: str, repo_name: str, resume: bool = True) -> UnifiedCrawler:
    """Create a unified crawler instance"""
    return UnifiedCrawler(repo_owner, repo_name, resume)

# Main crawling function
async def crawl_repository(repo_owner: str, repo_name: str, resume: bool = True) -> Dict[str, Any]:
    """
    Main function to crawl a complete GitHub repository
    
    Args:
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name  
        resume: Whether to resume from previous checkpoint
    
    Returns:
        Dictionary with crawling summary
    """
    crawler = create_unified_crawler(repo_owner, repo_name, resume)
    
    try:
        await crawler.crawl_complete_repository()
        return crawler.get_crawling_summary()
        
    except KeyboardInterrupt:
        crawler.logger.info("Crawling interrupted by user")
        return crawler.get_crawling_summary()
        
    except Exception as e:
        crawler.logger.error(f"Crawling failed: {e}")
        raise