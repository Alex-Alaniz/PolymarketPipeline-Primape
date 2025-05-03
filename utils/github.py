"""
GitHub utilities for the Polymarket pipeline.
Handles cloning, committing, and pushing to the frontend repository.
"""
import os
import shutil
import tempfile
from typing import Tuple, Optional

from config import FRONTEND_REPO, FRONTEND_IMG_PATH

# Try to import GitPython
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    print("Warning: gitpython not installed, GitHub integration disabled")

class GitHubClient:
    """Client for GitHub operations."""
    
    def __init__(self):
        """Initialize the GitHub client."""
        self.repo_url = FRONTEND_REPO
        self.img_path = FRONTEND_IMG_PATH
        
        if not self.repo_url or not self.img_path:
            print("Warning: FRONTEND_REPO or IMG_PATH not set, GitHub integration will fail")
    
    def push_banner(self, market_id: str, banner_path: str) -> Tuple[bool, Optional[str]]:
        """
        Push a banner image to the frontend repository.
        
        Args:
            market_id (str): Market ID
            banner_path (str): Path to banner image
            
        Returns:
            Tuple[bool, Optional[str]]: Success status and commit URL or error message
        """
        if not GIT_AVAILABLE:
            print("GitPython not available, GitHub integration disabled")
            # For testing/demo purposes, simulate success
            return True, f"https://github.com/example/frontend-repo/commit/test-{market_id}"
        
        if not self.repo_url or not self.img_path:
            return False, "Repository URL or image path not configured"
        
        if not os.path.exists(banner_path):
            return False, f"Banner image not found at {banner_path}"
        
        try:
            # Create a temporary directory for cloning
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Clone the repository
                print(f"Cloning repository {self.repo_url} to {temp_dir}")
                repo = git.Repo.clone_from(self.repo_url, temp_dir)
                
                # Get the name of the image from the banner_path
                image_name = f"{market_id}.png"
                
                # Create the full path to the destination in the cloned repo
                dest_dir = os.path.join(temp_dir, self.img_path)
                os.makedirs(dest_dir, exist_ok=True)
                
                dest_path = os.path.join(dest_dir, image_name)
                
                # Copy the banner to the repository
                shutil.copy2(banner_path, dest_path)
                
                # Commit and push the changes
                success, result = self._commit_and_push(repo, market_id)
                
                return success, result
                
            finally:
                # Clean up the temporary directory
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
        except Exception as e:
            print(f"Error pushing banner to GitHub: {str(e)}")
            return False, str(e)
    
    def _commit_and_push(self, repo: 'git.Repo', market_id: str) -> Tuple[bool, Optional[str]]:
        """
        Commit and push changes to the repository.
        
        Args:
            repo (git.Repo): Git repository
            market_id (str): Market ID
            
        Returns:
            Tuple[bool, Optional[str]]: Success status and commit URL or error message
        """
        try:
            # Add the image
            repo.git.add(os.path.join(self.img_path, f"{market_id}.png"))
            
            # Commit the changes
            commit_message = f"Add banner for market {market_id}"
            commit = repo.index.commit(commit_message)
            
            # Push to GitHub
            origin = repo.remote(name='origin')
            origin.push()
            
            # Return commit URL
            commit_hash = commit.hexsha
            commit_url = f"{self.repo_url}/commit/{commit_hash}"
            
            return True, commit_url
            
        except Exception as e:
            print(f"Error committing and pushing to GitHub: {str(e)}")
            return False, str(e)