# GitHub Unified Crawler

A production-grade GitHub repository crawler with intelligent rate limiting, real-time progress tracking, and comprehensive data extraction for reviewer recommendation systems.

## Features

- **Complete Data Extraction**: Crawls pull requests, commits, reviews, files, comments, and detailed commit information
- **Smart Rate Limiting**: Automatic GitHub API rate limit management with adaptive throttling
- **Real-time Progress Display**: Live CLI progress updates with ETA calculations and completion percentages
- **Resume Capability**: Automatic checkpointing allows resuming from any interruption point
- **Parallel Processing**: Intelligent concurrent processing optimized for GitHub API constraints
- **Data Quality Analysis**: Built-in validation and quality assessment for reviewer recommendation systems
- **Cross-platform Support**: Works on Windows, macOS, and Linux with proper terminal handling

## Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup validator
python3 setup.py
```

This will:
- Check Python version compatibility
- Install required dependencies
- Guide you through GitHub token setup
- Test API connectivity
- Validate your environment

### Option 2: Interactive Quick Start
```bash
# Run the interactive setup
python3 quickstart.py
```

This provides:
- Step-by-step repository selection
- Configuration guidance
- Token setup assistance
- Immediate crawling with guided options

### Option 3: Manual Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set GitHub token (get from GitHub Settings → Developer settings → Personal access tokens)
export GH_TOKEN='your_github_token_here'

# 3. Start crawling
python3 main.py --owner facebook --repo react
```

## What Gets Crawled

The crawler extracts comprehensive data in three optimized phases:

### Phase 1: Foundation Data (Sequential)
1. **Pull Requests** - All PRs with metadata, states, authors, dates
2. **Repository Commits** - Complete commit history with SHAs and metadata

### Phase 2: PR Dependencies (Parallel)
3. **PR Files** - File changes, additions, deletions, and diff patches for each PR
4. **PR Reviews** - Code reviews with reviewer identity, approval status, and timestamps
5. **PR Comments** - Review comments and discussion threads
6. **PR Commits** - Specific commits within each pull request

### Phase 3: Detailed Analysis (Intelligent Batching)
7. **Individual Commit Details** - Complete data for every unique commit across the repository

## Usage Examples

### Basic Commands
```bash
# Crawl a repository
python3 main.py --owner facebook --repo react

# Use conservative rate limiting for large repos
python3 main.py --owner tensorflow --repo tensorflow --conservative

# Start fresh without resuming
python3 main.py --owner microsoft --repo vscode --no-resume

# Validate existing crawled data
python3 main.py --owner facebook --repo react --validate-only
```

### Advanced Configuration
```bash
# Custom concurrent request limit
python3 main.py --owner myorg --repo myrepo --max-concurrent 5

# Show all available options
python3 main.py --help

# Display usage examples
python3 main.py --examples
```

### Data Quality Analysis
```bash
# Analyze data quality for reviewer recommendation systems
python3 data_quality_analyzer.py crawled-data/facebook-react
```

## Data Structure

```
crawled-data/
└── {owner}-{repo}/
    ├── pull/
    │   ├── all_data.json                    # Complete PR list with metadata
    │   └── {pr_number}/                     # Individual PR folders
    │       ├── files/all_data.json          # Files changed in this PR
    │       ├── reviews/all_data.json        # Code reviews for this PR
    │       ├── commits/all_data.json        # Commits in this PR
    │       └── comments/all_data.json       # Review comments
    ├── commit/
    │   ├── all_data.json                    # Repository commit history
    │   └── all/                             # Individual commit details
    │       └── {commit_sha}.json            # Detailed commit information
    ├── logs/
    │   └── unified_crawler_{timestamp}.log  # Detailed execution logs
    └── data_quality_analysis.json          # Quality assessment results
```

## Real-time Progress Display

During crawling, you'll see live updates:

```
================================================================================
GitHub Crawler - facebook/react
Total Runtime: 45m 23s
Current: Processing commit batches batch 15/87
================================================================================
Rate Limit [GOOD]: 3247/5000 (Reset: 14:30:00) - 35.1% used

[COMPLETE] Pull Requests
   [████████████████████████████████████████] 100.0%
   Progress: 2,431/2,431 (Failed: 0, Skipped: 0)
   Rate: 54.2/min | Duration: 44m 52s | ETA: Done

[RUNNING] Single Commits
   [████████████████████████░░░░░░░░░░░░░░░░] 62.3%
   Progress: 9,847/15,806 (Failed: 12, Skipped: 0)
   Rate: 218.5/min | Duration: 45m 06s | ETA: 27m 18s

Overall Progress: [████████████████████████████░░░░░░░░░░░░] 71.2%
   47,329/66,498 total items
================================================================================
Press Ctrl+C to stop gracefully
```

## Rate Limiting Intelligence

The crawler implements sophisticated rate limit management:

- **Adaptive Throttling**: Automatically adjusts request frequency based on remaining quota
- **Conservative Mode**: Activated after rate limit hits or with `--conservative` flag
- **Smart Batching**: Optimizes parallel requests while respecting API constraints
- **Automatic Recovery**: Waits for rate limit reset with progress display

### Rate Limit Behavior:
- **> 1000 remaining**: Full speed parallel processing
- **200-1000 remaining**: Moderate throttling
- **< 200 remaining**: Conservative mode with delays
- **Exhausted**: Automatic wait until reset with countdown timer

## Resume and Checkpoint System

The crawler automatically saves progress and handles interruptions:

```bash
# If crawling is interrupted, simply rerun the same command
python3 main.py --owner facebook --repo react

# The system will automatically:
# ✓ Skip completed crawlers
# ✓ Resume incomplete operations
# ✓ Continue from last checkpoint
# ✓ Preserve all previously crawled data
```

Checkpoint data includes:
- Completed crawler status
- Progress counters for each phase
- Failed and skipped item tracking
- Timing and performance metrics

## Data Quality Assessment

The crawler provides comprehensive data quality analysis for reviewer recommendation systems:

### Quality Metrics:
- **Review Coverage**: Percentage of PRs with code reviews
- **Comment Coverage**: Percentage of PRs with review comments
- **File Coverage**: Percentage of PRs with file change data
- **Commit Coverage**: Percentage of commits with detailed information

### Quality Scoring:
- **Excellent (70-100)**: Ready for production reviewer recommendation systems
- **Good (50-69)**: Suitable for most recommendation algorithms
- **Limited (30-49)**: May require supplementing with additional repositories
- **Poor (<30)**: Not recommended for reviewer recommendation

### Sample Quality Results:
```
Repository: facebook/react
Overall Quality Score: 85/100
Reviewer Recommendation Suitability: Excellent

Data Analysis:
- Total Pull Requests: 2,431
- Review Coverage: 24.1% (586 PRs with reviews)
- Total Reviews: 1,845
- Comment Coverage: 11.9%
- File Coverage: 99.4%

Recommendations:
- Data is well-suited for reviewer recommendation systems
- Strong file change data available for code-based features
- Sufficient review data for learning reviewer patterns
```

## Integration with Reviewer Recommendation Systems

The crawled data is optimized for machine learning applications:

### Key Data Points Available:
- **Reviewer Expertise**: Historical review patterns by file/directory
- **Code Change Analysis**: File modifications, additions, deletions
- **Collaboration Networks**: Author-reviewer relationship patterns
- **Temporal Patterns**: Review timing and development velocity
- **Social Signals**: Comment sentiment and review thoroughness

### Example Data Access:
```python
import json

# Load pull requests
with open('crawled-data/facebook-react/pull/all_data.json') as f:
    pull_requests = json.load(f)

# Load reviews for a specific PR
with open('crawled-data/facebook-react/pull/123/reviews/all_data.json') as f:
    reviews = json.load(f)

# Load detailed commit information
with open('crawled-data/facebook-react/commit/all/abc123def.json') as f:
    commit_details = json.load(f)
```

## Configuration Options

Customize behavior by modifying `config.py`:

```python
# Rate limiting settings
max_requests_per_hour = 4800        # Conservative GitHub API limit
rate_limit_buffer = 200             # Safety buffer for rate limits
max_concurrent_requests = 10        # Parallel request limit

# Retry and backoff settings
max_retries = 3                     # Number of retries for failed requests
base_backoff_delay = 60.0           # Base delay for exponential backoff
max_backoff_delay = 300.0           # Maximum delay (5 minutes)

# Progress and checkpoint settings
progress_update_interval = 1.0      # Progress display update frequency
checkpoint_interval = 50            # Save checkpoint every N operations
```

## Error Handling and Recovery

The crawler provides robust error handling:

- **Network Failures**: Automatic retry with exponential backoff
- **API Rate Limits**: Smart waiting with progress display
- **Invalid Responses**: Graceful error logging and continuation
- **Interruptions**: Checkpoint saving for seamless resume
- **Memory Management**: Efficient processing of large datasets

## Performance Optimization

### For Large Repositories:
```bash
# Use conservative mode
python3 main.py --owner tensorflow --repo tensorflow --conservative

# Reduce concurrent requests
python3 main.py --owner large-org --repo huge-repo --max-concurrent 3
```

### For Fast Networks:
```bash
# Increase parallelism
python3 main.py --owner small-org --repo fast-repo --max-concurrent 20
```

## Troubleshooting

### Common Issues and Solutions:

**Rate Limit Exceeded**
```bash
# The crawler handles this automatically, but you can force conservative mode
python3 main.py --owner repo --repo name --conservative
```

**Interrupted Crawl**
```bash
# Simply rerun - automatic resume
python3 main.py --owner repo --repo name
```

**Memory Issues with Large Repos**
```bash
# Reduce concurrent processing
python3 main.py --owner repo --repo name --max-concurrent 3
```

**Missing GitHub Token**
```bash
# Run setup script for guidance
python3 setup.py
```

**Validation Errors**
```bash
# Check data integrity
python3 main.py --owner repo --repo name --validate-only
```

### Getting Detailed Information:
1. Check log files in `crawled-data/{owner}-{repo}/logs/`
2. Run `python3 main.py --examples` for usage examples
3. Use `python3 setup.py` to validate environment
4. Run `python3 data_quality_analyzer.py` for data quality insights

## Requirements

- **Python**: 3.8 or higher
- **Dependencies**: Listed in `requirements.txt`
- **GitHub Token**: Personal access token with 'repo' permissions
- **Network**: Stable internet connection for API requests
- **Storage**: Varies by repository size (typically 50MB - 2GB)

## Security and Privacy

- GitHub token read from environment variable only
- No credential storage in code or configuration files
- Respects GitHub's API terms of service and rate limits
- Only accesses public repository data (or private repos you have access to)

## Performance Benchmarks

| Repository Size | Estimated Time | Data Size | API Requests |
|----------------|----------------|-----------|--------------|
| Small (< 100 PRs) | 5-15 minutes | 10-50 MB | 500-1,500 |
| Medium (100-1000 PRs) | 30-90 minutes | 50-200 MB | 1,500-8,000 |
| Large (1000+ PRs) | 2-8 hours | 200MB-2GB | 8,000+ |

Times vary based on network speed, rate limits, and repository complexity.