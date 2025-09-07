#!/usr/bin/env python3
"""
Data Quality Analyzer for Crawled GitHub Repositories
Analyzes the completeness and quality of crawled data for reviewer recommendation systems.
"""

import json
import os
import sys
from typing import Dict, Any, List
from collections import defaultdict

def analyze_repository_quality(base_folder_path: str) -> Dict[str, Any]:
    """Comprehensive analysis of repository data quality"""
    
    analysis = {
        'repository_path': base_folder_path,
        'overall_quality': 'unknown',
        'usability_for_reviewer_recommendation': 'unknown',
        'pull_requests': {},
        'reviews': {},
        'comments': {},
        'commits': {},
        'recommendations': []
    }
    
    try:
        # Analyze pull requests
        analysis['pull_requests'] = analyze_pull_requests(base_folder_path)
        
        # Analyze reviews and comments
        analysis['reviews'], analysis['comments'] = analyze_reviews_and_comments(base_folder_path)
        
        # Analyze commits
        analysis['commits'] = analyze_commits(base_folder_path)
        
        # Determine overall quality
        analysis['overall_quality'] = determine_overall_quality(analysis)
        
        # Assess usability for reviewer recommendation
        analysis['usability_for_reviewer_recommendation'] = assess_reviewer_recommendation_viability(analysis)
        
        # Generate recommendations
        analysis['recommendations'] = generate_recommendations(analysis)
        
    except Exception as e:
        analysis['error'] = str(e)
    
    return analysis

def analyze_pull_requests(base_folder_path: str) -> Dict[str, Any]:
    """Analyze pull request data"""
    pull_folder = f"{base_folder_path}/pull"
    pr_analysis = {
        'total_count': 0,
        'has_data': False,
        'status': 'missing'
    }
    
    all_data_file = f"{pull_folder}/all_data.json"
    if os.path.exists(all_data_file):
        try:
            with open(all_data_file, 'r') as f:
                pull_data = json.load(f)
                pr_analysis['total_count'] = len(pull_data)
                pr_analysis['has_data'] = len(pull_data) > 0
                pr_analysis['status'] = 'available'
                
                # Analyze PR states
                states = defaultdict(int)
                for pr in pull_data:
                    states[pr.get('state', 'unknown')] += 1
                pr_analysis['states'] = dict(states)
                
        except Exception as e:
            pr_analysis['error'] = str(e)
            pr_analysis['status'] = 'corrupted'
    
    return pr_analysis

def analyze_reviews_and_comments(base_folder_path: str) -> tuple:
    """Analyze review and comment data across all PRs"""
    pull_folder = f"{base_folder_path}/pull"
    
    reviews_analysis = {
        'prs_with_reviews': 0,
        'prs_without_reviews': 0,
        'total_reviews': 0,
        'review_percentage': 0.0,
        'status': 'missing'
    }
    
    comments_analysis = {
        'prs_with_comments': 0,
        'prs_without_comments': 0,
        'total_comments': 0,
        'comment_percentage': 0.0,
        'status': 'missing'
    }
    
    if not os.path.exists(pull_folder):
        return reviews_analysis, comments_analysis
    
    # Get all PR directories
    pr_dirs = [d for d in os.listdir(pull_folder) if d.isdigit()]
    total_prs = len(pr_dirs)
    
    if total_prs == 0:
        return reviews_analysis, comments_analysis
    
    reviews_analysis['status'] = 'available'
    comments_analysis['status'] = 'available'
    
    for pr_dir in pr_dirs:
        pr_path = f"{pull_folder}/{pr_dir}"
        
        # Check reviews
        reviews_file = f"{pr_path}/reviews/all_data.json"
        if os.path.exists(reviews_file):
            try:
                with open(reviews_file, 'r') as f:
                    review_data = json.load(f)
                    if len(review_data) > 0:
                        reviews_analysis['prs_with_reviews'] += 1
                        reviews_analysis['total_reviews'] += len(review_data)
                    else:
                        reviews_analysis['prs_without_reviews'] += 1
            except:
                reviews_analysis['prs_without_reviews'] += 1
        else:
            reviews_analysis['prs_without_reviews'] += 1
        
        # Check comments
        comments_file = f"{pr_path}/comments/all_data.json"
        if os.path.exists(comments_file):
            try:
                with open(comments_file, 'r') as f:
                    comment_data = json.load(f)
                    if len(comment_data) > 0:
                        comments_analysis['prs_with_comments'] += 1
                        comments_analysis['total_comments'] += len(comment_data)
                    else:
                        comments_analysis['prs_without_comments'] += 1
            except:
                comments_analysis['prs_without_comments'] += 1
        else:
            comments_analysis['prs_without_comments'] += 1
    
    # Calculate percentages
    if total_prs > 0:
        reviews_analysis['review_percentage'] = (reviews_analysis['prs_with_reviews'] / total_prs) * 100
        comments_analysis['comment_percentage'] = (comments_analysis['prs_with_comments'] / total_prs) * 100
    
    return reviews_analysis, comments_analysis

def analyze_commits(base_folder_path: str) -> Dict[str, Any]:
    """Analyze commit data"""
    commit_analysis = {
        'total_commits': 0,
        'individual_commits': 0,
        'individual_commit_percentage': 0.0,
        'status': 'missing'
    }
    
    # Check main commits file
    commits_file = f"{base_folder_path}/commit/all_data.json"
    if os.path.exists(commits_file):
        try:
            with open(commits_file, 'r') as f:
                commit_data = json.load(f)
                commit_analysis['total_commits'] = len(commit_data)
                commit_analysis['status'] = 'available'
        except:
            commit_analysis['status'] = 'corrupted'
    
    # Check individual commits
    individual_commits_folder = f"{base_folder_path}/commit/all"
    if os.path.exists(individual_commits_folder):
        individual_files = [f for f in os.listdir(individual_commits_folder) if f.endswith('.json')]
        commit_analysis['individual_commits'] = len(individual_files)
        
        if commit_analysis['total_commits'] > 0:
            commit_analysis['individual_commit_percentage'] = (
                commit_analysis['individual_commits'] / commit_analysis['total_commits']
            ) * 100
    
    return commit_analysis

def determine_overall_quality(analysis: Dict[str, Any]) -> str:
    """Determine overall data quality"""
    
    # Check if basic data exists
    if not analysis['pull_requests']['has_data']:
        return 'poor'
    
    # Check review coverage
    review_percentage = analysis['reviews']['review_percentage']
    
    if review_percentage >= 50:
        return 'excellent'
    elif review_percentage >= 20:
        return 'good'
    elif review_percentage >= 5:
        return 'fair'
    else:
        return 'poor'

def assess_reviewer_recommendation_viability(analysis: Dict[str, Any]) -> str:
    """Assess if data is suitable for reviewer recommendation systems"""
    
    review_percentage = analysis['reviews']['review_percentage']
    total_reviews = analysis['reviews']['total_reviews']
    
    if review_percentage >= 30 and total_reviews >= 100:
        return 'excellent'
    elif review_percentage >= 15 and total_reviews >= 50:
        return 'good'
    elif review_percentage >= 5 and total_reviews >= 20:
        return 'limited'
    else:
        return 'insufficient'

def generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on analysis"""
    recommendations = []
    
    review_percentage = analysis['reviews']['review_percentage']
    total_reviews = analysis['reviews']['total_reviews']
    
    if review_percentage < 5:
        recommendations.append(
            "WARNING: Very low review coverage. This repository may not be suitable for "
            "reviewer recommendation systems. Consider finding repositories with more active review practices."
        )
    
    if review_percentage < 20:
        recommendations.append(
            "Consider supplementing this data with additional repositories that have higher review coverage."
        )
    
    if total_reviews < 50:
        recommendations.append(
            "Low total number of reviews may result in poor recommendation accuracy. "
            "Consider combining data from multiple similar repositories."
        )
    
    if analysis['commits']['individual_commit_percentage'] < 80:
        recommendations.append(
            "Some individual commit details are missing. This may affect the quality of "
            "code change analysis in your recommendation system."
        )
    
    if not recommendations:
        recommendations.append(
            "Data quality looks good for reviewer recommendation systems. "
            "You should be able to extract meaningful patterns from this data."
        )
    
    return recommendations

def print_analysis_report(analysis: Dict[str, Any]):
    """Print a formatted analysis report"""
    
    print("=" * 80)
    print("GITHUB REPOSITORY DATA QUALITY ANALYSIS")
    print("=" * 80)
    print(f"Repository: {analysis['repository_path']}")
    print(f"Overall Quality: {analysis['overall_quality'].upper()}")
    print(f"Reviewer Recommendation Viability: {analysis['usability_for_reviewer_recommendation'].upper()}")
    print()
    
    # Pull Requests
    pr = analysis['pull_requests']
    print(f"PULL REQUESTS:")
    print(f"  Total: {pr['total_count']}")
    print(f"  Status: {pr['status']}")
    if 'states' in pr:
        for state, count in pr['states'].items():
            print(f"  {state}: {count}")
    print()
    
    # Reviews
    rev = analysis['reviews']
    print(f"REVIEWS:")
    print(f"  PRs with reviews: {rev['prs_with_reviews']}")
    print(f"  PRs without reviews: {rev['prs_without_reviews']}")
    print(f"  Total reviews: {rev['total_reviews']}")
    print(f"  Review coverage: {rev['review_percentage']:.1f}%")
    print()
    
    # Comments
    com = analysis['comments']
    print(f"COMMENTS:")
    print(f"  PRs with comments: {com['prs_with_comments']}")
    print(f"  PRs without comments: {com['prs_without_comments']}")
    print(f"  Total comments: {com['total_comments']}")
    print(f"  Comment coverage: {com['comment_percentage']:.1f}%")
    print()
    
    # Commits
    commits = analysis['commits']
    print(f"COMMITS:")
    print(f"  Total commits: {commits['total_commits']}")
    print(f"  Individual commit details: {commits['individual_commits']}")
    print(f"  Individual commit coverage: {commits['individual_commit_percentage']:.1f}%")
    print()
    
    # Recommendations
    print("RECOMMENDATIONS:")
    for i, rec in enumerate(analysis['recommendations'], 1):
        print(f"  {i}. {rec}")
    print()
    
    print("=" * 80)

def main():
    """Main function for command line usage"""
    if len(sys.argv) != 2:
        print("Usage: python data_quality_analyzer.py <path_to_crawled_data>")
        print("Example: python data_quality_analyzer.py crawled-data/facebook-react")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    
    if not os.path.exists(repo_path):
        print(f"Error: Path {repo_path} does not exist")
        sys.exit(1)
    
    analysis = analyze_repository_quality(repo_path)
    print_analysis_report(analysis)
    
    # Save detailed analysis to file
    output_file = f"{repo_path}/data_quality_analysis.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"Detailed analysis saved to: {output_file}")
    except Exception as e:
        print(f"Warning: Could not save analysis file: {e}")

if __name__ == "__main__":
    main()