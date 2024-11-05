# Comprehensive Job Monitor

A powerful job monitoring system that tracks new job postings across GitHub, LinkedIn, and JobRight.ai. Get instant notifications for positions matching your criteria, with support for custom filters and detailed job information.

## Features

- **Multi-Platform Monitoring**
  - GitHub job listings (e.g., SimplifyJobs/New-Grad-Positions)
  - LinkedIn job postings (with custom search parameters)
  - JobRight.ai integration (with API support)

- **Real-Time Notifications**
  - Desktop notifications for new job postings
  - Customizable notification format
  - Detailed job information including salary ranges (when available)

- **Advanced Features**
  - Secure credential storage
  - Configurable search parameters
  - Concurrent monitoring of multiple sources
  - Detailed logging system
  - Automatic error recovery

## Prerequisites

- Python 3.7+
- Chrome/Chromium browser (for LinkedIn integration)
- JobRight.ai API key (for JobRight.ai integration)

## Installation

1. Clone the repository:
```bash
git clone [your-repo-url]
cd job-monitor
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install ChromeDriver (for LinkedIn integration):
   - Download from: https://sites.google.com/chromium.org/driver/
   - Add to your system PATH

## Configuration

Create a `job_monitor_config.json` file (or let the script create a default one):

```json
{
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
      "remote": true,
      "posted_within_days": 30
    }
  }
}
```

### Configuration Options

- `check_interval`: Time between checks in seconds (default: 300)
- `github`: GitHub repository settings
  - `owner`: Repository owner
  - `repo`: Repository name
  - `branch`: Branch to monitor
- `linkedin`: LinkedIn search parameters
  - `keywords`: Job title or keywords
  - `location`: Job location
  - `f_E`: Experience level (2 = Entry level)
  - `sortBy`: Sort order (DD = Most recent)
- `jobright`: JobRight.ai search parameters
  - `keywords`: List of job title keywords
  - `locations`: List of locations
  - `experience_levels`: List of experience levels
  - `job_types`: List of job types
  - `remote`: Boolean for remote positions
  - `posted_within_days`: Job posting age filter

## Usage

1. Regular usage:
```bash
python github_job_monitor.py
```

2. With custom configuration:
```bash
python github_job_monitor.py --config your_config.json
```

3. Run in background (Windows):
```bash
start /B pythonw github_job_monitor.py
```

### First Run Setup

On first run, the script will:
1. Prompt for LinkedIn credentials (if LinkedIn monitoring is enabled)
2. Request JobRight.ai API key (if JobRight.ai monitoring is enabled)
3. Store credentials securely using keyring
4. Create default configuration if none exists

## Logs and Monitoring

- Logs are stored in `job_monitor.log`
- Process ID is stored in `job_monitor.pid`
- Desktop notifications appear for new job listings
- Detailed job information is logged for each new posting

## Structure

```
job-monitor/
├── github_job_monitor.py    # Main script
├── requirements.txt         # Python dependencies
├── job_monitor_config.json  # Configuration file
├── job_monitor.log         # Log file
├── job_monitor.pid         # Process ID file
└── run_job_monitor.bat     # Windows startup script
```

## Development

### Adding New Job Sources

To add a new job source:

1. Create a new manager class (similar to `LinkedInManager` or `JobRightManager`)
2. Implement the required methods:
   - Authentication/setup
   - Job listing retrieval
   - Cleanup
3. Add the new source to the `JobMonitor` class
4. Update the configuration structure

### Best Practices

- Use type hints for better code maintainability
- Add proper error handling and logging
- Implement graceful shutdown
- Follow the existing pattern for credential management

## Troubleshooting

### Common Issues

1. LinkedIn Authentication Fails
   - Check your credentials
   - Verify ChromeDriver version matches your Chrome version
   - Check if LinkedIn is blocking automated access

2. JobRight.ai API Issues
   - Verify API key is correct
   - Check API rate limits
   - Ensure search parameters are valid

3. Notification Issues
   - Check system notification settings
   - Verify plyer package is properly installed
   - Check notification permissions

### Error Logs

Check `job_monitor.log` for detailed error information and debugging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments

- SimplifyJobs for maintaining the New-Grad-Positions repository
- JobRight.ai for their API access
- All contributors to this project

## Security

- Credentials are stored securely using keyring
- API keys and passwords are never logged
- HTTPS is used for all API communications
