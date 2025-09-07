import os
import json
import asyncio
import aiofiles
from typing import List, Set, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_all_json_files_in_folder(folder_path: str) -> List[str]:
    """Get all JSON files in a folder"""
    if not os.path.exists(folder_path):
        return []
    
    return [
        file for file in os.listdir(folder_path) 
        if file.endswith('.json') and not file.startswith('.')
    ]

async def read_json_file_async(file_path: str) -> Dict[str, Any]:
    """Asynchronously read JSON file"""
    try:
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Failed to read JSON file {file_path}: {e}")
        return {}

async def write_json_file_async(file_path: str, data: Any):
    """Asynchronously write JSON file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(json.dumps(data, indent=2))
    except Exception as e:
        logger.error(f"Failed to write JSON file {file_path}: {e}")
        raise

def get_all_pull_numbers(pull_folder_path: str) -> List[int]:
    """Extract all pull request numbers from crawled data"""
    if not os.path.exists(pull_folder_path):
        return []
    
    pull_numbers = set()
    
    # First try to get from all_data.json (main file)
    all_data_file = f'{pull_folder_path}/all_data.json'
    if os.path.exists(all_data_file):
        try:
            with open(all_data_file, 'r') as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        if 'number' in item:
                            pull_numbers.add(item['number'])
                    
                    logger.info(f"Found {len(pull_numbers)} PR numbers from all_data.json")
                    return sorted(list(pull_numbers))
                    
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to read all_data.json: {e}")
    
    # Fallback: try individual page files
    json_files = get_all_json_files_in_folder(pull_folder_path)
    
    for json_file in json_files:
        if json_file == 'all_data.json':  # Already tried above
            continue
            
        try:
            with open(f'{pull_folder_path}/{json_file}', 'r') as f:
                data = json.load(f)
                
                # Handle both list and single PR formats
                if isinstance(data, list):
                    for item in data:
                        if 'number' in item:
                            pull_numbers.add(item['number'])
                elif isinstance(data, dict) and 'number' in data:
                    pull_numbers.add(data['number'])
                    
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to process file {json_file}: {e}")
    
    result = sorted(list(pull_numbers))
    logger.info(f"Total PR numbers found: {len(result)}")
    return result

def get_all_commit_shas_from_commits(commit_folder_path: str) -> Set[str]:
    """Extract all commit SHAs from crawled commit data"""
    if not os.path.exists(commit_folder_path):
        return set()
    
    json_files = get_all_json_files_in_folder(commit_folder_path)
    commit_shas = set()
    
    for json_file in json_files:
        try:
            with open(f'{commit_folder_path}/{json_file}', 'r') as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    for commit in data:
                        if 'sha' in commit:
                            commit_shas.add(commit['sha'])
                            
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to process commit file {json_file}: {e}")
    
    return commit_shas

def get_all_commit_shas_from_reviews(pull_folder_path: str) -> Set[str]:
    """Extract commit SHAs mentioned in pull request reviews"""
    if not os.path.exists(pull_folder_path):
        return set()
    
    commit_shas = set()
    pull_numbers = get_all_pull_numbers(pull_folder_path)
    
    for pr_number in pull_numbers:
        reviews_path = f'{pull_folder_path}/{pr_number}/reviews'
        if not os.path.exists(reviews_path):
            continue
            
        json_files = get_all_json_files_in_folder(reviews_path)
        
        for json_file in json_files:
            try:
                with open(f'{reviews_path}/{json_file}', 'r') as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        for review in data:
                            if 'commit_id' in review and review['commit_id']:
                                commit_shas.add(review['commit_id'])
                                
            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                logger.warning(f"Failed to process review file {json_file}: {e}")
    
    return commit_shas

def get_all_unique_commit_shas(base_folder_path: str) -> List[str]:
    """Get all unique commit SHAs from both commits and reviews"""
    commit_folder = f"{base_folder_path}/commit"
    pull_folder = f"{base_folder_path}/pull"
    
    commit_shas_from_commits = get_all_commit_shas_from_commits(commit_folder)
    commit_shas_from_reviews = get_all_commit_shas_from_reviews(pull_folder)
    
    # Combine and deduplicate
    all_commit_shas = commit_shas_from_commits.union(commit_shas_from_reviews)
    
    logger.info(f"Found {len(commit_shas_from_commits)} SHAs from commits, "
               f"{len(commit_shas_from_reviews)} from reviews, "
               f"{len(all_commit_shas)} unique total")
    
    return sorted(list(all_commit_shas))

def get_existing_single_commits(single_commits_folder: str) -> Set[str]:
    """Get set of already crawled single commit SHAs"""
    if not os.path.exists(single_commits_folder):
        return set()
    
    existing_files = [
        f.replace('.json', '') for f in os.listdir(single_commits_folder)
        if f.endswith('.json') and not f.startswith('.')
    ]
    
    return set(existing_files)

def calculate_remaining_work(base_folder_path: str) -> Dict[str, int]:
    """Calculate how much work remains for each crawler"""
    remaining = {}
    
    # Check existing data
    pull_numbers = get_all_pull_numbers(f"{base_folder_path}/pull")
    commit_shas = get_all_unique_commit_shas(base_folder_path)
    existing_single_commits = get_existing_single_commits(f"{base_folder_path}/commit/all")
    
    # Calculate remaining PR dependencies
    for dependency in ['files', 'reviews', 'commits', 'comments']:
        completed_count = 0
        for pr_number in pull_numbers:
            dep_folder = f"{base_folder_path}/pull/{pr_number}/{dependency}"
            if os.path.exists(dep_folder) and get_all_json_files_in_folder(dep_folder):
                completed_count += 1
        
        remaining[f"pr_{dependency}"] = len(pull_numbers) - completed_count
    
    # Calculate remaining single commits
    remaining['single_commits'] = len(commit_shas) - len(existing_single_commits)
    
    return remaining

def ensure_folder_structure(base_folder_path: str):
    """Ensure all necessary folders exist"""
    folders = [
        f"{base_folder_path}/pull",
        f"{base_folder_path}/commit",
        f"{base_folder_path}/commit/all",
        f"{base_folder_path}/logs"
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

async def batch_process_async(items: List[Any], batch_size: int, 
                            process_func, *args, **kwargs) -> List[Any]:
    """Process items in async batches"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # Process batch
        batch_tasks = [process_func(item, *args, **kwargs) for item in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        results.extend(batch_results)
    
    return results

def get_folder_size_mb(folder_path: str) -> float:
    """Get total size of folder in MB"""
    if not os.path.exists(folder_path):
        return 0.0
    
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(file_path)
            except OSError:
                pass
    
    return total_size / (1024 * 1024)  # Convert to MB

def cleanup_empty_folders(base_path: str):
    """Remove empty folders recursively"""
    for root, dirs, files in os.walk(base_path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):  # Empty directory
                    os.rmdir(dir_path)
                    logger.debug(f"Removed empty folder: {dir_path}")
            except OSError:
                pass


def validate_crawled_data(base_folder_path: str) -> Dict[str, Any]:
    """Validate integrity of crawled data with accurate counts and analysis"""
    validation_results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {},
        'analysis': {}
    }
    
    try:
        # Analyze pull requests DATA (not just files)
        pull_analysis = _analyze_pull_requests_data(base_folder_path)
        validation_results['stats'].update(pull_analysis['stats'])
        validation_results['analysis']['pull_requests'] = pull_analysis
        
        if pull_analysis['errors']:
            validation_results['errors'].extend(pull_analysis['errors'])
            validation_results['valid'] = False
        if pull_analysis['warnings']:
            validation_results['warnings'].extend(pull_analysis['warnings'])
        
        # Analyze commits DATA
        commit_analysis = _analyze_commits_data(base_folder_path)
        validation_results['stats'].update(commit_analysis['stats'])
        validation_results['analysis']['commits'] = commit_analysis
        
        if commit_analysis['errors']:
            validation_results['errors'].extend(commit_analysis['errors'])
            validation_results['valid'] = False
        if commit_analysis['warnings']:
            validation_results['warnings'].extend(commit_analysis['warnings'])
        
        # Analyze PR dependencies (reviews, comments, files)
        pr_deps_analysis = _analyze_pr_dependencies_data(base_folder_path)
        validation_results['stats'].update(pr_deps_analysis['stats'])
        validation_results['analysis']['pr_dependencies'] = pr_deps_analysis
        
        if pr_deps_analysis['warnings']:
            validation_results['warnings'].extend(pr_deps_analysis['warnings'])
        
        # Validate JSON integrity for samples
        json_validation = _validate_json_integrity(base_folder_path)
        if json_validation['errors']:
            validation_results['errors'].extend(json_validation['errors'])
            validation_results['valid'] = False
        
        # Generate quality assessment
        quality_assessment = _assess_data_quality(validation_results['analysis'])
        validation_results['analysis']['quality'] = quality_assessment
        
    except Exception as e:
        validation_results['errors'].append(f"Validation failed: {e}")
        validation_results['valid'] = False
    
    return validation_results

def _analyze_pull_requests_data(base_folder_path: str) -> Dict[str, Any]:
    """Analyze pull request data comprehensively"""
    analysis = {
        'stats': {},
        'errors': [],
        'warnings': [],
        'details': {}
    }
    
    pull_folder = f"{base_folder_path}/pull"
    all_data_file = f"{pull_folder}/all_data.json"
    
    # Check main pull requests file
    if os.path.exists(all_data_file):
        try:
            with open(all_data_file, 'r') as f:
                pull_data = json.load(f)
                
            analysis['stats']['total_pull_requests'] = len(pull_data)
            analysis['details']['has_main_data'] = True
            
            # Analyze PR states
            states = {}
            for pr in pull_data:
                state = pr.get('state', 'unknown')
                states[state] = states.get(state, 0) + 1
            analysis['details']['pr_states'] = states
            
        except json.JSONDecodeError as e:
            analysis['errors'].append(f"Invalid JSON in pull requests file: {e}")
            analysis['stats']['total_pull_requests'] = 0
            analysis['details']['has_main_data'] = False
        except Exception as e:
            analysis['errors'].append(f"Error reading pull requests: {e}")
            analysis['stats']['total_pull_requests'] = 0
            analysis['details']['has_main_data'] = False
    else:
        analysis['warnings'].append("No pull requests data file found")
        analysis['stats']['total_pull_requests'] = 0
        analysis['details']['has_main_data'] = False
    
    # Count individual PR folders
    pr_folders = []
    if os.path.exists(pull_folder):
        pr_folders = [item for item in os.listdir(pull_folder) if item.isdigit()]
    
    analysis['stats']['individual_pr_folders'] = len(pr_folders)
    analysis['details']['pr_folders'] = sorted([int(f) for f in pr_folders])
    
    return analysis

def _analyze_commits_data(base_folder_path: str) -> Dict[str, Any]:
    """Analyze commit data comprehensively"""
    analysis = {
        'stats': {},
        'errors': [],
        'warnings': [],
        'details': {}
    }
    
    commit_folder = f"{base_folder_path}/commit"
    all_data_file = f"{commit_folder}/all_data.json"
    
    # Check main commits file
    if os.path.exists(all_data_file):
        try:
            with open(all_data_file, 'r') as f:
                commit_data = json.load(f)
                
            analysis['stats']['total_repository_commits'] = len(commit_data)
            analysis['details']['has_main_commits'] = True
            
        except json.JSONDecodeError as e:
            analysis['errors'].append(f"Invalid JSON in commits file: {e}")
            analysis['stats']['total_repository_commits'] = 0
            analysis['details']['has_main_commits'] = False
        except Exception as e:
            analysis['errors'].append(f"Error reading commits: {e}")
            analysis['stats']['total_repository_commits'] = 0
            analysis['details']['has_main_commits'] = False
    else:
        analysis['warnings'].append("No repository commits data file found")
        analysis['stats']['total_repository_commits'] = 0
        analysis['details']['has_main_commits'] = False
    
    # Check individual commit details
    single_commits_folder = f"{commit_folder}/all"
    if os.path.exists(single_commits_folder):
        commit_files = [f for f in os.listdir(single_commits_folder) if f.endswith('.json')]
        analysis['stats']['individual_commit_details'] = len(commit_files)
        analysis['details']['has_individual_commits'] = len(commit_files) > 0
        
        # Calculate coverage percentage
        if analysis['stats']['total_repository_commits'] > 0:
            coverage = (len(commit_files) / analysis['stats']['total_repository_commits']) * 100
            analysis['stats']['commit_detail_coverage_percentage'] = round(coverage, 1)
        else:
            analysis['stats']['commit_detail_coverage_percentage'] = 0
    else:
        analysis['stats']['individual_commit_details'] = 0
        analysis['details']['has_individual_commits'] = False
        analysis['stats']['commit_detail_coverage_percentage'] = 0
    
    return analysis

def _analyze_pr_dependencies_data(base_folder_path: str) -> Dict[str, Any]:
    """Analyze PR dependency data (files, reviews, comments, commits)"""
    analysis = {
        'stats': {},
        'warnings': [],
        'details': {}
    }
    
    pull_folder = f"{base_folder_path}/pull"
    
    if not os.path.exists(pull_folder):
        return analysis
    
    # Get all PR folders
    pr_folders = [item for item in os.listdir(pull_folder) if item.isdigit()]
    
    if not pr_folders:
        return analysis
    
    dependency_types = ['files', 'reviews', 'comments', 'commits']
    
    for dep_type in dependency_types:
        stats = {
            f'prs_with_{dep_type}': 0,
            f'prs_without_{dep_type}': 0,
            f'total_{dep_type}_count': 0,
            f'{dep_type}_coverage_percentage': 0
        }
        
        for pr_folder in pr_folders:
            dep_file = f"{pull_folder}/{pr_folder}/{dep_type}/all_data.json"
            
            if os.path.exists(dep_file):
                try:
                    with open(dep_file, 'r') as f:
                        data = json.load(f)
                    
                    if len(data) > 0:
                        stats[f'prs_with_{dep_type}'] += 1
                        stats[f'total_{dep_type}_count'] += len(data)
                    else:
                        stats[f'prs_without_{dep_type}'] += 1
                        
                except (json.JSONDecodeError, Exception):
                    stats[f'prs_without_{dep_type}'] += 1
            else:
                stats[f'prs_without_{dep_type}'] += 1
        
        # Calculate coverage percentage
        total_prs = len(pr_folders)
        if total_prs > 0:
            coverage = (stats[f'prs_with_{dep_type}'] / total_prs) * 100
            stats[f'{dep_type}_coverage_percentage'] = round(coverage, 1)
        
        # Add to main stats
        analysis['stats'].update(stats)
        
        # Add warnings for low coverage
        if stats[f'{dep_type}_coverage_percentage'] < 5:
            analysis['warnings'].append(
                f"Very low {dep_type} coverage ({stats[f'{dep_type}_coverage_percentage']:.1f}%) - "
                f"may impact reviewer recommendation quality"
            )
    
    return analysis

def _validate_json_integrity(base_folder_path: str) -> Dict[str, Any]:
    """Validate JSON integrity for a sample of files"""
    validation = {
        'errors': [],
        'files_checked': 0
    }
    
    # Check key files
    key_files = [
        f"{base_folder_path}/pull/all_data.json",
        f"{base_folder_path}/commit/all_data.json"
    ]
    
    for file_path in key_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    json.load(f)
                validation['files_checked'] += 1
            except json.JSONDecodeError as e:
                validation['errors'].append(f"Invalid JSON in {file_path}: {e}")
    
    # Check sample of individual files
    individual_commit_folder = f"{base_folder_path}/commit/all"
    if os.path.exists(individual_commit_folder):
        commit_files = [f for f in os.listdir(individual_commit_folder) if f.endswith('.json')]
        sample_size = min(10, len(commit_files))
        
        for commit_file in commit_files[:sample_size]:
            file_path = f"{individual_commit_folder}/{commit_file}"
            try:
                with open(file_path, 'r') as f:
                    json.load(f)
                validation['files_checked'] += 1
            except json.JSONDecodeError as e:
                validation['errors'].append(f"Invalid JSON in {file_path}: {e}")
    
    return validation

def _assess_data_quality(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Assess overall data quality for reviewer recommendation systems"""
    assessment = {
        'overall_score': 0,
        'suitability_for_reviewer_recommendation': 'unknown',
        'strengths': [],
        'weaknesses': [],
        'recommendations': []
    }
    
    try:
        # Get key metrics
        total_prs = analysis.get('pull_requests', {}).get('stats', {}).get('total_pull_requests', 0)
        review_coverage = analysis.get('pr_dependencies', {}).get('stats', {}).get('reviews_coverage_percentage', 0)
        total_reviews = analysis.get('pr_dependencies', {}).get('stats', {}).get('total_reviews_count', 0)
        commit_coverage = analysis.get('commits', {}).get('stats', {}).get('commit_detail_coverage_percentage', 0)
        
        # Score calculation (0-100)
        score = 0
        
        # PR data availability (30 points)
        if total_prs > 0:
            score += 30
            assessment['strengths'].append(f"Has {total_prs} pull requests")
        else:
            assessment['weaknesses'].append("No pull request data found")
        
        # Review coverage (40 points)
        if review_coverage >= 30:
            score += 40
            assessment['strengths'].append(f"Excellent review coverage ({review_coverage:.1f}%)")
        elif review_coverage >= 15:
            score += 25
            assessment['strengths'].append(f"Good review coverage ({review_coverage:.1f}%)")
        elif review_coverage >= 5:
            score += 10
            assessment['weaknesses'].append(f"Low review coverage ({review_coverage:.1f}%)")
        else:
            assessment['weaknesses'].append(f"Very low review coverage ({review_coverage:.1f}%)")
        
        # Commit detail coverage (20 points)
        if commit_coverage >= 80:
            score += 20
            assessment['strengths'].append(f"Complete commit details ({commit_coverage:.1f}%)")
        elif commit_coverage >= 50:
            score += 15
        elif commit_coverage >= 20:
            score += 10
            assessment['weaknesses'].append(f"Incomplete commit details ({commit_coverage:.1f}%)")
        else:
            assessment['weaknesses'].append(f"Missing most commit details ({commit_coverage:.1f}%)")
        
        # Total review count (10 points)
        if total_reviews >= 100:
            score += 10
            assessment['strengths'].append(f"Substantial review data ({total_reviews} reviews)")
        elif total_reviews >= 50:
            score += 7
        elif total_reviews >= 20:
            score += 5
        else:
            assessment['weaknesses'].append(f"Limited review data ({total_reviews} reviews)")
        
        assessment['overall_score'] = score
        
        # Determine suitability
        if score >= 70:
            assessment['suitability_for_reviewer_recommendation'] = 'excellent'
            assessment['recommendations'].append("Data is well-suited for reviewer recommendation systems")
        elif score >= 50:
            assessment['suitability_for_reviewer_recommendation'] = 'good'
            assessment['recommendations'].append("Data can be used for reviewer recommendation with good results")
        elif score >= 30:
            assessment['suitability_for_reviewer_recommendation'] = 'limited'
            assessment['recommendations'].append("Consider supplementing with additional repositories")
        else:
            assessment['suitability_for_reviewer_recommendation'] = 'poor'
            assessment['recommendations'].append("Recommend finding repositories with more review activity")
        
        # Specific recommendations
        if review_coverage < 20:
            assessment['recommendations'].append(
                "Low review coverage may require algorithm adjustments to focus on file-based features"
            )
        
        if total_reviews < 50:
            assessment['recommendations'].append(
                "Consider combining data from multiple similar repositories"
            )
            
    except Exception as e:
        assessment['error'] = str(e)
    
    return assessment