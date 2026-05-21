# Job Postings Tracker

An interactive visualization page for tracking daily job postings across major Chinese job platforms.

## Features

- **Interactive Line Chart**: Visualize trends over time for each platform
- **Statistics Cards**: Display latest job posting counts for each platform
- **Data Table**: Show latest data with daily changes and percentages
- **Auto-refresh**: Refresh button to update data
- **Responsive Design**: Works on desktop and mobile devices

## Platforms Tracked

- 58同城 (58.com)
- 智联招聘 (Zhaopin)
- 前程无忧 (51job/qcwy)
- BOSS直聘 (Boss Zhipin)
- 猎聘 (Liepin)

## How to Update Data

### Manual Update

Use the Python script to manually add new data:

```bash
# From the project root directory
python scripts/update_job_data.py --manual
```

Then enter data in JSON format:
```json
{"58": {"2025-01-25": 30400}, "zl": {"2025-01-25": 31600}}
```

### Update from Command Line

Pass JSON data directly as an argument:

```bash
python scripts/update_job_data.py '{"58": {"2025-01-25": 30400}, "zl": {"2025-01-25": 31600}}'
```

### Email Integration (To Be Implemented)

The script has placeholder code for email integration. To implement:

1. Configure email credentials in the script
2. Set up email parsing logic
3. Schedule the script to run periodically (e.g., using cron)

Example cron job (daily at 9 AM):
```bash
0 9 * * * cd /path/to/academic_website && python scripts/update_job_data.py --email
```

## Data Format

Data is stored in `job-data.json` with the following structure:

```json
{
    "platform_code": {
        "YYYY-MM-DD": count,
        ...
    },
    ...
}
```

## Files

- `/job-tracker/index.html` - Main visualization page
- `/job-tracker/data/job-data.json` - Job posting data
- `/scripts/update_job_data.py` - Python script for updating data

## Accessing the Page

Once deployed, access the tracker at:
```
https://leoyang.org/job-tracker/
```

## Notes

- Data older than 30 days is automatically cleaned up
- The page uses Chart.js for visualizations
- Styling matches the main academic website theme
- Job posting counts are in the hundreds of thousands, representing daily listings across China

## Contact for Academic Cooperation

Dr. Leo Y. Yang  
Hong Kong Baptist University  
Email: leoyang@hkbu.edu.hk  
Phone: +1 (858) 405-2327  

For research purposes, raw data can be provided upon request. 