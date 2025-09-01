#!/usr/bin/env python3
"""
Quick Start Script for GitHub Unified Crawler

This script provides an interactive way to get started with the crawler.
"""

import os
import sys
import asyncio
from pathlib import Path

def get_github_token():
    """Get GitHub token from user or environment"""
    token = os.environ.get('GH_TOKEN')
    
    if token:
        print(f"✅ Using GitHub token from environment: {token[:8]}...")
        return token
    
    print("🔑 GitHub token not found in environment.")
    print("\nYou have two options:")
    print("1. Set environment variable: export GH_TOKEN='your_token'")
    print("2. Enter token now (not recommended for security)")
    
    choice = input("\nEnter choice [1/2]: ").strip()
    
    if choice == "2":
        token = input("Enter GitHub token: ").strip()
        if token:
            return token
    
    print("\n💡 To get a GitHub token:")
    print("1. Go to: https://github.com/settings/tokens")
    print("2. Click 'Generate new token (classic)'")
    print("3. Select 'repo' permissions")
    print("4. Copy the token and set: export GH_TOKEN='your_token'")
    
    return None

def get_repository_info():
    """Get repository information from user"""
    print("\n📚 Repository Selection")
    print("-" * 30)
    
    # Provide some popular examples
    print("💡 Popular repositories to try:")
    print("   facebook/react (Medium size)")
    print("   microsoft/vscode (Large size)")
    print("   octocat/Hello-World (Small size)")
    print("   tensorflow/tensorflow (Very large)")
    
    while True:
        owner = input("\nEnter repository owner: ").strip()
        repo = input("Enter repository name: ").strip()
        
        if owner and repo:
            return owner, repo
        else:
            print("❌ Please provide both owner and repository name")

def get_crawler_options():
    """Get crawler configuration options"""
    print("\n⚙️  Crawler Options")
    print("-" * 20)
    
    options = {}
    
    # Resume option
    resume_choice = input("Resume from previous crawl if available? [Y/n]: ").strip().lower()
    options['resume'] = resume_choice not in ['n', 'no']
    
    # Conservative mode
    conservative_choice = input("Use conservative rate limiting? (recommended for large repos) [y/N]: ").strip().lower()
    options['conservative'] = conservative_choice in ['y', 'yes']
    
    # Concurrent requests
    if not options['conservative']:
        try:
            concurrent = input("Max concurrent requests [10]: ").strip()
            options['max_concurrent'] = int(concurrent) if concurrent else 10
        except ValueError:
            options['max_concurrent'] = 10
    
    return options

def print_crawl_summary(owner: str, repo: str, options: dict):
    """Print crawl configuration summary"""
    print("\n" + "=" * 60)
    print("🎯 Crawl Configuration Summary")
    print("=" * 60)
    print(f"Repository: {owner}/{repo}")
    print(f"Resume mode: {'Enabled' if options['resume'] else 'Disabled'}")
    print(f"Conservative mode: {'Enabled' if options['conservative'] else 'Disabled'}")
    
    if 'max_concurrent' in options:
        print(f"Max concurrent: {options['max_concurrent']}")
    
    data_path = f"{config.base_folder}/{owner}-{repo}"
    print(f"Data location: {data_path}")
    
    # Check if data already exists
    if os.path.exists(data_path):
        size_mb = get_folder_size_mb(data_path)
        print(f"Existing data: {size_mb:.1f} MB")
    
    print("=" * 60)

def build_command(owner: str, repo: str, options: dict) -> str:
    """Build the equivalent CLI command"""
    cmd_parts = ["python main.py", f"--owner {owner}", f"--repo {repo}"]
    
    if not options['resume']:
        cmd_parts.append("--no-resume")
    
    if options['conservative']:
        cmd_parts.append("--conservative")
    
    if 'max_concurrent' in options and options['max_concurrent'] != 10:
        cmd_parts.append(f"--max-concurrent {options['max_concurrent']}")
    
    return " ".join(cmd_parts)

async def run_crawler(owner: str, repo: str, options: dict):
    """Run the actual crawler"""
    print(f"\n🚀 Starting crawl for {owner}/{repo}...")
    print("💡 Press Ctrl+C anytime to stop gracefully")
    print("-" * 60)
    
    try:
        # Apply options to config
        if options['conservative']:
            config.max_concurrent_requests = 5
            config.rate_limit_buffer = 500
        
        if 'max_concurrent' in options:
            config.max_concurrent_requests = options['max_concurrent']
        
        # Run the crawler
        summary = await crawl_repository(owner, repo, resume=options['resume'])
        
        # Print success summary
        print("\n" + "🎉" * 20)
        print("CRAWLING COMPLETED SUCCESSFULLY!")
        print("🎉" * 20)
        print(f"📁 Data location: {summary['base_folder']}")
        print(f"💾 Total size: {summary['data_size_mb']:.1f} MB")
        print(f"⏱️  Repository: {summary['repository']}")
        
        return summary
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawling stopped by user")
        print("💾 Progress has been saved to checkpoint")
        print("🔄 Run the same command again to resume")
        
    except Exception as e:
        print(f"\n❌ Crawling failed: {e}")
        print("📋 Check the logs for detailed error information")
        print("🔄 You can retry by running the same command")

async def interactive_mode():
    """Run interactive mode"""
    print("🎯 GitHub Unified Crawler - Quick Start")
    print("=" * 60)
    
    # Check token
    token = get_github_token()
    if not token:
        print("❌ Cannot proceed without GitHub token")
        return
    
    # Set token in environment if not already set
    if not os.environ.get('GH_TOKEN'):
        os.environ['GH_TOKEN'] = token
    
    # Get repository info
    owner, repo = get_repository_info()
    
    # Get options
    options = get_crawler_options()
    
    # Show summary
    print_crawl_summary(owner, repo, options)
    
    # Build equivalent command
    equivalent_cmd = build_command(owner, repo, options)
    print(f"\n💡 Equivalent CLI command:")
    print(f"   {equivalent_cmd}")
    
    # Confirm
    proceed = input("\nProceed with crawling? [Y/n]: ").strip().lower()
    
    if proceed in ['', 'y', 'yes']:
        await run_crawler(owner, repo, options)
    else:
        print("👋 Crawling cancelled")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # If arguments provided, assume user wants direct CLI
        print("💡 For interactive mode, run: python quickstart.py")
        print("💡 For direct CLI, run: python main.py --help")
        return
    
    try:
        asyncio.run(interactive_mode())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()