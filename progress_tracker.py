import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class CrawlerStats:
    """Statistics for a specific crawler"""
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def progress_percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100
    
    @property
    def is_complete(self) -> bool:
        return self.completed >= self.total and self.total > 0
    
    @property
    def duration(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def rate_per_minute(self) -> float:
        if self.duration == 0:
            return 0.0
        return (self.completed / self.duration) * 60

class ProgressTracker:
    """Real-time progress tracker with CLI display"""
    
    def __init__(self, repo_owner: str, repo_name: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.start_time = time.time()
        self.stats: Dict[str, CrawlerStats] = defaultdict(CrawlerStats)
        self.current_operation = "Initializing..."
        self.rate_limit_status = {}
        self.display_task = None
        self.is_running = False
        
    async def start_display(self):
        """Start the real-time display task"""
        self.is_running = True
        self.display_task = asyncio.create_task(self._display_loop())
    
    async def stop_display(self):
        """Stop the real-time display"""
        self.is_running = False
        if self.display_task:
            self.display_task.cancel()
            try:
                await self.display_task
            except asyncio.CancelledError:
                pass
        self._final_display()
    
    def update_operation(self, operation: str):
        """Update current operation description"""
        self.current_operation = operation
    
    def init_crawler(self, crawler_name: str, total_items: int):
        """Initialize stats for a crawler"""
        self.stats[crawler_name].total = total_items
        self.stats[crawler_name].start_time = time.time()
    
    def update_crawler_progress(self, crawler_name: str, completed: int = None, 
                              failed: int = None, skipped: int = None):
        """Update crawler progress"""
        stats = self.stats[crawler_name]
        if completed is not None:
            stats.completed = completed
        if failed is not None:
            stats.failed = failed
        if skipped is not None:
            stats.skipped = skipped
    
    def increment_crawler_progress(self, crawler_name: str, 
                                 completed: int = 0, failed: int = 0, skipped: int = 0):
        """Increment crawler progress"""
        stats = self.stats[crawler_name]
        stats.completed += completed
        stats.failed += failed
        stats.skipped += skipped
    
    def complete_crawler(self, crawler_name: str):
        """Mark crawler as complete"""
        self.stats[crawler_name].end_time = time.time()
    
    def update_rate_limit(self, rate_limit_status: Dict[str, Any]):
        """Update rate limit status"""
        self.rate_limit_status = rate_limit_status
    
    def _create_progress_bar(self, percentage: float, width: int = 40) -> str:
        """Create ASCII progress bar"""
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f'[{bar}] {percentage:5.1f}%'
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _format_eta(self, stats: CrawlerStats) -> str:
        """Calculate and format ETA"""
        if stats.completed == 0 or stats.is_complete:
            return "N/A"
        
        rate = stats.rate_per_minute
        if rate == 0:
            return "∞"
        
        remaining = stats.total - stats.completed
        eta_minutes = remaining / rate
        eta_seconds = eta_minutes * 60
        
        return self._format_duration(eta_seconds)
    
    async def _display_loop(self):
        """Main display loop"""
        while self.is_running:
            self._clear_screen()
            self._display_status()
            await asyncio.sleep(1.0)
    
    def _clear_screen(self):
        """Clear screen and move cursor to top"""
        # ANSI escape codes for clearing screen
        print('\033[2J\033[H', end='')
    
    def _display_status(self):
        """Display current crawling status"""
        total_duration = time.time() - self.start_time
        
        print("=" * 80)
        print(f"🚀 GitHub Crawler - {self.repo_owner}/{self.repo_name}")
        print(f"⏱️  Total Runtime: {self._format_duration(total_duration)}")
        print(f"🔄 Current: {self.current_operation}")
        print("=" * 80)
        
        # Rate limit status
        if self.rate_limit_status:
            rl = self.rate_limit_status
            status_color = "🟢" if rl['remaining'] > 1000 else "🟡" if rl['remaining'] > 200 else "🔴"
            print(f"{status_color} Rate Limit: {rl['remaining']}/{rl['limit']} "
                  f"(Reset: {rl['reset_time']}) - {rl['usage_percentage']:.1f}% used")
            
            if rl.get('conservative_mode', False):
                print("⚠️  Conservative mode enabled")
        
        print()
        
        # Crawler progress
        for crawler_name, stats in self.stats.items():
            if stats.total == 0:
                continue
                
            status_icon = "✅" if stats.is_complete else "🔄" if stats.completed > 0 else "⏳"
            progress_bar = self._create_progress_bar(stats.progress_percentage)
            
            print(f"{status_icon} {crawler_name.replace('_', ' ').title()}")
            print(f"   {progress_bar}")
            print(f"   Progress: {stats.completed:,}/{stats.total:,} "
                  f"(Failed: {stats.failed}, Skipped: {stats.skipped})")
            
            if stats.completed > 0:
                print(f"   Rate: {stats.rate_per_minute:.1f}/min | "
                      f"Duration: {self._format_duration(stats.duration)} | "
                      f"ETA: {self._format_eta(stats)}")
            print()
        
        # Overall progress
        total_items = sum(stats.total for stats in self.stats.values())
        completed_items = sum(stats.completed for stats in self.stats.values())
        
        if total_items > 0:
            overall_percentage = (completed_items / total_items) * 100
            overall_bar = self._create_progress_bar(overall_percentage)
            print(f"📊 Overall Progress: {overall_bar}")
            print(f"   {completed_items:,}/{total_items:,} total items")
        
        print("=" * 80)
        print("Press Ctrl+C to stop gracefully")
    
    def _final_display(self):
        """Display final summary"""
        self._clear_screen()
        total_duration = time.time() - self.start_time
        
        print("=" * 80)
        print(f"🎉 GitHub Crawler Complete - {self.repo_owner}/{self.repo_name}")
        print(f"⏱️  Total Duration: {self._format_duration(total_duration)}")
        print("=" * 80)
        
        for crawler_name, stats in self.stats.items():
            if stats.total == 0:
                continue
                
            status = "✅ Complete" if stats.is_complete else "❌ Incomplete"
            print(f"{status} {crawler_name.replace('_', ' ').title()}")
            print(f"   Items: {stats.completed:,}/{stats.total:,} "
                  f"(Failed: {stats.failed}, Skipped: {stats.skipped})")
            print(f"   Duration: {self._format_duration(stats.duration)}")
            print(f"   Average Rate: {stats.rate_per_minute:.1f} items/min")
            print()
        
        # Final stats
        total_items = sum(stats.completed for stats in self.stats.values())
        total_failed = sum(stats.failed for stats in self.stats.values())
        
        print(f"📈 Final Summary:")
        print(f"   Total Items Crawled: {total_items:,}")
        print(f"   Total Failed: {total_failed:,}")
        print(f"   Average Rate: {total_items / (total_duration / 60):.1f} items/min")
        print("=" * 80)

# Singleton progress tracker
_progress_tracker: Optional[ProgressTracker] = None

def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance"""
    if _progress_tracker is None:
        raise RuntimeError("Progress tracker not initialized")
    return _progress_tracker

def init_progress_tracker(repo_owner: str, repo_name: str) -> ProgressTracker:
    """Initialize the global progress tracker"""
    global _progress_tracker
    _progress_tracker = ProgressTracker(repo_owner, repo_name)
    return _progress_tracker