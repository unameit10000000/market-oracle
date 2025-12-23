# AI Tracking Module - Step-by-Step Implementation Task List

## Quick Reference: Implementation Order

This is a concise, actionable task list for implementing the AI Tracking module. Refer to `AI_TRACKING_REQUIREMENTS.md` for detailed specifications.

---

## Phase 1: Frontend UI Updates (Tasks 1-4)

### ✅ Task 1: Rename Component & Update Labels
**File**: `app/components/tracking-chat.tsx`
- [ ] Change "AI Assistant" → "AI Tracking" (line 102)
- [ ] Change subtitle "Get insights about your tracking modules" → "Get insights about our enabled tracking modules" (line 105)
- [ ] Update any TypeScript interfaces if needed

### ✅ Task 2: Add Enable Thinking Toggle
**File**: `app/components/tracking-chat.tsx`
- [ ] Add state: `const [enableThinking, setEnableThinking] = useState(false)`
- [ ] Add checkbox component in CardHeader section
- [ ] Label: "Enable Thinking"
- [ ] When checked: Show interval selection (Task 3)
- [ ] When unchecked: Enable chat input, hide interval selection

### ✅ Task 3: Add Interval Selection UI
**File**: `app/components/tracking-chat.tsx`
- [ ] Add state: `const [thinkingInterval, setThinkingInterval] = useState<string | null>(null)`
- [ ] Create interval selection UI (radio buttons or checkboxes)
- [ ] Options: "5m", "15m", "30m", "1h", "4h"
- [ ] Only visible when `enableThinking === true`
- [ ] Show "Start Thinking" button when interval is selected

### ✅ Task 4: Implement Start Thinking Dialog
**File**: `app/components/tracking-chat.tsx`
- [ ] Add state: `const [showStartDialog, setShowStartDialog] = useState(false)`
- [ ] Create Dialog component with:
  - Warning about API costs (OpenRouter/Anthropic)
  - "Abort" button (closes dialog)
  - "Start" button (starts auto mode - see Task 8)

---

## Phase 2: State Management (Tasks 5-7)

### ✅ Task 5: Add Global State Management
**File**: `app/components/market-dashboard.tsx`
- [ ] Add state: `const [trackingEnabled, setTrackingEnabled] = useState(false)`
- [ ] Add state: `const [isThinkingActive, setIsThinkingActive] = useState(false)`
- [ ] Pass `trackingEnabled` as prop to `PolymarketTracking` component
- [ ] Pass `analysisId` as prop to `TrackingChat` component
- [ ] Create callback to update `trackingEnabled` from TrackingChat

### ✅ Task 6: Add Cookie Management Functions
**File**: `app/components/tracking-chat.tsx` or `app/lib/utils.ts`
- [ ] Create `saveAiResponseToCookie(aiResponse: object)` function
- [ ] Create `loadChatHistoryFromCookies(): ChatMessage[]` function
- [ ] Create `clearSessionCookies()` function
- [ ] Use cookie library (js-cookie or document.cookie)

### ✅ Task 7: Add Auto Mode State Variables
**File**: `app/components/tracking-chat.tsx`
- [ ] Add state: `const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null)`
- [ ] Add state: `const [autoModeInterval, setAutoModeInterval] = useState<NodeJS.Timeout | null>(null)`
- [ ] Load chat history from cookies on component mount

---

## Phase 3: Backend Implementation (Tasks 8-11)

### ✅ Task 8: Create Backend Route File
**File**: `api/routes/ai_tracking_routes.py` (NEW FILE)
- [ ] Create new file
- [ ] Import necessary modules (Flask, json, os, etc.)
- [ ] Import analysis functions from `api.analysis`
- [ ] Import poly functions from `api.poly`
- [ ] Import config (AI_API_TYPE, anthropic_client, etc.)

### ✅ Task 9: Implement Start Thinking Endpoint
**File**: `api/routes/ai_tracking_routes.py`
- [ ] Create route: `@app.route('/ai-tracking/start-thinking', methods=['POST'])`
- [ ] Validate request body: `interval`, `enabled_modules`, `analysis_id`, `chat_history`
- [ ] Return success response with `next_fetch_at` timestamp
- [ ] Register route in `api/main.py` or `api/routes/__init__.py`

### ✅ Task 10: Implement Fetch Analysis Endpoint
**File**: `api/routes/ai_tracking_routes.py`
- [ ] Create route: `@app.route('/ai-tracking/fetch-analysis', methods=['POST'])`
- [ ] Validate request: `analysis_id`, `enabled_modules`, `chat_history`
- [ ] Read analysis files:
  - `api/analysis/<analysis_id>/comprehensive_analysis.txt`
  - `api/analysis/<analysis_id>/output.csv`
- [ ] Check enabled modules and fetch data:
  - If "polymarket" in enabled_modules: Call `poly.get_event_by_slug()` or similar
- [ ] Construct AI prompt (see Task 11)
- [ ] Call AI API (OpenRouter/Anthropic)
- [ ] Return response with `ai_response` and module data (e.g., `polymarket_response`)

### ✅ Task 11: Implement AI Prompt Construction
**File**: `api/routes/ai_tracking_routes.py`
- [ ] Create function `construct_ai_prompt(analysis_files, chat_history, module_data, enabled_modules)`
- [ ] System prompt: "Based on our existing analysis, and our provided realtime data as of now <timestamp>, give your two cents about what is happening. In particular I want you to provide an immediate action plan containing what to look out for, what to track and how to respond."
- [ ] User prompt should include:
  1. Analysis files content (comprehensive_analysis.txt, output.csv)
  2. Chat history (if available)
  3. Module data (only if module is enabled):
     - Polymarket: "Realtime information provided from Polymarket: {data}"
     - Note: Frontend displays calculated values (ID, Active/Open, Price, Volume, Chance, Buy Yes/No)
- [ ] Call AI client with constructed prompt
- [ ] Return AI response

### ✅ Task 12: Implement Stop Thinking & Manual Chat Endpoints
**File**: `api/routes/ai_tracking_routes.py`
- [ ] Create route: `@app.route('/ai-tracking/stop-thinking', methods=['POST'])`
- [ ] Create route: `@app.route('/ai-tracking/chat', methods=['POST'])`
- [ ] Manual chat endpoint should work similarly to fetch-analysis but triggered by user message
- [ ] Register all routes

---

## Phase 4: Frontend API Integration (Tasks 13-15)

### ✅ Task 13: Add API Client Functions
**File**: `app/lib/api/market-oracle.ts`
- [ ] Add `startThinking(options)` function
- [ ] Add `stopThinking(analysisId)` function
- [ ] Add `fetchAnalysis(options)` function
- [ ] Add `sendChatMessage(options)` function
- [ ] Use existing `apiClient` from `app/lib/api/index.ts`

### ✅ Task 14: Implement Auto-Fetch Logic
**File**: `app/components/tracking-chat.tsx`
- [ ] Create function `startAutoMode()`:
  - Call `startThinking()` API
  - Set up `setInterval` based on selected interval
  - Store interval ID in state
  - Set `isThinkingActive = true`
- [ ] Create function `stopAutoMode()`:
  - Call `stopThinking()` API
  - Clear interval
  - Set `isThinkingActive = false`
- [ ] Create function `performAutoFetch()`:
  - Call `fetchAnalysis()` API
  - Update chat with AI response
  - Update `lastFetchTime`
  - Save `ai_response` to cookies
  - Emit event or callback to update module components

### ✅ Task 15: Connect Start Button to Auto Mode
**File**: `app/components/tracking-chat.tsx`
- [ ] In Start Thinking dialog "Start" button handler:
  - Call `startAutoMode()`
  - Close dialog
  - Update UI to show auto mode indicators

---

## Phase 5: Module Integration (Tasks 16-18)

### ✅ Task 16: Update Polymarket Tracking Component
**File**: `app/components/polymarket-tracking.tsx`
- [ ] Add prop: `trackingEnabled?: boolean`
- [ ] Add prop: `autoModeData?: PolymarketMarketsResponse | null`
- [ ] Add prop: `onDataUpdate?: (data: PolymarketMarketsResponse) => void` (optional)
- [ ] When `trackingEnabled === true`:
  - Disable "Fetch Markets" button
  - If `autoModeData` is provided, use it instead of manual fetch
  - Update `marketsData` state with `autoModeData`
- [ ] When `trackingEnabled === false`:
  - Enable "Fetch Markets" button
  - Use manual fetch as before

### ✅ Task 17: Update Market Dashboard Component
**File**: `app/components/market-dashboard.tsx`
- [ ] Pass `trackingEnabled` prop to `PolymarketTracking`
- [ ] Pass `analysisId` prop to `TrackingChat`
- [ ] Create callback function to receive `trackingEnabled` updates from TrackingChat
- [ ] Create callback function to receive auto mode data and pass to PolymarketTracking

### ✅ Task 18: Implement Data Flow from Auto Fetch to Modules
**File**: `app/components/tracking-chat.tsx`
- [ ] After successful auto fetch:
  - Extract `polymarket_response` from backend response (if present)
  - Call callback to update PolymarketTracking component
  - Or use React Context/state management to share data

---

## Phase 6: UI Indicators & Controls (Tasks 19-21)

### ✅ Task 19: Add Auto Mode Status Indicator
**File**: `app/components/tracking-chat.tsx`
- [ ] Display badge/indicator when `isThinkingActive === true`
- [ ] Show selected interval (e.g., "Auto: 15m")
- [ ] Place in CardHeader or near title

### ✅ Task 20: Add Last Fetch Time Display
**File**: `app/components/tracking-chat.tsx`
- [ ] Display `lastFetchTime` when available
- [ ] Format: "Last updated: 10:30 AM" or similar
- [ ] Update after each successful fetch

### ✅ Task 21: Add Stop & Clear Session Buttons
**File**: `app/components/tracking-chat.tsx`
- [ ] Add "Stop" button (only visible when `isThinkingActive === true`)
- [ ] On click: Call `stopAutoMode()`
- [ ] Add "Clear Session" button/icon
- [ ] On click: Call `clearSessionCookies()` and clear chat messages

---

## Phase 7: Manual Mode & Chat Input (Tasks 22-23)

### ✅ Task 22: Implement Manual Chat Mode
**File**: `app/components/tracking-chat.tsx`
- [ ] When `enableThinking === false`:
  - Enable chat input
  - On send: Call `sendChatMessage()` API
  - Display response in chat
  - Save to cookies

### ✅ Task 23: Disable Chat Input in Auto Mode
**File**: `app/components/tracking-chat.tsx`
- [ ] When `isThinkingActive === true`:
  - Disable chat input field
  - Show message: "Auto mode active - chat disabled"

---

## Phase 8: Error Handling (Task 24)

### ✅ Task 24: Add Comprehensive Error Handling
**Files**: Multiple
- [ ] Backend: Handle missing analysis files gracefully
- [ ] Backend: Handle API key errors
- [ ] Backend: Handle module fetch failures
- [ ] Frontend: Display user-friendly error messages
- [ ] Frontend: Handle network errors
- [ ] Frontend: Continue auto mode on errors (don't stop)
- [ ] Frontend: Show error in chat when fetch fails

---

## Phase 9: Testing & Refinement (Tasks 25-26)

### ✅ Task 25: Test All Functionality
- [ ] Test Enable Thinking toggle
- [ ] Test interval selection
- [ ] Test Start Thinking dialog
- [ ] Test auto mode starts correctly
- [ ] Test data fetches at correct intervals
- [ ] Test AI responses display
- [ ] Test module data updates
- [ ] Test manual mode still works
- [ ] Test stop button
- [ ] Test clear session
- [ ] Test error scenarios

### ✅ Task 26: Fix Bugs & Optimize
- [ ] Fix any bugs found during testing
- [ ] Optimize performance (reduce unnecessary re-renders)
- [ ] Clean up console logs
- [ ] Update any TypeScript types
- [ ] Ensure all linter errors are fixed

---

## Quick Implementation Checklist

### Must-Have Features
- [x] Component renamed to "AI Tracking"
- [ ] Enable Thinking toggle
- [ ] Interval selection (5m, 15m, 30m, 1h, 4h)
- [ ] Start Thinking button with confirmation dialog
- [ ] Auto mode fetches data at intervals
- [ ] AI responses display automatically
- [ ] Module data updates automatically
- [ ] Manual mode still works
- [ ] Stop button works
- [ ] Clear session works
- [ ] Cookies save/load correctly

### Backend Requirements
- [ ] `/ai-tracking/start-thinking` endpoint
- [ ] `/ai-tracking/stop-thinking` endpoint
- [ ] `/ai-tracking/fetch-analysis` endpoint
- [ ] `/ai-tracking/chat` endpoint
- [ ] AI prompt construction with analysis files + module data
- [ ] Response includes both `ai_response` and module data

### Frontend Requirements
- [ ] State management for `trackingEnabled`
- [ ] Cookie management for chat history
- [ ] Auto-fetch interval logic
- [ ] Module component updates from auto mode
- [ ] UI indicators for auto mode status
- [ ] Error handling throughout

---

## Notes

1. **Start with UI**: Implement Tasks 1-4 first to get the UI structure
2. **Then Backend**: Implement Tasks 8-12 to get backend working
3. **Then Integration**: Connect frontend to backend (Tasks 13-15)
4. **Then Modules**: Update module components (Tasks 16-18)
5. **Finally Polish**: Add indicators, error handling, testing

6. **Interval Timing**: Frontend controls all timing. Backend only responds to requests.

7. **Module Data**: Only include module data in response if that module is enabled.

8. **Reuse Code**: Use existing functions from `api/poly.py` for Polymarket data.

---

**End of Task List**

