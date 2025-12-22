# Realtime Thinking Module - Feature Specification

## Overview

The Realtime Thinking Module is an intelligent monitoring and analysis system that continuously tracks market conditions, compares them against existing analysis data, and provides real-time insights through an interactive chat interface. This module acts as a "thinking assistant" that monitors changes in Polymarket data and event resolutions, alerting users to significant developments that may impact their trading decisions.

## Core Concept

The module operates as a background monitoring service that:
- Continuously compares current market data (Polymarket) against previously generated analysis
- Detects changes, discrepancies, and new opportunities
- Provides contextual insights through a chat-based interface
- Can be toggled on/off by users at any time
- Implements smart data reduction techniques to minimize API costs and processing overhead

## Key Features

### 1. Toggle Control
- **Frontend**: User interface toggle switch/button to enable/disable the module
- **State Management**: Module state persists across sessions (optional)
- **Visual Indicator**: Clear UI feedback showing when the module is active/inactive

### 2. Data Monitoring
- **Analysis Data Comparison**: Continuously compares current Polymarket data against stored analysis results
- **Change Detection**: Identifies:
  - Probability shifts in Polymarket markets
  - Event resolution status changes
  - New markets or events that weren't in original analysis
  - Significant price movement indicators (when chart data is added later)

### 3. Event Resolution Tracking
- **Resolution Status Monitoring**: Tracks when events resolve and their outcomes
- **Impact Analysis**: Correlates event resolutions with potential price impacts
- **Time-based Correlation**: Analyzes price changes over 1, 2, and 4-hour windows relative to event resolutions
- **Source Attribution**: Identifies which events may have caused observed price movements

### 4. Interactive Chat Interface
- **Embedded Chat Window**: UI component integrated into the dashboard
- **Real-time Updates**: Streams insights and alerts as they're detected
- **Contextual Responses**: Provides explanations for detected changes
- **Query Capability**: Users can ask questions about current market conditions
- **Message History**: Maintains conversation history during active session

### 5. Smart Data Reduction
- **Intelligent Polling**: Adjusts polling frequency based on:
  - Time until next scheduled event
  - Recent activity levels
  - User-defined sensitivity settings
- **Change Thresholds**: Only triggers updates when changes exceed configurable thresholds
- **Caching Strategy**: Efficiently caches data to minimize redundant API calls
- **Batch Processing**: Groups multiple checks to reduce API rate limit issues
- **Selective Monitoring**: Focuses on markets/events most relevant to user's analysis

## Technical Architecture

### Backend Components

#### 1. Realtime Monitoring Service
- **Location**: `api/realtime_monitor.py`
- **Responsibilities**:
  - Polls Polymarket API at configurable intervals
  - Compares current data against analysis snapshots
  - Detects significant changes
  - Manages polling state and rate limiting

#### 2. WebSocket/SSE Endpoint
- **Location**: `api/main.py` (new route)
- **Endpoint**: `/realtime/stream` or `/realtime/events`
- **Protocol**: WebSocket (preferred) or Server-Sent Events (SSE)
- **Responsibilities**:
  - Maintains persistent connection with frontend
  - Streams real-time updates to connected clients
  - Handles connection lifecycle (connect, disconnect, reconnect)

#### 3. Analysis Comparison Engine
- **Location**: `api/realtime_monitor.py` (component)
- **Responsibilities**:
  - Loads stored analysis data (CSV, comprehensive_analysis.txt)
  - Extracts Polymarket URLs and event references
  - Compares current Polymarket data with historical snapshots
  - Calculates change metrics (probability deltas, resolution status)

#### 4. Event Resolution Tracker
- **Location**: `api/realtime_monitor.py` (component)
- **Responsibilities**:
  - Monitors event resolution times
  - Tracks resolution outcomes
  - Correlates resolutions with time windows (1h, 2h, 4h)
  - Identifies potential causal relationships

#### 5. Data Reduction Manager
- **Location**: `api/realtime_monitor.py` (component)
- **Responsibilities**:
  - Implements adaptive polling intervals
  - Manages data caching
  - Applies change thresholds
  - Optimizes API call patterns

### Frontend Components

#### 1. Realtime Toggle Control
- **Location**: `app/components/realtime-toggle.tsx`
- **Responsibilities**:
  - Toggle switch/button UI
  - Manages connection state
  - Visual feedback (active/inactive indicators)
  - Persists state (optional: localStorage)

#### 2. Realtime Chat Window
- **Location**: `app/components/realtime-chat.tsx`
- **Responsibilities**:
  - Chat interface UI
  - Message display and history
  - Input field for user queries
  - Connection status indicator
  - Auto-scroll to latest messages

#### 3. WebSocket/SSE Client
- **Location**: `app/lib/api/realtime-client.ts`
- **Responsibilities**:
  - Establishes WebSocket/SSE connection
  - Handles reconnection logic
  - Processes incoming messages
  - Manages connection lifecycle

#### 4. Dashboard Integration
- **Location**: `app/components/market-dashboard.tsx`
- **Integration Points**:
  - Add RealtimeToggle component to dashboard header
  - Embed RealtimeChat component (collapsible panel or sidebar)
  - Pass `analysisId` to realtime components for context

## Data Flow

### Initialization Flow
1. User toggles module ON from frontend
2. Frontend establishes WebSocket/SSE connection to backend
3. Frontend sends `analysis_id` to backend
4. Backend loads analysis data for the given `analysis_id`
5. Backend extracts Polymarket URLs and event references
6. Backend initializes monitoring for identified markets/events
7. Backend sends confirmation message to frontend

### Monitoring Loop
1. Backend polls Polymarket API (with smart intervals)
2. Backend compares current data with stored analysis
3. Backend detects changes (if any exceed thresholds)
4. Backend generates insight message
5. Backend streams message to connected frontend clients
6. Frontend displays message in chat interface
7. Loop continues until module is toggled OFF

### Event Resolution Flow
1. Backend detects event resolution (via Polymarket API)
2. Backend checks resolution time against current time
3. Backend monitors price data (when available) over 1h, 2h, 4h windows
4. Backend correlates resolution with price movements
5. Backend generates analysis message
6. Backend streams message to frontend

### User Query Flow
1. User types question in chat interface
2. Frontend sends query to backend via WebSocket/SSE
3. Backend processes query with context:
   - Current Polymarket data
   - Original analysis data
   - Recent changes detected
4. Backend generates response (potentially using AI)
5. Backend streams response to frontend
6. Frontend displays response in chat

## Configuration

### Backend Configuration (`.env`)
```env
# Realtime Thinking Module Settings
REALTIME_ENABLED=true
REALTIME_POLL_INTERVAL=30  # seconds (default polling interval)
REALTIME_MIN_POLL_INTERVAL=10  # minimum interval (seconds)
REALTIME_MAX_POLL_INTERVAL=300  # maximum interval (seconds)
REALTIME_PROBABILITY_THRESHOLD=0.05  # minimum probability change to trigger update (0.0-1.0)
REALTIME_CACHE_TTL=60  # cache time-to-live (seconds)
REALTIME_EVENT_WINDOW_HOURS=4  # hours to monitor after event resolution
```

### Frontend Configuration (`.env.local`)
```env
# Realtime WebSocket/SSE URL
NEXT_PUBLIC_REALTIME_WS_URL=ws://localhost:5000/realtime/stream
# or for SSE:
NEXT_PUBLIC_REALTIME_SSE_URL=http://localhost:5000/realtime/events
```

## API Endpoints

### WebSocket Endpoint
```
ws://localhost:5000/realtime/stream
```

**Connection Message Format:**
```json
{
  "type": "connect",
  "analysis_id": "20251220_212438",
  "config": {
    "sensitivity": "medium",  // low, medium, high
    "monitor_windows": [1, 2, 4]  // hours
  }
}
```

**Message Types:**
- `connect` - Initialize connection
- `disconnect` - Close connection
- `query` - User query/question
- `update` - Real-time update from backend
- `error` - Error message
- `status` - Connection status

### REST Endpoint (Alternative/Supplemental)
```
POST /realtime/start
POST /realtime/stop
GET /realtime/status
```

## Data Structures

### Analysis Snapshot
```typescript
interface AnalysisSnapshot {
  analysis_id: string;
  timestamp: string;
  polymarket_events: PolymarketEvent[];
  predictions: Prediction[];
  created_at: string;
}
```

### Polymarket Event
```typescript
interface PolymarketEvent {
  event_slug: string;
  event_url: string;
  markets: Market[];
  resolution_time?: string;
  resolution_status?: 'pending' | 'resolved' | 'cancelled';
}
```

### Market
```typescript
interface Market {
  market_id: string;
  market_slug: string;
  outcomes: Outcome[];
  last_updated: string;
}
```

### Outcome
```typescript
interface Outcome {
  name: string;
  probability: number;  // 0.0-1.0
}
```

### Change Detection
```typescript
interface ChangeDetection {
  type: 'probability_change' | 'resolution' | 'new_market' | 'event_update';
  event_slug: string;
  market_id?: string;
  change_details: {
    previous_value?: any;
    current_value: any;
    delta?: number;
    significance: 'low' | 'medium' | 'high';
  };
  timestamp: string;
  message: string;  // Human-readable description
}
```

## Smart Data Reduction Strategies

### 1. Adaptive Polling Intervals
- **High Activity**: Poll every 10-30 seconds when events are near resolution
- **Normal Activity**: Poll every 60-120 seconds during regular hours
- **Low Activity**: Poll every 5-10 minutes during off-hours
- **Event-Based**: Immediately poll when scheduled events occur

### 2. Change Thresholds
- **Probability Changes**: Only report if delta > 5% (configurable)
- **Resolution Status**: Always report (high significance)
- **New Markets**: Always report (high significance)
- **Price Movements**: Only report if > 2% change (when chart data available)

### 3. Caching Strategy
- Cache Polymarket API responses for 60 seconds (configurable)
- Cache analysis data in memory (loaded once per analysis_id)
- Cache comparison results to avoid redundant calculations
- Invalidate cache on significant changes

### 4. Selective Monitoring
- Only monitor markets/events referenced in the analysis
- Skip markets that have already resolved (unless checking historical correlation)
- Focus on events with upcoming resolution times
- Prioritize high-impact events (based on analysis confidence)

### 5. Batch Processing
- Group multiple market checks into single API calls when possible
- Batch WebSocket messages to reduce connection overhead
- Aggregate similar changes into single update messages

## User Experience

### Visual Design
- **Toggle**: Prominent toggle switch in dashboard header
- **Chat Window**: Collapsible panel or sidebar (user preference)
- **Messages**: Clear formatting with timestamps, icons for message types
- **Status Indicator**: Visual indicator showing connection status and last update time
- **Loading States**: Clear feedback during connection establishment

### Message Types
- **Info**: General updates (blue/neutral color)
- **Alert**: Significant changes (yellow/warning color)
- **Critical**: High-impact changes (red/error color)
- **Query Response**: AI-generated responses (green/success color)

### Interaction Patterns
- **Auto-scroll**: Chat automatically scrolls to latest messages
- **Message Persistence**: Messages persist during session (optional: save to localStorage)
- **Copy/Share**: Users can copy messages or share insights
- **Mute/Filter**: Users can mute certain message types or filter by event

## Error Handling

### Connection Errors
- Automatic reconnection with exponential backoff
- Clear error messages to user
- Fallback to polling-based approach if WebSocket fails
- Graceful degradation if realtime features unavailable

### API Errors
- Handle Polymarket API rate limits gracefully
- Retry failed requests with backoff
- Cache last known good state
- Notify user of API issues

### Data Errors
- Validate analysis data before monitoring
- Handle missing or corrupted analysis files
- Provide helpful error messages
- Allow user to retry or reconfigure

## Security Considerations

- **Authentication**: Consider adding authentication for production
- **Rate Limiting**: Implement rate limiting on WebSocket connections
- **Input Validation**: Validate all user queries and inputs
- **CORS**: Ensure proper CORS configuration for WebSocket/SSE
- **Data Privacy**: Don't expose sensitive analysis data unnecessarily

## Performance Considerations

- **Connection Limits**: Limit number of concurrent WebSocket connections
- **Memory Management**: Efficiently manage cached data and connections
- **CPU Usage**: Optimize polling and comparison algorithms
- **Network Usage**: Minimize API calls through smart caching and batching
- **Scalability**: Design for potential horizontal scaling (Redis for state, etc.)

## Future Enhancements (Post-Initial Implementation)

### Chart Data Integration
When realtime chart data is added:
- Compare current prices against predicted price targets
- Detect when price movements align with predictions
- Alert when prices approach target levels
- Correlate price movements with event resolutions
- Provide visual price charts in chat interface

### Additional Features
- **Historical Correlation Analysis**: Analyze how past resolutions affected prices
- **Prediction Accuracy Tracking**: Track how well original predictions performed
- **Multi-Analysis Monitoring**: Monitor multiple analysis sessions simultaneously
- **Custom Alerts**: User-defined alert conditions
- **Export Insights**: Export chat history and insights
- **AI-Powered Summaries**: Periodic summaries of detected changes

## Implementation Phases

### Phase 1: Core Infrastructure
- Backend monitoring service skeleton
- WebSocket/SSE endpoint
- Frontend toggle and chat UI components
- Basic connection and message flow

### Phase 2: Polymarket Integration
- Analysis data loading and parsing
- Polymarket API polling
- Change detection logic
- Message generation

### Phase 3: Event Resolution Tracking
- Resolution status monitoring
- Time-window correlation
- Impact analysis
- Resolution-based alerts

### Phase 4: Smart Data Reduction
- Adaptive polling
- Caching implementation
- Change thresholds
- Selective monitoring

### Phase 5: User Queries & AI
- Query processing
- Context-aware responses
- AI integration for intelligent answers

### Phase 6: Polish & Optimization
- Performance optimization
- Error handling improvements
- UI/UX refinements
- Documentation

## Notes

- **Chart Data Exclusion**: Initial implementation excludes realtime chart data. Architecture should be designed to easily integrate chart data later.
- **Modularity**: Design components to be modular and independently testable
- **Testing**: Include unit tests for change detection, polling logic, and data reduction
- **Documentation**: Maintain clear documentation for API endpoints and data structures
- **Monitoring**: Consider adding logging and metrics for the monitoring service itself

