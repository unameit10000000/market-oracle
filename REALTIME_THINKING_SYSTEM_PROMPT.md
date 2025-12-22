# System Prompt: Realtime Thinking Module Implementation

## Context

You are implementing the **Realtime Thinking Module** for the Market Oracle application. This module provides continuous monitoring of Polymarket data, compares it against stored analysis results, and delivers real-time insights through an interactive chat interface.

## Project Structure

### Backend (Python Flask API)
- **Location**: `api/` directory
- **Main File**: `api/main.py` (Flask app with existing endpoints)
- **Polymarket Integration**: `api/poly.py` (existing Polymarket API client)
- **Analysis Storage**: `api/analysis/<analysis_id>/` directories containing:
  - `comprehensive_analysis.txt` - Full AI analysis
  - `output.csv` - Structured CSV data
  - `forexfactory_events.json` - Economic calendar events
  - `tradingeconomics_events.json` - Economic calendar events
  - Various transcript files

### Frontend (Next.js React App)
- **Location**: `app/` directory
- **Main Pages**: 
  - `app/app/page.tsx` - Home page with analysis workflow
  - `app/app/dashboard/page.tsx` - Dashboard page
- **Components**: `app/components/` directory
- **API Client**: `app/lib/api/market-oracle.ts` (existing API client)
- **Dashboard Component**: `app/components/market-dashboard.tsx`

## Existing Integration Points

### Polymarket API Endpoints (Already Implemented)
- `GET /poly/event?url=...` - Get event data by URL
- `GET /poly/event/slug/<slug>` - Get event data by slug
- `GET /poly/probabilities?url=...` - Get outcome probabilities
- `GET /poly/event/markets/list?url=...` - Get reduced market list
- `GET /poly/market/<id>` - Get market data by ID

### Analysis API Endpoints (Already Implemented)
- `POST /validate` - Validate YouTube URLs, returns `analysis_id`
- `POST /analyze` - Run analysis with economic calendar data
- `POST /process` - Generate CSV from analysis, returns CSV data

### Polymarket Client Functions (Available in `api/poly.py`)
- `get_event_by_slug(slug: str)` - Fetch event data
- `get_outcome_probabilities(polymarket_url: str)` - Get probabilities
- `get_event_data(polymarket_url: str)` - Get complete event data
- `extract_event_slug_from_url(url: str)` - Extract slug from URL

## Implementation Requirements

### Backend Implementation

#### 1. Create Realtime Monitoring Service
**File**: `api/realtime_monitor.py`

**Key Components**:
- `RealtimeMonitor` class that:
  - Loads analysis data from `analysis/<analysis_id>/` directory
  - Extracts Polymarket URLs and event references from analysis
  - Polls Polymarket API at configurable intervals
  - Compares current data with stored analysis snapshots
  - Detects significant changes (probability shifts, resolutions, etc.)
  - Implements smart data reduction (caching, adaptive polling, thresholds)
  - Generates human-readable insight messages

**Key Functions**:
```python
class RealtimeMonitor:
    def __init__(self, analysis_id: str, config: dict):
        """Initialize monitor for a specific analysis"""
    
    def load_analysis_data(self) -> dict:
        """Load and parse analysis data (CSV, comprehensive_analysis.txt)"""
    
    def extract_polymarket_references(self) -> List[dict]:
        """Extract Polymarket URLs and event slugs from analysis"""
    
    def poll_polymarket_data(self) -> dict:
        """Poll current Polymarket data for monitored events"""
    
    def compare_with_analysis(self, current_data: dict) -> List[ChangeDetection]:
        """Compare current data with stored analysis, return changes"""
    
    def should_poll(self) -> bool:
        """Determine if polling should occur based on smart reduction logic"""
    
    def generate_insight_message(self, change: ChangeDetection) -> str:
        """Generate human-readable message from detected change"""
```

#### 2. Add WebSocket/SSE Endpoint
**File**: `api/main.py` (add new route)

**Options**:
- **WebSocket** (preferred): Use `flask-socketio` or `websockets` library
- **Server-Sent Events (SSE)**: Simpler, works with Flask natively

**Endpoint**: `/realtime/stream` or `/realtime/events`

**Responsibilities**:
- Accept WebSocket/SSE connections from frontend
- Initialize `RealtimeMonitor` instance for connected `analysis_id`
- Stream real-time updates to connected clients
- Handle user queries and generate responses
- Manage connection lifecycle (connect, disconnect, reconnect)

**Message Protocol**:
```python
# Client -> Server
{
    "type": "connect",
    "analysis_id": "20251220_212438",
    "config": {
        "sensitivity": "medium",
        "monitor_windows": [1, 2, 4]
    }
}

# Server -> Client
{
    "type": "update",
    "timestamp": "2025-12-21T10:30:00Z",
    "change_type": "probability_change",
    "message": "Bitcoin price probability increased from 0.45 to 0.62...",
    "details": {...}
}
```

#### 3. Configuration
**File**: `api/.env` (add new variables)

Add configuration options:
- `REALTIME_POLL_INTERVAL` - Default polling interval (seconds)
- `REALTIME_PROBABILITY_THRESHOLD` - Minimum change to trigger update
- `REALTIME_CACHE_TTL` - Cache time-to-live (seconds)
- `REALTIME_EVENT_WINDOW_HOURS` - Hours to monitor after resolution

### Frontend Implementation

#### 1. Create Realtime Toggle Component
**File**: `app/components/realtime-toggle.tsx`

**Features**:
- Toggle switch/button to enable/disable module
- Visual indicator (active/inactive state)
- Optional: Persist state in localStorage
- Callback to notify parent component of state changes

**Props**:
```typescript
interface RealtimeToggleProps {
  analysisId: string;
  onToggle: (enabled: boolean) => void;
  defaultEnabled?: boolean;
}
```

#### 2. Create Realtime Chat Component
**File**: `app/components/realtime-chat.tsx`

**Features**:
- Chat message display area with scroll
- Message input field for user queries
- Connection status indicator
- Message history (persist during session)
- Auto-scroll to latest messages
- Message type styling (info, alert, critical, query response)

**Props**:
```typescript
interface RealtimeChatProps {
  analysisId: string;
  enabled: boolean;
  onClose?: () => void;
}
```

**State Management**:
- Messages array
- Connection status
- Input value
- Scroll position

#### 3. Create Realtime Client
**File**: `app/lib/api/realtime-client.ts`

**Features**:
- WebSocket/SSE client implementation
- Connection management (connect, disconnect, reconnect)
- Message handling and parsing
- Automatic reconnection with exponential backoff
- Error handling and status reporting

**API**:
```typescript
class RealtimeClient {
  constructor(url: string, analysisId: string);
  connect(): void;
  disconnect(): void;
  sendQuery(query: string): void;
  onMessage(callback: (message: RealtimeMessage) => void): void;
  onStatusChange(callback: (status: ConnectionStatus) => void): void;
}
```

#### 4. Integrate into Dashboard
**File**: `app/components/market-dashboard.tsx`

**Integration Points**:
- Add `RealtimeToggle` component to dashboard header (near filters)
- Add `RealtimeChat` component as collapsible panel or sidebar
- Pass `analysisId` prop to both components
- Handle toggle state changes
- Manage realtime client lifecycle

**Layout Considerations**:
- Toggle should be visible but not intrusive
- Chat window should be accessible but not block main content
- Consider collapsible/expandable chat panel
- Responsive design for mobile devices

## Data Flow Implementation

### 1. Analysis Data Parsing
- Parse `output.csv` to extract predictions and Polymarket references
- Parse `comprehensive_analysis.txt` to find Polymarket URLs
- Extract event slugs and market IDs from analysis
- Create snapshot of initial state for comparison

### 2. Change Detection Logic
- Compare current Polymarket probabilities with stored values
- Calculate deltas and check against thresholds
- Detect resolution status changes (pending -> resolved)
- Identify new markets not in original analysis
- Track event resolution times

### 3. Smart Data Reduction
- Implement adaptive polling based on:
  - Time until next event resolution
  - Recent activity levels
  - User sensitivity settings
- Cache Polymarket API responses
- Only trigger updates when changes exceed thresholds
- Batch multiple checks when possible

### 4. Message Generation
- Create human-readable messages from detected changes
- Include context (previous value, current value, delta)
- Explain significance of changes
- Provide actionable insights when possible

## Important Constraints

### 1. Chart Data Exclusion (Initial Phase)
- **DO NOT** implement realtime chart data integration in initial version
- Design architecture to easily add chart data later
- Use placeholder comments/markers where chart data will be integrated
- Document integration points for future chart data addition

### 2. Polymarket API Rate Limits
- Implement proper rate limiting and backoff
- Cache responses to minimize API calls
- Handle rate limit errors gracefully
- Notify users if rate limits are hit

### 3. Error Handling
- Handle missing or corrupted analysis files
- Handle Polymarket API failures
- Handle WebSocket/SSE connection issues
- Provide clear error messages to users
- Implement automatic reconnection logic

### 4. Performance
- Minimize memory usage (don't cache everything indefinitely)
- Optimize polling intervals
- Efficiently compare data (avoid full scans)
- Consider using background tasks/threads for monitoring

## Testing Considerations

### Backend Tests
- Test analysis data loading and parsing
- Test Polymarket API integration
- Test change detection logic
- Test smart data reduction algorithms
- Test WebSocket/SSE connection handling
- Test error scenarios

### Frontend Tests
- Test toggle component state management
- Test chat component message display
- Test WebSocket/SSE client connection
- Test reconnection logic
- Test UI responsiveness

## Code Style & Best Practices

### Python (Backend)
- Follow existing code style in `api/main.py` and `api/poly.py`
- Use type hints for function parameters and returns
- Add docstrings for all functions and classes
- Use logging instead of print statements
- Handle exceptions gracefully
- Follow Flask route patterns from existing code

### TypeScript/React (Frontend)
- Follow existing code style in `app/components/`
- Use TypeScript interfaces for all props and state
- Use React hooks (useState, useEffect, useCallback)
- Follow component patterns from existing components
- Use existing UI components from `app/components/ui/`
- Handle async operations properly (try/catch, loading states)

## Dependencies to Add

### Backend
- `flask-socketio` (if using WebSocket) OR use native Flask SSE support
- Consider `redis` for state management if scaling (optional for initial version)

### Frontend
- WebSocket client library (native browser WebSocket API is sufficient)
- OR EventSource for SSE (native browser API)

## Implementation Checklist

### Backend
- [ ] Create `api/realtime_monitor.py` with RealtimeMonitor class
- [ ] Implement analysis data loading and parsing
- [ ] Implement Polymarket data polling
- [ ] Implement change detection logic
- [ ] Implement smart data reduction
- [ ] Add WebSocket/SSE endpoint to `api/main.py`
- [ ] Add configuration variables to `.env`
- [ ] Add error handling and logging
- [ ] Test with existing analysis data

### Frontend
- [ ] Create `app/components/realtime-toggle.tsx`
- [ ] Create `app/components/realtime-chat.tsx`
- [ ] Create `app/lib/api/realtime-client.ts`
- [ ] Integrate components into `app/components/market-dashboard.tsx`
- [ ] Add styling and UI polish
- [ ] Test connection and message flow
- [ ] Test error scenarios and reconnection

### Integration
- [ ] Test end-to-end flow (toggle on -> connect -> receive updates)
- [ ] Test with multiple analysis IDs
- [ ] Test error scenarios
- [ ] Performance testing
- [ ] Documentation updates

## Future Enhancements (Post-Initial Implementation)

When adding realtime chart data:
1. Extend `RealtimeMonitor` to fetch chart data
2. Add price comparison logic
3. Correlate price movements with event resolutions
4. Add price charts to chat interface
5. Update change detection to include price movements

## Notes

- Keep code modular and testable
- Document all public APIs
- Consider backward compatibility
- Design for easy extension (chart data, additional data sources)
- Follow existing project patterns and conventions
- Prioritize user experience and performance

