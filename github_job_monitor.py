import requests
import time
import re
from datetime import datetime
import signal
import sys
import argparse
from plyer import notification
import logging
import os
from typing import Set, Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import quote, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
from pathlib import Path
import keyring
import asyncio
import aiohttp
from bs4 import BeautifulSoup

@dataclass
class JobListing:
    company: str
    role: str
    location: str
    link: str
    date: str
    source: str  # 'github', 'linkedin', or 'jobright'
    salary_range: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    
    def __hash__(self):
        return hash((self.company, self.role, self.location, self.link, self.source))

class JobRightManager:
    def __init__(self, api_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.session = aiohttp.ClientSession()
        self.api_key = api_key or self.load_api_key()
        self.base_url = "https://api.jobright.ai/v1"
        
    def load_api_key(self) -> str:
        """Load JobRight.ai API key from keyring or prompt user."""
        api_key = keyring.get_password("jobright", "api_key")
        
        if not api_key:
            api_key = input("Enter JobRight.ai API key: ")
            keyring.set_password("jobright", "api_key", api_key)
            
        return api_key
        
    async def authenticate(self) -> bool:
        """Verify API key is valid."""
        try:
            async with self.session.get(
                f"{self.base_url}/auth/verify",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Failed to authenticate with JobRight.ai: {str(e)}")
            return False

    async def get_job_listings(self, search_params: Dict[str, Any]) -> List[JobListing]:
        """
        Fetch job listings from JobRight.ai based on search parameters.
        
        Args:
            search_params: Dictionary containing search parameters like:
                - keywords: List of job title keywords
                - locations: List of locations
                - experience_levels: List of experience levels
                - job_types: List of job types (full-time, part-time, etc.)
                - remote: Boolean indicating remote positions
                - posted_within_days: Integer for job posting age filter
        """
        listings = []
        try:
            # Construct search query
            query = {
                "query": {
                    "keywords": search_params.get("keywords", []),
                    "locations": search_params.get("locations", []),
                    "experience_levels": search_params.get("experience_levels", []),
                    "job_types": search_params.get("job_types", []),
                    "remote": search_params.get("remote", None),
                    "posted_within_days": search_params.get("posted_within_days", 30)
                },
                "page": 1,
                "per_page": 100
            }
            
            async with self.session.post(
                f"{self.base_url}/jobs/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=query
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for job in data.get("jobs", []):
                        listings.append(JobListing(
                            company=job.get("company_name", ""),
                            role=job.get("title", ""),
                            location=job.get("location", ""),
                            link=job.get("application_url", ""),
                            date=job.get("posted_at", ""),
                            source="jobright",
                            salary_range=job.get("salary_range", ""),
                            description=job.get("description", ""),
                            requirements=job.get("requirements", [])
                        ))
                else:
                    self.logger.error(f"Failed to fetch JobRight.ai listings: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"Error fetching JobRight.ai jobs: {str(e)}")
            
        return listings

    async def cleanup(self):
        """Clean up aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

class JobMonitor:
    def __init__(self, config: dict):
        self.config = config
        self.setup_logging()
        self.killer = GracefulKiller()
        self.session = requests.Session()
        self.linkedin = LinkedInManager()
        self.jobright = JobRightManager()
        
    # ... (previous methods remain the same) ...

    async def get_jobright_listings(self) -> List[JobListing]:
        """Fetch job listings from JobRight.ai."""
        return await self.jobright.get_job_listings(self.config['jobright']['search_params'])

    def notify(self, listing: JobListing):
        """Send desktop notification for new job listing with enhanced details."""
        title = f"New Job ({listing.source.title()}): {self.truncate_string(listing.company)}"
        
        # Customize message based on source and available information
        if listing.source == "jobright" and listing.salary_range:
            message = (
                f"{self.truncate_string(listing.role)} in {self.truncate_string(listing.location)}\n"
                f"Salary: {listing.salary_range}"
            )
        else:
            message = f"{self.truncate_string(listing.role)} in {self.truncate_string(listing.location)}"
        
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Job Monitor",
                timeout=10
            )
            
            # Log detailed information
            log_message = (
                f"New {listing.source} listing:\n"
                f"Company: {listing.company}\n"
                f"Role: {listing.role}\n"
                f"Location: {listing.location}\n"
                f"Link: {listing.link}\n"
                f"Date: {listing.date}"
            )
            
            if listing.salary_range:
                log_message += f"\nSalary Range: {listing.salary_range}"
                
            if listing.requirements:
                log_message += f"\nKey Requirements: {', '.join(listing.requirements[:3])}..."
                
            self.logger.info(log_message)
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    async def run(self):
        """Main monitoring loop with async support."""
        self.logger.info("Starting job monitor")
        
        if not self.linkedin.login():
            self.logger.error("Failed to login to LinkedIn. Only monitoring GitHub and JobRight.ai.")
            
        if not await self.jobright.authenticate():
            self.logger.error("Failed to authenticate with JobRight.ai. Only monitoring GitHub and LinkedIn.")
        
        last_listings: Set[JobListing] = set()
        first_run = True
        
        try:
            while not self.killer.kill_now:
                try:
                    # Fetch listings from all sources
                    current_listings = set()
                    current_listings.update(self.get_github_listings())
                    current_listings.update(self.get_linkedin_listings())
                    current_listings.update(await self.get_jobright_listings())

                    if first_run:
                        self.logger.info(f"Initially found {len(current_listings)} open listings")
                        first_run = False
                    else:
                        new_listings = current_listings - last_listings
                        for listing in new_listings:
                            self.notify(listing)

                    last_listings = current_listings
                    await asyncio.sleep(self.config['check_interval'])

                except Exception as e:
                    self.logger.error(f"An error occurred in the main loop: {str(e)}", exc_info=True)
                    await asyncio.sleep(self.config['check_interval'])

        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources on shutdown."""
        self.logger.info("Shutting down job monitor")
        self.session.close()
        self.linkedin.cleanup()
        await self.jobright.cleanup()
        if os.path.exists('job_monitor.pid'):
            os.remove('job_monitor.pid')

async def main():
    parser = argparse.ArgumentParser(description="Monitor GitHub, LinkedIn, and JobRight.ai for job listings")
    parser.add_argument("--config", type=str, default="job_monitor_config.json",
                      help="Path to configuration file")
    args = parser.parse_args()

    # Load configuration
    if not os.path.exists(args.config):
        default_config = {
            "check_interval": 300,
            "github": {
                "owner": "SimplifyJobs",
                "repo": "New-Grad-Positions",
                "branch": "dev"
            },
            "linkedin": {
                "search_params": {
                    "keywords": "software engineer new grad",
                    "location": "United States",
                    "f_E": "2",
                    "sortBy": "DD"
                }
            },
            "jobright": {
                "search_params": {
                    "keywords": ["software engineer", "developer"],
                    "locations": ["United States"],
                    "experience_levels": ["entry"],
                    "job_types": ["full-time"],
                    "remote": True,
                    "posted_within_days": 30
                }
            }
        }
        with open(args.config, 'w') as f:
            json.dump(default_config, f, indent=2)
            
    with open(args.config, 'r') as f:
        config = json.load(f)

    # Write PID to file
    with open('job_monitor.pid', 'w') as f:
        f.write(str(os.getpid()))

    monitor = JobMonitor(config)
    await monitor.run()

if __name__ == "__main__":
    asyncio.run(main())