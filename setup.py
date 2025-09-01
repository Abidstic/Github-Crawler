#!/usr/bin/env python3
"""
Setup script for GitHub Unified Crawler
Helps validate environment and setup
"""

import os
import sys
import subprocess
import pkg_resources
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_dependencies():
    """Check if all dependencies are installed"""
    print("\n📦 Checking dependencies...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read().strip().split('\n')
        
        missing_packages = []
        
        for requirement in requirements:
            if not requirement.strip() or requirement.startswith('#'):
                continue
                
            package_name = requirement.split('==')[0].strip()
            
            try:
                pkg_resources.get_distribution(package_name)
                print(f"✅ {package_name}")
            except pkg_resources.DistributionNotFound:
                missing_packages.append(requirement)
                print(f"❌ {package_name} (missing)")
        
        if missing_packages:
            print(f"\n⚠️  Missing packages found. Install with:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
        
        print("✅ All dependencies satisfied")
        return True
        
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def check_github_token():
    """Check if GitHub token is configured"""
    print("\n🔑 Checking GitHub token...")
    
    token = os.environ.get('GH_TOKEN')
    
    if not token:
        print("❌ GitHub token not found")
        print("\n🛠️  To set up GitHub token:")
        print("1. Go to GitHub Settings → Developer settings → Personal access tokens")
        print("2. Generate new token (classic) with 'repo' permissions")
        print("3. Set environment variable:")
        print("   export GH_TOKEN='your_token_here'")
        print("   # or add to your .bashrc/.zshrc for permanent setup")
        return False
    
    # Validate token format
    if not token.startswith(('ghp_', 'github_pat_')):
        print("⚠️  Token format looks unusual (should start with 'ghp_' or 'github_pat_')")
    
    print(f"✅ GitHub token found: {token[:8]}...")
    return True

def create_folder_structure():
    """Create basic folder structure"""
    print("\n📁 Creating folder structure...")
    
    folders = [
        'crawled-data',
        'logs'
    ]
    
    for folder in folders:
        Path(folder).mkdir(exist_ok=True)
        print(f"✅ {folder}/")
    
    return True

def test_github_api():
    """Test GitHub API connectivity"""
    print("\n🌐 Testing GitHub API connectivity...")
    
    token = os.environ.get('GH_TOKEN')
    if not token:
        print("❌ Cannot test API without token")
        return False
    
    try:
        # Try importing required modules
        try:
            import aiohttp
        except ImportError:
            print("❌ aiohttp not installed. Installing...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'aiohttp'], check=True)
            import aiohttp
        
        import asyncio
        
        async def test_api():
            headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {token}',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            async with aiohttp.ClientSession() as session:
                # Test with a simple API call
                async with session.get('https://api.github.com/user', headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        print(f"✅ API connection successful")
                        print(f"   Authenticated as: {user_data.get('login', 'Unknown')}")
                        
                        # Check rate limit
                        remaining = response.headers.get('X-RateLimit-Remaining', 'Unknown')
                        limit = response.headers.get('X-RateLimit-Limit', 'Unknown')
                        print(f"   Rate limit: {remaining}/{limit}")
                        return True
                    else:
                        print(f"❌ API test failed: {response.status}")
                        return False
        
        return asyncio.run(test_api())
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def install_dependencies():
    """Install dependencies using pip"""
    print("\n📦 Installing dependencies...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def main():
    """Main setup function"""
    print("🎯 GitHub Unified Crawler - Setup Validation")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        create_folder_structure(),
    ]
    
    # Check if dependencies need to be installed
    if not check_dependencies():
        install_choice = input("\n❓ Install missing dependencies now? [Y/n]: ").strip().lower()
        if install_choice in ['', 'y', 'yes']:
            if install_dependencies():
                checks.append(check_dependencies())
            else:
                checks.append(False)
        else:
            checks.append(False)
    else:
        checks.append(True)
    
    checks.extend([
        check_github_token(),
        test_github_api(),
    ])
    
    print("\n" + "=" * 60)
    
    if all(checks):
        print("🎉 Setup validation passed! You're ready to crawl.")
        print("\n🚀 Example usage:")
        print("   python main.py --owner facebook --repo react")
        print("   python main.py --examples  # Show more examples")
    else:
        print("⚠️  Setup validation failed. Please fix the issues above.")
        print("\n💡 Common solutions:")
        print("   • Install Python 3.8+")
        print("   • Run: pip install -r requirements.txt")
        print("   • Set GitHub token: export GH_TOKEN='your_token'")
    
    print("=" * 60)

if __name__ == "__main__":
    main()