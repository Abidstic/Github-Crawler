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
    """Validate integrity of crawled data"""
    validation_results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }
    
    try:
        # Check pull requests
        pull_folder = f"{base_folder_path}/pull"
        pull_files = get_all_json_files_in_folder(pull_folder)
        validation_results['stats']['pull_files'] = len(pull_files)
        
        # Check commits
        commit_folder = f"{base_folder_path}/commit"
        commit_files = get_all_json_files_in_folder(commit_folder)
        validation_results['stats']['commit_files'] = len(commit_files)
        
        # Check single commits
        single_commit_folder = f"{base_folder_path}/commit/all"
        single_commit_files = get_all_json_files_in_folder(single_commit_folder)
        validation_results['stats']['single_commit_files'] = len(single_commit_files)
        
        # Validate JSON integrity
        for folder in [pull_folder, commit_folder, single_commit_folder]:
            if os.path.exists(folder):
                for json_file in get_all_json_files_in_folder(folder):
                    file_path = f"{folder}/{json_file}"
                    try:
                        with open(file_path, 'r') as f:
                            json.load(f)
                    except json.JSONDecodeError as e:
                        validation_results['errors'].append(f"Invalid JSON in {file_path}: {e}")
                        validation_results['valid'] = False
        
        # Check for missing dependencies
        pull_numbers = get_all_pull_numbers(pull_folder)
        for pr_number in pull_numbers[:10]:  # Check first 10 PRs
            for dep in ['files', 'reviews', 'commits', 'comments']:
                dep_folder = f"{pull_folder}/{pr_number}/{dep}"
                if not os.path.exists(dep_folder):
                    validation_results['warnings'].append(f"Missing {dep} for PR {pr_number}")
        
    except Exception as e:
        validation_results['errors'].append(f"Validation failed: {e}")
        validation_results['valid'] = False
    
    return validation_results