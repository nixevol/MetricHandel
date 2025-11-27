# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MetricHandel is a web application for network metric monitoring and data management. It provides a FastAPI backend with SQLite database integration and a frontend interface built with Tailwind CSS and JavaScript.

**Key purpose**: Ingest, process, and visualize telecom network metrics (4G/5G cell performance data, burst load monitoring, etc.)

## Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment: `.venv` (already configured)

### Setup & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

The application will:
- Start FastAPI server on `http://127.0.0.1:8000`
- Automatically open the web interface in your browser
- Server files from `./static/` directory

## Architecture

### Backend Structure

**Main components:**

- **main.py**: FastAPI application with all API endpoints
  - Server lifecycle management (auto-launch browser)
  - No-cache middleware for static files (development environment)
  - 18+ REST endpoints organized into functional groups

- **database.py**: DatabaseManager class
  - SQLite connection management
  - Table/column queries, data pagination with search
  - Import/export/clear operations
  - Uses `./DB/Data.db` as default database

- **data_processor.py**: DataProcessor class
  - ETL pipeline for ingesting Excel/CSV files
  - Configuration-driven column mapping
  - Uses JSON config files in `./Models/` directory
  - Merges multiple files and imports into SQLite

### Data Flow

1. **Data Ingestion**: Excel/CSV files matched by glob patterns → processed via config mapping → imported to SQLite
2. **Web UI**: Frontend requests API endpoints → backend queries database → JSON responses
3. **Data Export**: Users trigger downloads → backend generates CSV/Excel → streamed to client

### Frontend Structure

- **static/index.html**: Main SPA layout with sidebar navigation
- **static/app.js**: Main application logic (~1000+ lines)
- **static/modules/**: Feature-specific modules (e.g., `high-load-cell/index.js` for burst monitoring)
- **static/libs/**: Bundled libraries (Tailwind CSS, axios, FontAwesome)

### Database

- **Location**: `./DB/Data.db` (SQLite)
- **Tables**: Dynamic, created based on import config (e.g., "4G指标", "5G指标", etc.)
- **Columns**: Field-mapped during import process

## API Endpoints

### Data Management
- `GET /api/tables` - List all tables
- `GET /api/tables/{table_name}/columns` - Get table columns
- `GET /api/tables/{table_name}/data` - Paginated data retrieval with search
- `GET /api/tables/{table_name}/count` - Get row count
- `GET /api/tables/{table_name}/download` - Export table to CSV/Excel
- `DELETE /api/tables/{table_name}/data` - Clear table

### File Management
- `GET /api/files` - List uploaded files with metadata
- `POST /api/files/upload` - Upload Excel/CSV files
- `GET /api/files/{filename}/download` - Download file
- `DELETE /api/files/{filename}` - Delete file

### Model Execution
- `GET /api/models` - List available config models from `./Models/`
- `POST /api/models/execute` - Execute data import with specific model config (async)
- `GET /api/models/execute/{task_id}` - Check async task status

### Monitoring
- `GET /api/query/overload` - Query burst load cells with statistics
- `GET /api/query/overload/download` - Download burst load data (CSV/Excel)
  - **Parameters**: `start_time`, `end_time`, `format` (csv|xlsx)
  - **Note**: Uses SQL script `./Scripts/OverLoad.sql` for query

## Configuration

### Import Models
JSON config files in `./Models/` directory define:
- Source file glob pattern
- Sheet name (for Excel)
- Field row number (header row)
- Data start row
- Column mapping (source field → target field)
- Export destination (database path, table name)

**Example structure** (see `Models/RDC突发指标监控.json`):
```json
{
  "File": { "Path": "./Data/*.xlsx", "SheetName": "Sheet0" },
  "Table": { "FieldRow": 1, "StartRow": 2 },
  "Columns": [
    { "Field": "source_col", "Target": "target_col", "DefaultValue": "" }
  ],
  "Export": { "Database": "./DB/Data.db", "Table": "table_name" }
}
```

### SQL Scripts
- **Location**: `./Scripts/` directory
- **OverLoad.sql**: Query template for burst load monitoring with time-range parameters

## Key Implementation Details

### FastAPI Patterns
- **Context Manager (lifespan)**: Application startup/shutdown lifecycle management
- **Streaming Responses**: Large file downloads use StreamingResponse with BytesIO
- **Query Parameters**: Pagination (`page`, `page_size`), search, time ranges
- **Path Validation**: SQL injection prevention via parameterized queries and bracket-quoted identifiers

### Database Patterns
- **Dynamic Table Names**: Uses bracket notation `[table_name]` for safety
- **Parameterized Queries**: All user inputs use ? placeholders
- **Connection Lifecycle**: Each operation creates/closes connection (no connection pooling)

### Frontend Patterns
- **Modular JavaScript**: Feature modules loaded dynamically
- **State Management**: Global variables for current page, table selection
- **Async/Await**: Promise-based API calls with axios
- **Custom Modal**: Cross-browser compatible dialog system

## Common Development Tasks

### Adding a New API Endpoint
1. Define async function in `main.py` with `@app.get/post/delete` decorator
2. Use `db.` methods for database operations
3. Return JSON dict or StreamingResponse for files
4. Handle exceptions with HTTPException(status_code, detail)

### Adding a New Data Import Model
1. Create JSON config in `./Models/` directory
2. Follow existing config structure (see Models folder)
3. Point "File.Path" to data location with glob pattern
4. Map columns under "Columns" section
5. Endpoint will auto-discover via `/api/models` GET

### Debugging
- Check browser console (F12) for frontend errors
- Server logs print to console on startup
- Database: `./DB/Data.db` can be opened with any SQLite client
- No-cache middleware strips caching headers for static files (helps with dev)

### Common Parameter Issues
- **API Parameter Mismatch**: Use `alias` parameter in Query() to map frontend parameter names to backend function parameters
  - Example: `param_name: str = Query(..., alias="frontend_name")`
- **Time Format**: Use ISO format with space separator: `YYYY-MM-DD HH:MM:SS`
- **URL Encoding**: Parameters like timestamps need `encodeURIComponent()` on frontend

## Testing

Run single tests or explore specific functionality by:
- Checking API responses via browser developer tools (Network tab)
- Uploading test files through UI
- Checking database directly: `sqlite3 ./DB/Data.db`
- Reviewing browser console for JavaScript errors

## Known Limitations & Notes

- SQLite (not suitable for high concurrency)
- No connection pooling (creates new connection per request)
- No authentication/authorization
- File upload to `./Data/` with no size limits
- All static assets served locally (no CDN) for offline/intranet use
