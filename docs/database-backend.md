# Database Backend Implementation for Extraction Jobs and Schedules

## Overview
This implementation adds a PostgreSQL database backend to store and track extraction jobs and trigger schedules. The solution follows the existing convention of prepending table names with `csp_scanner_` and uses the same database configuration variables already available in the config.

## Database Schema

### Tables Created

#### 1. `csp_scanner_extraction_jobs`
Stores information about extraction jobs (both ad-hoc and scheduled).

**Columns:**
- `id` (String/UUID, Primary Key) - Unique job identifier
- `status` (String) - Job status: pending, running, completed, failed
- `started_at` (DateTime with timezone, indexed) - Job start timestamp
- `completed_at` (DateTime with timezone, nullable) - Job completion timestamp
- `services` (JSON) - List of services to extract
- `regions` (JSON, nullable) - List of regions to extract from
- `filters` (JSON, nullable) - Filter parameters applied
- `batch_size` (Integer) - Batch size for processing
- `total_artifacts` (Integer) - Total number of artifacts processed
- `successful_artifacts` (Integer) - Number of successfully sent artifacts
- `failed_artifacts` (Integer) - Number of failed artifacts
- `errors` (JSON, nullable) - List of error messages
- `created_at` (DateTime with timezone) - Record creation timestamp
- `updated_at` (DateTime with timezone) - Last update timestamp

#### 2. `csp_scanner_schedules`
Stores information about extraction schedules.

**Columns:**
- `id` (String, Primary Key) - Unique schedule identifier (schedule name)
- `name` (String, indexed) - Human-readable schedule name
- `cron_expression` (String) - Cron expression for scheduling
- `services` (JSON, nullable) - List of services to extract
- `regions` (JSON, nullable) - List of regions to extract from
- `filters` (JSON, nullable) - Filter parameters to apply
- `batch_size` (Integer) - Batch size for processing
- `is_active` (Boolean, indexed) - Whether schedule is active
- `paused` (Boolean) - Whether schedule is paused
- `last_run_at` (DateTime with timezone, nullable) - Last execution timestamp
- `next_run_at` (DateTime with timezone, nullable) - Next scheduled execution
- `description` (String, nullable) - Optional description
- `created_at` (DateTime with timezone) - Record creation timestamp
- `updated_at` (DateTime with timezone) - Last update timestamp

#### 3. `csp_scanner_config`
Stores the application's configuration settings.

**Columns:**
- `id` (String, Primary Key) - Unique identifier for the configuration entry.
- `config` (JSON) - The configuration data.
- `created_at` (DateTime with timezone) - Timestamp of when the configuration was created.
- `updated_at` (DateTime with timezone) - Timestamp of when the configuration was last updated.

#### 4. `csp_scanner_config_versions`
Stores versions of the application's configuration settings.

**Columns:**
- `id` (Integer, Primary Key) - Unique identifier for the configuration version.
- `version` (Integer, indexed) - The version number.
- `config` (JSON) - The configuration data for this version.
- `created_at` (DateTime with timezone) - Timestamp of when this version was created.

## Implementation Details

### 1. Database Models (`app/models/database.py`)
- Added `ExtractionJob`, `Schedule`, `ConfigEntry`, and `ConfigVersion` SQLAlchemy models
- Added CRUD methods to `DatabaseManager` class:
  - **Job methods:** `create_job()`, `get_job()`, `update_job()`, `list_jobs()`, `delete_old_jobs()`
  - **Schedule methods:** `create_schedule()`, `get_schedule()`, `update_schedule()`, `list_schedules()`, `delete_schedule()`
  - **Config methods:** `create_config()`, `get_config()`, `update_config()`, `create_config_version()`, `get_config_version()`

### 2. Orchestrator Updates (`app/services/orchestrator.py`)
- Added database integration to `ExtractionOrchestrator`
- Jobs are now persisted to database when created
- Job status is updated in database upon completion/failure
- `get_job_status()` checks database if job not found in memory
- `list_jobs()` retrieves jobs from database when enabled
- Graceful fallback to in-memory storage if database is unavailable

### 3. Schedule API Updates (`app/api/routes/schedules.py`)
- Create schedule endpoint now saves to database
- List schedules endpoint enriched with database metadata
- Delete, pause, and resume operations update database
- All database operations have error handling with logging

### 4. Application Startup (`app/main.py`)
- Database tables are automatically created on startup if database is enabled
- Schedules are restored from database on application startup
- Only active, non-paused schedules are restored to APScheduler

## Configuration

The implementation uses existing database configuration variables:

```yaml
# Environment variables (or config file)
CSP_SCANNER_DATABASE_ENABLED: "true"
CSP_SCANNER_DATABASE_HOST: "localhost"
CSP_SCANNER_DATABASE_PORT: "5432"
CSP_SCANNER_DATABASE_NAME: "csp_scanner"
CSP_SCANNER_DATABASE_USER: "your_user"
CSP_SCANNER_DATABASE_PASSWORD: "your_password"
```

Or via Settings class properties:
- `database_enabled`
- `database_host`
- `database_port`
- `database_name`
- `database_user`
- `database_password`

## Features

### Job Tracking
1. **Persistent Storage**: All jobs are saved to database with full metadata
2. **Status Updates**: Job status is updated in real-time as execution progresses
3. **Historical Data**: Jobs remain in database for auditing and reporting
4. **Query Support**: Filter jobs by status, limit results
5. **Cleanup**: `delete_old_jobs()` method for removing old job records

### Schedule Management
1. **Persistent Schedules**: Schedules survive application restarts
2. **State Management**: Track active/inactive and paused states
3. **Execution History**: Track last run and next run times
4. **Rich Metadata**: Store all schedule parameters (services, regions, filters, etc.)
5. **Restore on Startup**: Automatically restore schedules when application starts

### Graceful Degradation
- Database operations are optional and don't block functionality
- If database is unavailable, application falls back to in-memory storage
- All database errors are logged but don't cause API failures
- Works seamlessly with existing non-database deployments

## Usage Examples

### Enable Database
```bash
# Set environment variables
export CSP_SCANNER_DATABASE_ENABLED=true
export CSP_SCANNER_DATABASE_HOST=localhost
export CSP_SCANNER_DATABASE_PORT=5432
export CSP_SCANNER_DATABASE_NAME=csp_scanner
export CSP_SCANNER_DATABASE_USER=postgres
export CSP_SCANNER_DATABASE_PASSWORD=your_password

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Query Jobs from Database
```python
from app.models.database import get_db_manager

db_manager = get_db_manager()

# Get all jobs
jobs = db_manager.list_jobs(limit=50)

# Get jobs by status
running_jobs = db_manager.list_jobs(status="running")

# Get specific job
job = db_manager.get_job(job_id="some-uuid")

# Clean up old jobs (older than 30 days)
deleted_count = db_manager.delete_old_jobs(days=30)
```

### Query Schedules from Database
```python
from app.models.database import get_db_manager

db_manager = get_db_manager()

# Get all schedules
schedules = db_manager.list_schedules()

# Get active schedules only
active_schedules = db_manager.list_schedules(active_only=True)

# Get specific schedule
schedule = db_manager.get_schedule(schedule_id="daily-extract")
```

## Migration Path

For existing deployments:

1. **Without Database** (default):
   - No changes required
   - Application continues to work with in-memory storage

2. **Enable Database**:
   - Set `CSP_SCANNER_DATABASE_ENABLED=true`
   - Configure database connection parameters
   - Restart application
   - Tables are automatically created
   - Existing schedules will need to be recreated (they'll be saved to DB)

3. **Future Migrations**:
   - Consider using Alembic for schema migrations
   - Existing tables follow the `csp_scanner_` naming convention

## Testing

The database-related tests are designed to be self-contained and not interfere with each other. This is achieved by using a temporary, file-based SQLite database for each test function. This ensures that the database logic is tested in isolation.

To test database functionality:
```bash
# Run all tests, including database tests
pytest

# Run specific database tests
pytest tests/test_database_manager.py -v
```

## Benefits

1. **Persistence**: Jobs and schedules survive application restarts
2. **Auditing**: Historical record of all extraction jobs
3. **Monitoring**: Query database for job statistics and trends
4. **Scalability**: Multiple instances can share job history
5. **Reporting**: Build dashboards and reports from job data
6. **Recovery**: Restore schedules after crashes or deployments
7. **Compliance**: Maintain audit trail of all extraction activities

## Future Enhancements

Potential improvements:
1. Add database indexes for common queries (status, timestamps)
2. Implement job cleanup cron task
3. Add metrics and statistics endpoints
4. Support for job cancellation via database
5. Schedule versioning and history
6. Job dependencies and workflows
7. Integration with external monitoring tools
