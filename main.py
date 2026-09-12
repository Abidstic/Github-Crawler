import argparse
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from unified_crawler import crawl_repository
from config import config
from utils import validate_crawled_data, get_folder_size_mb

def validate_environment():
    """Validate environment and dependencies"""
    if not config.github_token:
        print("❌ Error: GitHub token not found!")
        print("Please set the GH_TOKEN environment variable:")
        print("  export GH_TOKEN='your_github_token_here'")
        print("\nTo create a GitHub token:")
        print("1. Go to GitHub Settings → Developer settings → Personal access tokens")
        print("2. Generate new token with 'repo' permissions")
        print("3. Copy the token and set it as environment variable")
        sys.exit(1)
    
    print(f"✅ GitHub token found: {config.github_token[:8]}...")

def print_banner():
    """Print application banner"""
    print("=" * 80)
    print("🚀 GitHub Unified Crawler")
    print("   Complete repository data extraction with intelligent rate limiting")
    print("=" * 80)

def print_help_examples():
    """Print usage examples"""
    print("\n📖 Usage Examples:")
    print("  python main.py --owner facebook --repo react")
    print("  python main.py --owner microsoft --repo vscode --no-resume")
    print("  python main.py --owner tensorflow --repo tensorflow --conservative")
    print("  python main.py --owner myorg --repo myrepo --validate-only")
    print("  python main.py --owner myorg --repo myrepo --limit 100 --selection latest")

def configure_crawl_limit(args):
    """Set config.crawl_limit / config.crawl_selection from CLI args."""

    # Non-interactive path: explicit CLI flags
    if args.limit is not None:
        config.crawl_limit = max(0, args.limit)
        config.crawl_selection = args.selection or 'latest'
        return

    # Interactive path
    print("\n📊 Crawl Limiter")
    print("   This analysis only needs a limited, relevant sample rather than the full repo.")
    limit_input = input(
        "   How many pull requests would you like to crawl? "
        "(press Enter for all): "
    ).strip()

    if not limit_input:
        config.crawl_limit = 0
        config.crawl_selection = 'latest'
        return

    try:
        limit = int(limit_input)
    except ValueError:
        print("   ⚠️  Not a valid number — crawling all pull requests instead.")
        config.crawl_limit = 0
        config.crawl_selection = 'latest'
        return

    if limit <= 0:
        config.crawl_limit = 0
        config.crawl_selection = 'latest'
        return

    selection_input = input(
        "   Which pull requests? [latest/oldest/random] (default: latest): "
    ).strip().lower()

    config.crawl_limit = limit
    config.crawl_selection = selection_input if selection_input in ('latest', 'oldest', 'random') else 'latest'
    print(f"   ✅ Will crawl {config.crawl_limit} {config.crawl_selection} pull requests, "
          f"plus commits/files/reviews/comments for just those PRs.")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="GitHub Unified Crawler - Comprehensive repository data extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --owner facebook --repo react
  %(prog)s --owner microsoft --repo vscode --no-resume  
  %(prog)s --owner tensorflow --repo tensorflow --conservative

Features:
  • Intelligent rate limiting with automatic backoff
  • Real-time progress display with ETA
  • Resume capability from checkpoints
  • Parallel processing where possible
  • Comprehensive error handling and retry logic
  
The crawler will fetch:
  • All pull requests and their metadata
  • All repository commits
  • Files, reviews, commits, and comments for each PR
  • Detailed information for each unique commit
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--owner', 
        required=True,
        help='GitHub repository owner (e.g., facebook, microsoft)'
    )
    
    parser.add_argument(
        '--repo', 
        required=True,
        help='GitHub repository name (e.g., react, vscode)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--no-resume', 
        action='store_true',
        help='Start fresh crawl instead of resuming from checkpoint'
    )
    
    parser.add_argument(
        '--conservative',
        action='store_true', 
        help='Use conservative rate limiting (slower but safer)'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate existing crawled data without crawling'
    )
    
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=config.max_concurrent_requests,
        help=f'Maximum concurrent requests (default: {config.max_concurrent_requests})'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit crawl to N pull requests (and matching commits). Omit to be asked interactively, or pass 0 for no limit.'
    )
    
    parser.add_argument(
        '--selection',
        choices=['latest', 'oldest', 'random'],
        default=None,
        help='Which N pull requests to keep when --limit is set (default: latest)'
    )
    
    parser.add_argument(
        '--examples',
        action='store_true',
        help='Show usage examples and exit'
    )
    
    args = parser.parse_args()
    
    if args.examples:
        print_help_examples()
        return
    
    print_banner()
    validate_environment()
    
    # Apply configuration overrides
    if args.conservative:
        config.max_concurrent_requests = min(5, config.max_concurrent_requests)
        config.rate_limit_buffer = 500
        print("🐌 Conservative mode enabled")
    
    if args.max_concurrent:
        config.max_concurrent_requests = args.max_concurrent
    
    # Validation only mode
    if args.validate_only:
        await validate_only_mode(args.owner, args.repo)
        return
    
    # Crawl limiter: how much data to crawl, kept relevant across PRs/commits
    configure_crawl_limit(args)
    
    print(f"\n🎯 Target Repository: {args.owner}/{args.repo}")
    print(f"📁 Data will be saved to: {config.base_folder}/{args.owner}-{args.repo}")
    print(f"🔄 Resume mode: {'Enabled' if not args.no_resume else 'Disabled'}")
    print(f"⚡ Max concurrent requests: {config.max_concurrent_requests}")
    print(f"🛡️  Rate limit buffer: {config.rate_limit_buffer}")
    if config.crawl_limit > 0:
        print(f"🎯 Crawl limit: {config.crawl_limit} pull requests ({config.crawl_selection}) "
              f"— commits will be scoped to match")
    else:
        print(f"🎯 Crawl limit: none (full repository)")
    
    # Ask for confirmation for large repositories
    response = input("\nProceed with crawling? [Y/n]: ").strip().lower()
    if response in ['n', 'no']:
        print("Crawling cancelled.")
        return
    
    print("\n🚀 Starting unified crawl...\n")
    
    try:
        # Run the unified crawler
        summary = await crawl_repository(
            args.owner, 
            args.repo, 
            resume=not args.no_resume
        )
        
        # Print final summary
        print_final_summary(summary)
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawling stopped by user. Progress saved to checkpoint.")
        print("   Run the same command again to resume from where you left off.")
        
    except Exception as e:
        print(f"\n❌ Crawling failed: {e}")
        print("   Check logs for detailed error information.")
        print("   You can resume by running the same command again.")
        sys.exit(1)

async def validate_only_mode(owner: str, repo: str):
    """Run validation-only mode"""
    print(f"\n🔍 Validating existing data for {owner}/{repo}...")
    
    base_folder = f"{config.base_folder}/{owner}-{repo}"
    
    if not os.path.exists(base_folder):
        print(f"❌ No data found at {base_folder}")
        return
    
    # Run validation
    results = validate_crawled_data(base_folder)
    
    if results['valid']:
        print("✅ Data validation passed!")
        folder_size = get_folder_size_mb(base_folder)
        print(f"📊 Data size: {folder_size:.1f} MB")
        
        # Print comprehensive stats
        stats = results.get('stats', {})
        analysis = results.get('analysis', {})

        # Core data counts
        print(f"   Total Pull Requests: {stats.get('total_pull_requests', 0):,}")
        print(f"   Total Repository Commits: {stats.get('total_repository_commits', 0):,}")
        print(f"   Individual Commit Details: {stats.get('individual_commit_details', 0):,}")

        # Coverage analysis
        print(f"   Review Coverage: {stats.get('reviews_coverage_percentage', 0):.1f}%")
        print(f"   Comment Coverage: {stats.get('comments_coverage_percentage', 0):.1f}%")
        print(f"   Files Coverage: {stats.get('files_coverage_percentage', 0):.1f}%")

        # Quality assessment
        quality = analysis.get('quality', {})
        if quality:
            print(f"   Overall Quality Score: {quality.get('overall_score', 0)}/100")
            suitability = quality.get('suitability_for_reviewer_recommendation', 'unknown')
            print(f"   Reviewer Recommendation Suitability: {suitability.title()}")
            
            # Show key recommendations
            recommendations = quality.get('recommendations', [])
            if recommendations:
                print("   Key Recommendations:")
                for rec in recommendations[:2]:  # Show first 2 recommendations
                    print(f"     - {rec}")
                    
        # Show data quality warnings
        warnings = results.get('warnings', [])
        if warnings:
            print("   Warnings:")
            for warning in warnings[:3]:  # Show first 3 warnings
                print(f"     - {warning}")
    else:
        print("❌ Data validation failed!")
        for error in results['errors']:
            print(f"   Error: {error}")
        for warning in results['warnings']:
            print(f"   Warning: {warning}")

def print_final_summary(summary):
    """Print final crawling summary"""
    print("\n" + "=" * 80)
    print("🎉 CRAWLING COMPLETED!")
    print("=" * 80)
    
    print(f"📁 Repository: {summary['repository']}")
    print(f"💾 Data Location: {summary['base_folder']}")
    print(f"📊 Total Data Size: {summary['data_size_mb']:.1f} MB")
    
    # Print crawler details if available
    checkpoint_summary = summary.get('checkpoint_summary', {})
    crawler_details = checkpoint_summary.get('crawler_details', {})
    
    if crawler_details:
        print(f"\n📈 Crawler Summary:")
        for crawler_name, details in crawler_details.items():
            status = "✅" if details['completed'] else "❌"
            print(f"   {status} {crawler_name.replace('_', ' ').title()}: {details['progress']}")
            if details['failed_count'] > 0:
                print(f"      ⚠️ Failed items: {details['failed_count']}")
    
    # Run quick validation and show quality metrics
    try:
        validation_results = validate_crawled_data(summary['base_folder'])
        if validation_results.get('analysis', {}).get('quality'):
            quality = validation_results['analysis']['quality']
            print(f"\n📈 Data Quality Assessment:")
            print(f"   Quality Score: {quality.get('overall_score', 0)}/100")
            print(f"   Reviewer Recommendation Suitability: {quality.get('suitability_for_reviewer_recommendation', 'unknown').title()}")
            
            stats = validation_results.get('stats', {})
            review_coverage = stats.get('reviews_coverage_percentage', 0)
            if review_coverage > 0:
                print(f"   Review Coverage: {review_coverage:.1f}%")
    except Exception:
        pass  # Skip quality assessment if validation fails
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Your data is ready in: {summary['base_folder']}")
    print(f"   2. Run quality analysis: python data_quality_analyzer.py {summary['base_folder']}")
    print(f"   3. Use this path in your reviewer recommendation system")
    print(f"   4. Run validation: python main.py --owner {summary['repository'].split('/')[0]} --repo {summary['repository'].split('/')[1]} --validate-only")
    
    print("=" * 80)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)