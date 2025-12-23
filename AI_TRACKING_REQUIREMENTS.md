# AI Tracking Module - Complete Requirements & Implementation Guide

## Overview

This document outlines the complete requirements for updating the "AI Assistant" section to "AI Tracking" with automated thinking capabilities that integrate with real-time tracking modules (Polymarket and future modules).

---

## Phase 1: UI/UX Updates

### 1.1 Component Renaming
- **Change component name**: "AI Assistant" → "AI Tracking"
- **Change subtitle**: "Get insights about your tracking modules" → "Get insights about our enabled tracking modules"
- **Update file**: `app/components/tracking-chat.tsx`

### 1.2 Enable Thinking Toggle
- **Add checkbox**: "Enable Thinking" 
- **Behavior**:
  - When **unchecked (Disabled)**: Chat interaction is enabled (manual mode)
  - When **checked (Enabled)**: Chat interaction is disabled (auto mode)
  - When enabled, show additional controls (see 1.3)

### 1.3 Thinking Interval Selection
- **Display condition**: Only visible when "Enable Thinking" is checked
- **Options**: Radio buttons or checkboxes for:
  - 5 minutes
  - 15 minutes
  - 30 minutes
  - 1 hour
  - 4 hours
- **Default**: None selected (user must choose before starting)

### 1.4 Start Thinking Button
- **Display condition**: Only visible when "Enable Thinking" is checked AND an interval is selected
- **Action**: Opens confirmation dialog (see 1.5)

### 1.5 Start Thinking Confirmation Dialog
- **Trigger**: When "Start Thinking" button is clicked
- **Content**:
  - Warning message about API costs (OpenRouter or Anthropic)
  - Note that each interaction uses these APIs and costs money
  - **Buttons**:
    - "Abort" - Cancel and close dialog
    - "Start" - Proceed with auto mode

### 1.6 Auto Mode UI Indicators
When auto mode is active, display:
- **Status indicator**: Small badge/indicator showing:
  - Auto mode is active
  - Selected interval (e.g., "Auto: 15m")
- **Last fetch timestamp**: Display when AI last fetched data (e.g., "Last updated: 10:30 AM")
- **Stop button**: Button to stop auto mode
- **Clear session button/icon**: Removes cookies containing `ai_response` data

### 1.7 Module Button States
- **When auto mode is active**: Disable all manual fetch buttons for enabled modules (e.g., "Fetch Markets" button in Polymarket Tracking)
- **When auto mode is inactive**: Enable all manual fetch buttons

### 1.8 Chat Input State
- **When auto mode is active**: Disable chat input field
- **When auto mode is inactive**: Enable chat input field

---

## Phase 2: Frontend State Management

### 2.1 Global State Variables
Create and manage the following state variables:

- **`trackingEnabled`** (boolean): 
  - `true` when auto mode is active
  - `false` when auto mode is inactive
  - Stored in React context or passed via props to all tracking modules

- **`thinkingInterval`** (string | null):
  - Selected interval: "5m", "15m", "30m", "1h", "4h"
  - `null` when no interval selected

- **`isThinkingActive`** (boolean):
  - `true` when auto mode is running
  - `false` when stopped

- **`lastFetchTime`** (Date | null):
  - Timestamp of last data fetch
  - Updated after each successful fetch

### 2.2 Cookie Management
- **Storage**: Store `ai_response` data in cookies after each auto fetch
- **Key format**: `ai_response_<timestamp>` or single `ai_response` key with array
- **Clear function**: Remove all `ai_response` cookies when "Clear session" is clicked
- **Retrieval**: Load chat history from cookies on component mount (if available)

### 2.3 Module Communication
- **Polymarket Tracking component**:
  - Check `trackingEnabled` state
  - If `true`: Automatically fetch data based on `thinkingInterval`
  - If `true`: Disable manual "Fetch Markets" button
  - If `true`: Use data from backend response (see Phase 4) instead of manual fetch

---

## Phase 3: Frontend-Backend Integration

### 3.1 Start Thinking Endpoint
- **Endpoint**: `POST /ai-tracking/start-thinking`
- **Request body**:
```json
{
  "interval": "15m",
  "enabled_modules": ["polymarket"],
  "analysis_id": "20251223_000322",
  "chat_history": [
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "assistant", 
      "content": "..."
    }
  ]
}
```

- **Response**:
```json
{
  "status": "success",
  "message": "Auto thinking started",
  "next_fetch_at": "2025-12-23T10:45:00Z"
}
```

### 3.2 Stop Thinking Endpoint
- **Endpoint**: `POST /ai-tracking/stop-thinking`
- **Request body**:
```json
{
  "analysis_id": "20251223_000322"
}
```

- **Response**:
```json
{
  "status": "success",
  "message": "Auto thinking stopped"
}
```

### 3.3 Fetch Analysis Endpoint (Auto Mode)
- **Endpoint**: `POST /ai-tracking/fetch-analysis`
- **Trigger**: Called automatically by frontend based on selected interval
- **Request body**:
```json
{
  "analysis_id": "20251223_000322",
  "enabled_modules": ["polymarket"],
  "chat_history": [
    // Previous chat messages from cookies
  ],
  "polymarket_config": {
    "url": "https://polymarket.com/event/...",
    "slug": "bitcoin-above-on-december-23"
  }
}
```

- **Response** (see Phase 4 for full structure):
```json
{
  "ai_response": {
    "content": "Based on our existing analysis...",
    "timestamp": "2025-12-23T10:30:00Z"
  },
  "polymarket_response": {
    "status": "success",
    "event_slug": "bitcoin-above-on-december-23",
    "endDate": "2025-12-23T17:00:00Z",
    "markets_count": 11,
    "markets": [...]
  }
}
```

### 3.4 Manual Chat Endpoint (Disabled Mode)
- **Endpoint**: `POST /ai-tracking/chat`
- **Trigger**: When user sends message in manual mode
- **Request body**:
```json
{
  "analysis_id": "20251223_000322",
  "message": "User's question",
  "chat_history": [
    // Previous chat messages
  ],
  "enabled_modules": ["polymarket"],
  "polymarket_data": {
    // Current Polymarket data if available
  }
}
```

- **Response**:
```json
{
  "ai_response": {
    "content": "AI response text",
    "timestamp": "2025-12-23T10:30:00Z"
  }
}
```

---

## Phase 4: Backend Implementation

### 4.1 AI Analysis Function Setup

#### 4.1.1 System Prompt
```python
SYSTEM_PROMPT = """Based on our existing analysis, and our provided realtime data as of now <timestamp>, give your two cents about what is happening. In particular I want you to provide an immediate action plan containing what to look out for, what to track and how to respond."""
```

#### 4.1.2 User Prompt Construction
The user prompt should include (in order):

1. **Analysis Files** (always included):
   - `api/analysis/<analysis_id>/comprehensive_analysis.txt`
   - `api/analysis/<analysis_id>/output.csv`

2. **Chat History** (if available):
   - Previous messages from frontend cookies
   - Format: Array of `{role: "user"|"assistant", content: "..."}`

3. **Module Data** (conditional, based on enabled modules):
   - **Polymarket** (if enabled):
     - Include all Polymarket data retrieved
     - Add context: "Realtime information provided from Polymarket: {all the polymarket data retrieved}"
     - **Important**: Note that frontend displays calculated values:
       - Main datapoint: `ID: 949324, Active/Open, Price: <78,000, Volume: $23.71K, Chance: <1%, Buy Yes: 0.1¢, Buy No: 100¢`
     - Include this context in the prompt

#### 4.1.3 Module Data Checks
- **Check enabled modules** before including data:
  - Only include Polymarket data if `"polymarket"` is in `enabled_modules`
  - Only include future modules if they are in `enabled_modules`
- **Reuse existing functions**: Use existing Polymarket fetching functions from `api/poly.py`

### 4.2 Backend Response Structure

#### 4.2.1 Auto Mode Response
```json
{
  "ai_response": {
    "content": "Full AI analysis text...",
    "timestamp": "2025-12-23T10:30:00Z"
  },
  "polymarket_response": {
    "status": "success",
    "event_slug": "bitcoin-above-on-december-23",
    "endDate": "2025-12-23T17:00:00Z",
    "markets_count": 11,
    "markets": [
      {
        "id": "949358",
        "question": "Will the price of Bitcoin be above $84,000 on December 23?",
        "groupItemTitle": "84,000",
        "details": {
          "active": true,
          "closed": false,
          "outcomes": "[\"Yes\", \"No\"]",
          "outcomePrices": "[\"0.9925\", \"0.0075\"]",
          "volume": "94649.391723"
        }
      },
      {
        "id": "949360",
        "question": "Will the price of Bitcoin be above $86,000 on December 23?",
        "groupItemTitle": "86,000",
        "details": {
          "active": true,
          "closed": false,
          "outcomes": "[\"Yes\", \"No\"]",
          "outcomePrices": "[\"0.945\", \"0.055\"]",
          "volume": "104211.365158"
        }
      }
    ]
  }
}
```

**Note**: The `polymarket_response` key is only included if Polymarket module is enabled.

#### 4.2.2 Manual Mode Response
```json
{
  "ai_response": {
    "content": "AI response to user's question...",
    "timestamp": "2025-12-23T10:30:00Z"
  }
}
```

### 4.3 Backend Route Implementation

#### 4.3.1 Create New Route File
- **File**: `api/routes/ai_tracking_routes.py`
- **Routes**:
  - `POST /ai-tracking/start-thinking`
  - `POST /ai-tracking/stop-thinking`
  - `POST /ai-tracking/fetch-analysis`
  - `POST /ai-tracking/chat`

#### 4.3.2 Key Implementation Points
- **No interval logic in backend**: Backend only responds to frontend requests
- **Frontend controls timing**: Frontend uses `setInterval` based on selected interval
- **Error handling**: Return appropriate error messages for:
  - Missing analysis files
  - API key issues
  - Module fetch failures
  - AI API failures

### 4.4 Data Flow

1. **Frontend** sends request with:
   - `analysis_id`
   - `enabled_modules`
   - `chat_history` (from cookies)
   - Module-specific configs (e.g., Polymarket URL/slug)

2. **Backend**:
   - Reads analysis files (`comprehensive_analysis.txt`, `output.csv`)
   - Checks enabled modules
   - Fetches data from enabled modules (e.g., Polymarket)
   - Constructs AI prompt with all data
   - Calls AI API (OpenRouter or Anthropic)
   - Returns combined response

3. **Frontend**:
   - Receives response
   - Updates chat window with AI response
   - Updates module UI with module data (e.g., Polymarket markets)
   - Saves `ai_response` to cookies
   - Updates `lastFetchTime`

---

## Phase 5: Frontend Auto-Fetch Logic

### 5.1 Interval Management
- **Use `setInterval`**: Set up interval based on selected option:
  - 5m = 300,000ms
  - 15m = 900,000ms
  - 30m = 1,800,000ms
  - 1h = 3,600,000ms
  - 4h = 14,400,000ms

- **Clear interval**: When auto mode stops, clear the interval

### 5.2 Fetch Process
1. Check if `trackingEnabled` is `true`
2. Check if `isThinkingActive` is `true`
3. Call `POST /ai-tracking/fetch-analysis`
4. On success:
   - Display AI response in chat
   - Update Polymarket Tracking component with `polymarket_response` data
   - Save `ai_response` to cookies
   - Update `lastFetchTime`
5. On error:
   - Display error message
   - Log error
   - Continue with next interval (don't stop auto mode)

### 5.3 Module Data Update
- **Polymarket Tracking component**:
  - Check if `trackingEnabled` is `true`
  - If `true`, listen for data updates from auto-fetch response
  - Update `marketsData` state with `polymarket_response` data
  - Disable manual "Fetch Markets" button

---

## Phase 6: Integration Points

### 6.1 Polymarket Tracking Component Updates
- **Add prop**: `trackingEnabled` (boolean)
- **Add prop**: `autoModeData` (PolymarketMarketsResponse | null)
- **Logic**:
  ```typescript
  if (trackingEnabled && autoModeData) {
    // Use autoModeData instead of manual fetch
    setMarketsData(autoModeData);
    // Disable fetch button
  }
  ```

### 6.2 Market Dashboard Component Updates
- **Pass props**: 
  - `trackingEnabled` to PolymarketTracking
  - `analysisId` to TrackingChat
- **State management**: Manage `trackingEnabled` state at dashboard level

### 6.3 Tracking Chat Component Updates
- **Rename**: "AI Assistant" → "AI Tracking"
- **Add controls**: Enable Thinking checkbox, interval selection, Start button
- **Add indicators**: Status badge, last fetch time, stop button, clear session
- **Manage state**: `trackingEnabled`, `thinkingInterval`, `isThinkingActive`
- **Cookie management**: Save/load `ai_response` data

---

## Phase 7: Error Handling & Edge Cases

### 7.1 Error Scenarios
- **Missing analysis files**: Show error, don't crash
- **API key not configured**: Show warning in dialog before starting
- **Module fetch failure**: Continue with other modules, show partial data
- **AI API failure**: Show error message, retry on next interval
- **Network failure**: Show error, retry on next interval

### 7.2 Edge Cases
- **User stops auto mode mid-fetch**: Cancel request, clear interval
- **User changes interval**: Restart interval with new timing
- **User enables/disables module**: Update enabled_modules list
- **Cookies full**: Handle cookie storage limits gracefully
- **Multiple tabs**: Consider state synchronization (optional)

---

## Phase 8: Testing Checklist

### 8.1 UI Testing
- [ ] Component name changed to "AI Tracking"
- [ ] Subtitle updated correctly
- [ ] Enable Thinking checkbox works
- [ ] Interval selection appears when enabled
- [ ] Start Thinking button appears when interval selected
- [ ] Confirmation dialog shows correctly
- [ ] Auto mode indicators display correctly
- [ ] Stop button stops auto mode
- [ ] Clear session removes cookies
- [ ] Module buttons disable when auto mode active
- [ ] Chat input disables when auto mode active

### 8.2 Functionality Testing
- [ ] Auto mode starts correctly
- [ ] Interval timing works correctly
- [ ] Data fetches at correct intervals
- [ ] AI responses display in chat
- [ ] Module data updates correctly
- [ ] Cookies save correctly
- [ ] Chat history loads from cookies
- [ ] Manual mode still works when auto mode disabled
- [ ] Error handling works for all scenarios

### 8.3 Integration Testing
- [ ] Backend endpoints respond correctly
- [ ] Analysis files are read correctly
- [ ] Module data is fetched correctly
- [ ] AI prompt construction is correct
- [ ] Response structure matches requirements
- [ ] Frontend updates UI correctly from response

---

## Implementation Task List

### Task 1: Update Component Names & Labels
- [ ] Update `tracking-chat.tsx`: Change "AI Assistant" to "AI Tracking"
- [ ] Update subtitle text
- [ ] Update any related TypeScript interfaces/types

### Task 2: Add Enable Thinking Toggle
- [ ] Add checkbox component for "Enable Thinking"
- [ ] Implement state management for toggle
- [ ] Add conditional rendering for interval selection (only when enabled)

### Task 3: Add Interval Selection UI
- [ ] Create interval selection component (radio buttons or checkboxes)
- [ ] Options: 5m, 15m, 30m, 1h, 4h
- [ ] Store selected interval in state
- [ ] Show "Start Thinking" button when interval selected

### Task 4: Implement Start Thinking Dialog
- [ ] Create confirmation dialog component
- [ ] Add warning message about API costs
- [ ] Implement "Abort" and "Start" buttons
- [ ] Handle dialog state management

### Task 5: Create Backend Routes
- [ ] Create `api/routes/ai_tracking_routes.py`
- [ ] Implement `POST /ai-tracking/start-thinking`
- [ ] Implement `POST /ai-tracking/stop-thinking`
- [ ] Implement `POST /ai-tracking/fetch-analysis`
- [ ] Implement `POST /ai-tracking/chat`
- [ ] Register routes in main app

### Task 6: Implement AI Analysis Function
- [ ] Create function to read analysis files
- [ ] Create function to construct system prompt
- [ ] Create function to construct user prompt with:
  - Analysis files
  - Chat history
  - Module data (conditional)
- [ ] Integrate with existing AI client (OpenRouter/Anthropic)
- [ ] Handle errors gracefully

### Task 7: Implement Module Data Fetching
- [ ] Add logic to check enabled modules
- [ ] Integrate Polymarket data fetching
- [ ] Format module data for AI prompt
- [ ] Include module data in response

### Task 8: Implement Frontend Auto-Fetch Logic
- [ ] Create interval management function
- [ ] Implement auto-fetch on interval
- [ ] Handle fetch responses
- [ ] Update chat with AI responses
- [ ] Update module components with data
- [ ] Save responses to cookies

### Task 9: Implement Cookie Management
- [ ] Create functions to save `ai_response` to cookies
- [ ] Create functions to load chat history from cookies
- [ ] Create function to clear session cookies
- [ ] Handle cookie size limits

### Task 10: Update Polymarket Tracking Component
- [ ] Add `trackingEnabled` prop
- [ ] Add `autoModeData` prop
- [ ] Disable "Fetch Markets" button when auto mode active
- [ ] Use `autoModeData` when available
- [ ] Update component to listen for auto mode data

### Task 11: Add Auto Mode UI Indicators
- [ ] Create status indicator component
- [ ] Display selected interval
- [ ] Display last fetch timestamp
- [ ] Create stop button
- [ ] Create clear session button/icon

### Task 12: Update Market Dashboard
- [ ] Add `trackingEnabled` state management
- [ ] Pass `trackingEnabled` to PolymarketTracking
- [ ] Pass `analysisId` to TrackingChat
- [ ] Coordinate state between components

### Task 13: Implement Manual Chat Mode
- [ ] Ensure chat input works when auto mode disabled
- [ ] Implement manual chat endpoint call
- [ ] Display responses in chat
- [ ] Save manual chat history to cookies

### Task 14: Error Handling
- [ ] Add error handling for missing analysis files
- [ ] Add error handling for API failures
- [ ] Add error handling for module fetch failures
- [ ] Display user-friendly error messages
- [ ] Handle network errors gracefully

### Task 15: Testing & Refinement
- [ ] Test all UI components
- [ ] Test auto mode functionality
- [ ] Test manual mode functionality
- [ ] Test error scenarios
- [ ] Test cookie management
- [ ] Test module integration
- [ ] Fix any bugs found
- [ ] Optimize performance

---

## Notes & Clarifications

### Important Points
1. **Interval Logic**: Frontend controls all timing. Backend only responds to requests.
2. **Module Data**: Only fetch and include module data if that module is enabled.
3. **Response Structure**: Backend returns both `ai_response` and module data (e.g., `polymarket_response`) in a single response.
4. **Cookie Storage**: Store only `ai_response` data, not full module data.
5. **State Management**: `trackingEnabled` should be accessible to all tracking modules.
6. **Reuse Existing Code**: Use existing Polymarket functions from `api/poly.py`.
7. **No Duplicate Calls**: In auto mode, use backend response data to update modules, don't make separate API calls.

### Future Considerations
- Additional tracking modules can be added following the same pattern
- WebSocket/SSE could be added for real-time updates (future enhancement)
- State synchronization across browser tabs (future enhancement)
- Analytics/logging for API usage (future enhancement)

---

## File Structure Summary

### New Files to Create
- `api/routes/ai_tracking_routes.py` - Backend routes for AI tracking
- `app/lib/api/ai-tracking.ts` - Frontend API client functions (optional, can add to existing market-oracle.ts)

### Files to Modify
- `app/components/tracking-chat.tsx` - Main component updates
- `app/components/polymarket-tracking.tsx` - Add auto mode support
- `app/components/market-dashboard.tsx` - State management
- `app/lib/api/market-oracle.ts` - Add AI tracking API functions
- `api/routes/__init__.py` - Register new routes (if needed)
- `api/main.py` - Register new routes (if needed)

---

## Success Criteria

The implementation is complete when:
1. ✅ Component renamed to "AI Tracking"
2. ✅ Enable Thinking toggle works correctly
3. ✅ Interval selection and Start Thinking button work
4. ✅ Confirmation dialog appears with cost warning
5. ✅ Auto mode fetches data at correct intervals
6. ✅ AI responses display in chat automatically
7. ✅ Module data updates automatically
8. ✅ Manual mode still works when auto mode disabled
9. ✅ All buttons disable/enable correctly
10. ✅ Cookies save and load correctly
11. ✅ Error handling works for all scenarios
12. ✅ Stop and Clear Session buttons work

---

**End of Requirements Document**

