# 🚀 GitHub Unified Crawler

A comprehensive, intelligent GitHub repository crawler with real-time progress tracking, smart rate limiting, and automatic resume capabilities.

## ✨ Features

-   **🎯 Single Command**: Crawl entire repository with one command
-   **⚡ Async & Parallel**: Intelligent parallel processing where possible
-   **🛡️ Smart Rate Limiting**: Automatic GitHub API rate limit management
-   **📊 Real-time Progress**: Live CLI progress display with ETA
-   **💾 Resume Capability**: Automatic checkpointing and resume from failures
-   **🔄 Fault Tolerant**: Handles network errors, API failures, and interruptions
-   **📈 Comprehensive Data**: PRs, commits, reviews, files, comments, and detailed commit info

## 🏗️ What It Crawls

1. **Pull Requests** - All PRs with metadata
2. **Repository Commits** - All commits in the repository
3. **PR Files** - Files changed in each PR
4. **PR Reviews** - Reviews for each PR
5. **PR Commits** - Commits within each PR
6. **PR Comments** - Review comments for each PR
7. **Single Commits** - Detailed data for each unique commit

## 📦 Installation

1. **Clone or download the project files**

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up GitHub token:**

```bash
# Get a GitHub personal access token with 'repo' permissions
# From: GitHub Settings → Developer settings → Personal access tokens

export GH_TOKEN='your_github_token_here'
```

## 🚀 Quick Start

**Note: If python doesn’t work on your system, try using python3 instead.**

### Basic Usage

```bash
# Crawl complete repository
python main.py --owner facebook --repo react

# Crawl without resuming from previous attempts
python main.py --owner microsoft --repo vscode --no-resume

# Use conservative rate limiting (recommended for large repos)
python main.py --owner tensorflow --repo tensorflow --conservative
```

### Advanced Options

```bash
# Validate existing crawled data
python main.py --owner facebook --repo react --validate-only

# Show usage examples
python main.py --examples

# Custom concurrent request limit
python main.py --owner myorg --repo myrepo --max-concurrent 5
```

## 📊 Real-time Progress Display

While running, you'll see a live updating display:

```
================================================================================
🚀 GitHub Crawler - facebook/react
⏱️  Total Runtime: 45m 23s
🔄 Current: Processing commit batches batch 15/87
================================================================================
🟢 Rate Limit: 3247/5000 (Reset: 14:30:00) - 35.1% used

✅ Pull Requests
   [████████████████████████████████████████] 100.0%
   Progress: 2,431/2,431 (Failed: 0, Skipped: 0)
   Rate: 54.2/min | Duration: 44m 52s | ETA: N/A

🔄 Single Commits
   [████████████████████████░░░░░░░░░░░░░░░░] 62.3%
   Progress: 9,847/15,806 (Failed: 12, Skipped: 0)
   Rate: 218.5/min | Duration: 45m 06s | ETA: 27m 18s

📊 Overall Progress: [████████████████████████████░░░░░░░░░░░░] 71.2%
   47,329/66,498 total items
================================================================================
Press Ctrl+C to stop gracefully
```

## 📁 Output Structure

```
crawled-data/
└── {owner}-{repo}/
    ├── pull/
    │   ├── all_data.json                    # All pull requests
    │   └── {pr_number}/
    │       ├── files/all_data.json          # PR files
    │       ├── reviews/all_data.json        # PR reviews
    │       ├── commits/all_data.json        # PR commits
    │       └── comments/all_data.json       # PR comments
    ├── commit/
    │   ├── all_data.json                    # All repository commits
    │   └── all/
    │       └── {sha}.json                   # Individual commit details
    ├── logs/
    │   └── unified_crawler_{timestamp}.log  # Detailed logs
    └── .checkpoint.json                     # Resume checkpoint (auto-deleted when complete)
```

## 🛡️ Rate Limiting Intelligence

The crawler automatically manages GitHub's API rate limits:

-   **5,000 requests/hour** for authenticated users
-   **Smart throttling** based on remaining quota
-   **Conservative mode** after rate limit hits
-   **Automatic waiting** with progress display
-   **Optimal batching** for parallel requests

### Rate Limit Strategies:

-   **Green (>1000 remaining)**: Full speed parallel processing
-   **Yellow (200-1000 remaining)**: Moderate throttling
-   **Red (<200 remaining)**: Conservative mode with delays
-   **Exhausted**: Automatic wait until reset with countdown

## 💾 Resume Capability

The crawler automatically saves progress and can resume from any point:

```bash
# If interrupted, simply run the same command again
python main.py --owner facebook --repo react

# The crawler will automatically:
# ✅ Skip completed crawlers
# ✅ Resume incomplete operations
# ✅ Continue from last checkpoint
```

## 🔧 Configuration

Modify `config.py` to customize behavior:

```python
# Rate limiting
max_requests_per_hour = 4800    # Conservative limit
rate_limit_buffer = 200         # Safety buffer

# Performance
max_concurrent_requests = 10    # Parallel requests
items_per_page = 100           # GitHub API max

# Retry behavior
max_retries = 3                # Request retries
base_backoff_delay = 60.0      # Base delay seconds
```

## 🚨 Error Handling

The crawler handles various scenarios gracefully:

-   **Network failures**: Automatic retry with exponential backoff
-   **Rate limit exceeded**: Smart waiting with progress display
-   **API errors**: Detailed logging and graceful continuation
-   **Interruptions**: Save checkpoint and resume capability
-   **Invalid data**: Skip and continue with error logging

## 📋 Validation

Validate your crawled data:

```bash
python main.py --owner facebook --repo react --validate-only
```

This checks:

-   JSON file integrity
-   Expected folder structure
-   Data completeness
-   File counts and sizes

## 🎯 Integration with Reviewer Recommender

After crawling, your data structure is ready for the reviewer recommendation system:

```python
# In your reviewer recommender
CRAWLED_DATA_PATH = "crawled-data/facebook-react"

# Access the data:
# - Pull requests: {CRAWLED_DATA_PATH}/pull/all_data.json
# - Commits: {CRAWLED_DATA_PATH}/commit/all_data.json
# - Individual commits: {CRAWLED_DATA_PATH}/commit/all/{sha}.json
# - PR dependencies: {CRAWLED_DATA_PATH}/pull/{pr_number}/{type}/all_data.json
```

## 🐛 Troubleshooting

### Common Issues:

**1. Rate Limit Errors**

```bash
# Use conservative mode
python main.py --owner repo --repo name --conservative
```

**2. Large Repository Timeouts**

```bash
# Reduce concurrent requests
python main.py --owner repo --repo name --max-concurrent 3
```

**3. Interrupted Crawl**

```bash
# Simply rerun - it will resume automatically
python main.py --owner repo --repo name
```

**4. Missing Token**

```bash
# Set GitHub token
export GH_TOKEN='ghp_your_token_here'
```

### Getting Help:

1. Run with `--examples` for usage examples
2. Check log files in `crawled-data/{owner}-{repo}/logs/`
3. Use `--validate-only` to check data integrity

## 📈 Performance Tips

-   **Large repositories**: Use `--conservative` mode
-   **Fast networks**: Increase `--max-concurrent`
-   **Rate limit issues**: The crawler handles this automatically
-   **Resume interrupted crawls**: Just rerun the same command

## 🔒 Security

-   Token is read from environment variable only
-   No token storage in code or files
-   Respects GitHub's rate limits and terms of service
