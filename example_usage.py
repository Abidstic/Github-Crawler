#!/usr/bin/env python3
"""
Example usage of the GitHub Unified Crawler

This script demonstrates how to use the crawler programmatically
and how to access the crawled data for analysis.
"""

import asyncio
import json
import os
from pathlib import Path
from unified_crawler import crawl_repository
from utils import validate_crawled_data, get_folder_size_mb
from config import config

async def example_crawl_small_repo():
    """Example: Crawl a small repository"""
    print("🎯 Example 1: Crawling a small repository")
    print("-" * 50)
    
    # Small repo for testing
    owner = "octocat"  # GitHub's example account
    repo = "Hello-World"  # Small test repo
    
    try:
        summary = await crawl_repository(owner, repo, resume=True)
        
        print(f"✅ Crawling completed!")
        print(f"📁 Data saved to: {summary['base_folder']}")
        print(f"💾 Size: {summary['data_size_mb']:.1f} MB")
        
        return summary
        
    except Exception as e:
        print(f"❌ Crawling failed: {e}")
        return None

async def example_analyze_crawled_data(base_folder: str):
    """Example: Analyze crawled data"""
    print(f"\n🔍 Example 2: Analyzing crawled data")
    print("-" * 50)
    
    # Load pull requests
    pull_requests_file = f"{base_folder}/pull/all_data.json"
    if os.path.exists(pull_requests_file):
        with open(pull_requests_file, 'r') as f:
            pull_requests = json.load(f)
        
        print(f"📊 Pull Requests Analysis:")
        print(f"   Total PRs: {len(pull_requests)}")
        
        # Analyze PR states
        states = {}
        authors = {}
        for pr in pull_requests:
            state = pr.get('state', 'unknown')
            author = pr.get('user', {}).get('login', 'unknown')
            
            states[state] = states.get(state, 0) + 1
            authors[author] = authors.get(author, 0) + 1
        
        print(f"   States: {dict(states)}")
        print(f"   Top contributors: {sorted(authors.items(), key=lambda x: x[1], reverse=True)[:5]}")
    
    # Load commits
    commits_file = f"{base_folder}/commit/all_data.json"
    if os.path.exists(commits_file):
        with open(commits_file, 'r') as f:
            commits = json.load(f)
        
        print(f"\n📊 Commits Analysis:")
        print(f"   Total commits: {len(commits)}")
        
        # Analyze commit authors
        commit_authors = {}
        for commit in commits:
            author = commit.get('commit', {}).get('author', {}).get('name', 'unknown')
            commit_authors[author] = commit_authors.get(author, 0) + 1
        
        print(f"   Top committers: {sorted(commit_authors.items(), key=lambda x: x[1], reverse=True)[:5]}")
    
    # Check single commits
    single_commits_folder = f"{base_folder}/commit/all"
    if os.path.exists(single_commits_folder):
        single_commit_files = [f for f in os.listdir(single_commits_folder) if f.endswith('.json')]
        print(f"\n📊 Single Commits:")
        print(f"   Detailed commits: {len(single_commit_files)}")

def example_data_for_reviewer_system(base_folder: str):
    """Example: Extract data needed for reviewer recommendation"""
    print(f"\n🎯 Example 3: Data for Reviewer Recommendation")
    print("-" * 50)
    
    # This shows how to extract the data your reviewer recommender needs
    reviewer_data = {
        'pull_requests': [],
        'reviews': [],
        'file_changes': [],
        'commit_details': []
    }
    
    try:
        # Extract PR data
        pull_requests_file = f"{base_folder}/pull/all_data.json"
        if os.path.exists(pull_requests_file):
            with open(pull_requests_file, 'r') as f:
                prs = json.load(f)
            
            for pr in prs:
                pr_data = {
                    'number': pr.get('number'),
                    'author': pr.get('user', {}).get('login'),
                    'title': pr.get('title'),
                    'files_changed': pr.get('changed_files', 0),
                    'additions': pr.get('additions', 0),
                    'deletions': pr.get('deletions', 0),
                    'created_at': pr.get('created_at'),
                    'merged_at': pr.get('merged_at'),
                }
                reviewer_data['pull_requests'].append(pr_data)
        
        # Extract review data (from each PR's reviews)
        for pr in reviewer_data['pull_requests']:
            pr_number = pr['number']
            reviews_file = f"{base_folder}/pull/{pr_number}/reviews/all_data.json"
            
            if os.path.exists(reviews_file):
                with open(reviews_file, 'r') as f:
                    reviews = json.load(f)
                
                for review in reviews:
                    review_data = {
                        'pr_number': pr_number,
                        'reviewer': review.get('user', {}).get('login'),
                        'state': review.get('state'),  # APPROVED, CHANGES_REQUESTED, etc.
                        'submitted_at': review.get('submitted_at')
                    }
                    reviewer_data['reviews'].append(review_data)
        
        print(f"📊 Extracted data for reviewer recommendation:")
        print(f"   Pull requests: {len(reviewer_data['pull_requests'])}")
        print(f"   Reviews: {len(reviewer_data['reviews'])}")
        
        # Save processed data for reviewer system
        output_file = f"{base_folder}/processed_for_reviewer_system.json"
        with open(output_file, 'w') as f:
            json.dump(reviewer_data, f, indent=2)
        
        print(f"💾 Processed data saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Failed to process data: {e}")

async def run_examples():
    """Run all examples"""
    print("🎯 GitHub Unified Crawler - Examples")
    print("=" * 60)
    
    # Check if we have a token
    if not os.environ.get('GH_TOKEN'):
        print("❌ Please set GH_TOKEN environment variable first")
        print("   export GH_TOKEN='your_github_token_here'")
        return
    
    # Example 1: Crawl small repo
    summary = await example_crawl_small_repo()
    
    if summary:
        base_folder = summary['base_folder']
        
        # Example 2: Analyze data
        await example_analyze_crawled_data(base_folder)
        
        # Example 3: Prepare data for reviewer system
        example_data_for_reviewer_system(base_folder)
    
    print("\n" + "=" * 60)
    print("🎉 Examples completed!")
    print("💡 Now try crawling your own repository:")
    print("   python main.py --owner YOUR_ORG --repo YOUR_REPO")

def check_environment():
    """Check if environment is ready"""
    print("🔧 Environment Check")
    print("-" * 30)
    
    checks = [
        check_python_version(),
        check_dependencies(), 
        check_github_token()
    ]
    
    if all(checks):
        print("\n✅ Environment is ready!")
        return True
    else:
        print("\n❌ Environment setup incomplete")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Crawler Setup and Examples")
    parser.add_argument('--check', action='store_true', help='Check environment setup')
    parser.add_argument('--examples', action='store_true', help='Run example crawls')
    
    args = parser.parse_args()
    
    if args.check:
        check_environment()
    elif args.examples:
        if check_environment():
            asyncio.run(run_examples())
    else:
        print("🎯 GitHub Unified Crawler Setup")
        print("Usage:")
        print("  python setup.py --check     # Check environment")
        print("  python setup.py --examples  # Run examples")