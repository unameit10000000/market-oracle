# Realtime Chart Data Integration - Future Enhancement Plan

## Overview

This document outlines the plan for integrating realtime chart data into the Realtime Thinking Module. This enhancement will be implemented **after** the initial version that focuses on Polymarket data monitoring.

## Current State (Initial Implementation)

The initial Realtime Thinking Module will:
- Monitor Polymarket data (probabilities, event resolutions)
- Compare against stored analysis data
- Provide insights through chat interface
- **Exclude** realtime chart/price data

## Future Enhancement: Chart Data Integration

### Purpose

Adding realtime chart data will enable the module to:
- Compare actual price movements against predicted price targets
- Detect when prices approach or reach target levels
- Correlate price movements with event resolutions
- Provide more comprehensive market analysis
- Validate prediction accuracy in real-time

### Data Sources

#### Primary Options

1. **Kraken Exchange API** (Recommended)
   - Well-documented REST API
   - Real-time and historical price data
   - Support for major cryptocurrencies (BTC, ETH, XRP, etc.)
   - Free tier available
   - Endpoints:
     - `GET /0/public/Ticker` - Current price
     - `GET /0/public/OHLC` - OHLC (Open/High/Low/Close) data
     - `GET /0/public/Trades` - Recent trades

2. **CoinGecko API** (Alternative)
   - Free tier with rate limits
   - Simple REST API
   - Good coverage of cryptocurrencies
   - Endpoints:
     - `GET /simple/price` - Current prices
     - `GET /coins/{id}/ohlc` - OHLC data

3. **Binance API** (Alternative)
   - Comprehensive market data
   - WebSocket support for real-time updates
   - Good for high-frequency updates

#### Recommendation

Start with **Kraken API** for the following reasons:
- Already mentioned in project roadmap
- Reliable and well-maintained
- Good documentation
- Suitable rate limits for this use case
- Supports all major cryptocurrencies referenced in analysis

### Architecture Changes

#### Backend Modifications

**File**: `api/realtime_monitor.py`

**New Components**:

1. **Chart Data Fetcher**
```python
class ChartDataFetcher:
    def __init__(self, exchange: str = "kraken"):
        """Initialize chart data fetcher for specified exchange"""
    
    def get_current_price(self, symbol: str, pair: str = "USD") -> float:
        """Get current price for symbol (e.g., 'BTC', 'XRP')"""
    
    def get_ohlc_data(self, symbol: str, interval: str = "1h", limit: int = 24) -> List[dict]:
        """Get OHLC (Open/High/Low/Close) data for time period"""
    
    def get_price_history(self, symbol: str, hours: int) -> List[dict]:
        """Get price history for specified hours"""
```

2. **Price Comparison Engine**
```python
class PriceComparisonEngine:
    def __init__(self, analysis_data: dict):
        """Initialize with analysis data containing price targets"""
    
    def extract_price_targets(self) -> List[PriceTarget]:
        """Extract price targets from analysis data"""
    
    def compare_with_current_price(self, current_price: float, target: PriceTarget) -> PriceComparison:
        """Compare current price with target"""
    
    def check_target_reached(self, current_price: float, target: PriceTarget) -> bool:
        """Check if price target has been reached"""
    
    def calculate_price_movement(self, symbol: str, hours: int) -> PriceMovement:
        """Calculate price movement over time period"""
```

3. **Event-Price Correlation Analyzer**
```python
class EventPriceCorrelationAnalyzer:
    def __init__(self, monitor: RealtimeMonitor):
        """Initialize with realtime monitor instance"""
    
    def correlate_resolution_with_price(self, event: Event, resolution_time: datetime) -> Correlation:
        """Correlate event resolution with price movements"""
    
    def analyze_price_impact(self, event: Event, time_windows: List[int]) -> ImpactAnalysis:
        """Analyze price impact over 1h, 2h, 4h windows"""
    
    def find_supporting_sources(self, price_change: float, event: Event) -> List[str]:
        """Find sources that might support observed price change"""
```

**File**: `api/main.py`

**New Endpoint** (Optional):
```python
@app.route('/realtime/chart-data', methods=['GET'])
def get_chart_data():
    """
    Get current chart data for symbols.
    Query params: symbols (comma-separated), exchange (optional)
    """
```

**File**: `api/kraken.py` (New)

Create new Kraken API client similar to `api/poly.py`:
```python
"""
Kraken Exchange API Client
Fetches real-time and historical price data
"""

def get_ticker(symbol: str, pair: str = "USD") -> dict:
    """Get current ticker data for symbol"""

def get_ohlc(symbol: str, interval: str = "1h", since: int = None) -> dict:
    """Get OHLC data for symbol"""

def get_trades(symbol: str, since: int = None) -> dict:
    """Get recent trades for symbol"""
```

#### Frontend Modifications

**File**: `app/lib/api/market-oracle.ts`

**New API Methods**:
```typescript
// Add to marketOracleApi
getChartData(symbols: string[], exchange?: string): Promise<ChartDataResponse>
getPriceHistory(symbol: string, hours: number): Promise<PriceHistoryResponse>
```

**File**: `app/components/realtime-chat.tsx`

**Enhancements**:
- Display price information in messages
- Show price charts inline (using charting library)
- Highlight when targets are reached
- Visual indicators for price movements

**New Component**: `app/components/price-chart.tsx`
```typescript
interface PriceChartProps {
  symbol: string;
  timeframe: '1h' | '4h' | '24h';
  showTargets?: boolean;
  targets?: PriceTarget[];
}
```

### Data Structures

#### Price Target
```typescript
interface PriceTarget {
  symbol: string;  // "BTC", "XRP", etc.
  target_price: number;
  target_type: "support" | "resistance" | "prediction";
  timeframe: string;  // "1h", "2h", "4h", etc.
  confidence: number;  // 0.0-1.0
  source: string;  // Analysis source
  created_at: string;
}
```

#### Price Comparison
```typescript
interface PriceComparison {
  symbol: string;
  current_price: number;
  target_price: number;
  delta: number;  // current - target
  delta_percent: number;  // (current - target) / target * 100
  target_reached: boolean;
  distance_to_target: number;  // absolute distance
  significance: 'low' | 'medium' | 'high';
}
```

#### Price Movement
```typescript
interface PriceMovement {
  symbol: string;
  start_price: number;
  end_price: number;
  change: number;
  change_percent: number;
  timeframe: string;  // "1h", "2h", "4h"
  volatility: number;
  trend: 'up' | 'down' | 'sideways';
}
```

#### Correlation
```typescript
interface Correlation {
  event: Event;
  resolution_time: string;
  price_before: number;
  price_after: number;
  price_change: number;
  price_change_percent: number;
  time_windows: {
    '1h': PriceMovement;
    '2h': PriceMovement;
    '4h': PriceMovement;
  };
  correlation_strength: 'weak' | 'moderate' | 'strong';
  supporting_sources: string[];
}
```

### Integration Points

#### 1. Analysis Data Parsing

**Enhance**: `RealtimeMonitor.load_analysis_data()`

Extract price targets from:
- CSV data (`output.csv`) - Look for `Price_Level`, `Price_Type` columns
- Comprehensive analysis text - Parse price predictions and targets
- Store in structured format for comparison

**Example CSV columns to parse**:
```csv
Token,Price_Level,Price_Type,Timeframe,Forecast
Bitcoin,95000,Resistance,4h,Bullish
XRP,0.65,Support,2h,Bullish
```

#### 2. Monitoring Loop Enhancement

**Enhance**: `RealtimeMonitor.monitoring_loop()`

Add price checking:
1. Fetch current prices for all symbols in analysis
2. Compare with price targets
3. Detect when targets are reached
4. Calculate price movements over time windows
5. Generate price-related insights

**Pseudo-code**:
```python
def monitoring_loop(self):
    while self.active:
        # Existing Polymarket checks
        polymarket_changes = self.check_polymarket_changes()
        
        # NEW: Price checks
        price_changes = self.check_price_changes()
        
        # NEW: Target reached checks
        targets_reached = self.check_targets_reached()
        
        # NEW: Event-price correlation
        correlations = self.check_event_price_correlations()
        
        # Combine and send updates
        all_changes = polymarket_changes + price_changes + targets_reached + correlations
        self.send_updates(all_changes)
        
        self.wait_for_next_poll()
```

#### 3. Change Detection Enhancement

**Enhance**: `RealtimeMonitor.compare_with_analysis()`

Add price comparison logic:
- Compare current prices with stored price targets
- Detect significant price movements (> threshold)
- Identify when prices approach targets (within X%)
- Track price trends (upward, downward, sideways)

#### 4. Message Generation Enhancement

**Enhance**: `RealtimeMonitor.generate_insight_message()`

Add price-related message types:
- "Price target reached: Bitcoin hit $95,000 (predicted: $95,000)"
- "Price approaching target: XRP at $0.64, target $0.65 (1.6% away)"
- "Significant price movement: Bitcoin up 3.2% in last hour"
- "Event correlation: Fed rate decision resolved, Bitcoin moved +2.1% in 2 hours"

### Smart Data Reduction for Chart Data

#### 1. Adaptive Polling
- **High Volatility**: Poll every 30-60 seconds when prices are moving rapidly
- **Normal Conditions**: Poll every 2-5 minutes during regular trading
- **Low Activity**: Poll every 10-15 minutes during off-hours
- **Target Proximity**: Increase polling when price is within 5% of target

#### 2. Selective Monitoring
- Only monitor symbols mentioned in analysis
- Skip symbols with no price targets
- Focus on symbols with upcoming events
- Prioritize high-confidence predictions

#### 3. Caching Strategy
- Cache price data for 30-60 seconds
- Cache OHLC data for longer periods (5-10 minutes)
- Invalidate cache on significant price movements
- Store price snapshots for correlation analysis

#### 4. Change Thresholds
- Only report price changes > 2% (configurable)
- Only report target proximity when within 5% (configurable)
- Always report when target is reached
- Report correlations only if price change > 1% and correlation strength > moderate

### Configuration

**File**: `api/.env` (add new variables)

```env
# Chart Data Integration
CHART_DATA_ENABLED=true
CHART_DATA_EXCHANGE=kraken  # kraken, coingecko, binance
KRAKEN_API_KEY=  # Optional, for authenticated endpoints
KRAKEN_API_SECRET=  # Optional, for authenticated endpoints
CHART_DATA_POLL_INTERVAL=120  # seconds
CHART_DATA_PRICE_THRESHOLD=0.02  # 2% minimum change to trigger update
CHART_DATA_TARGET_PROXIMITY=0.05  # 5% proximity to target to increase monitoring
CHART_DATA_CACHE_TTL=60  # seconds
```

### UI Enhancements

#### Chat Interface
- **Price Messages**: Display current price, target price, and delta
- **Price Charts**: Inline mini-charts for price movements
- **Target Indicators**: Visual indicators when targets are reached
- **Correlation Visualizations**: Show event-price correlations graphically

#### Dashboard Integration
- **Price Widget**: Add price display widget to dashboard
- **Target Progress**: Show progress bars for price targets
- **Correlation Timeline**: Visualize event resolutions and price movements

### Implementation Phases

#### Phase 1: Basic Price Fetching
- Create Kraken API client
- Implement basic price fetching
- Add price data to monitoring loop
- Display prices in chat messages

#### Phase 2: Price Target Comparison
- Extract price targets from analysis
- Implement price comparison logic
- Generate target-related insights
- Add target reached alerts

#### Phase 3: Price Movement Analysis
- Implement price movement calculation
- Add trend detection
- Generate movement-based insights
- Add price charts to UI

#### Phase 4: Event-Price Correlation
- Implement correlation analysis
- Track price movements after event resolutions
- Generate correlation insights
- Add correlation visualizations

#### Phase 5: Advanced Features
- Historical correlation analysis
- Prediction accuracy tracking
- Multi-timeframe analysis
- Advanced charting features

### Testing Strategy

#### Backend Tests
- Test Kraken API integration
- Test price fetching and caching
- Test price comparison logic
- Test correlation analysis
- Test error handling (API failures, rate limits)

#### Frontend Tests
- Test price display in chat
- Test chart rendering
- Test target indicators
- Test correlation visualizations

#### Integration Tests
- Test end-to-end price monitoring
- Test target detection
- Test correlation analysis
- Test performance with multiple symbols

### Error Handling

#### API Failures
- Handle Kraken API rate limits
- Implement retry logic with backoff
- Fallback to alternative data sources
- Cache last known prices

#### Data Quality
- Validate price data before use
- Handle missing or invalid data
- Detect and report data anomalies
- Provide fallback values when needed

### Performance Considerations

#### API Rate Limits
- Kraken: 1 request per second (public endpoints)
- Implement proper rate limiting
- Use caching to minimize requests
- Batch requests when possible

#### Data Storage
- Store price snapshots for correlation analysis
- Implement efficient data structures
- Clean up old data periodically
- Consider database for historical data

#### Processing
- Optimize price comparison algorithms
- Use efficient data structures
- Minimize redundant calculations
- Consider background processing for heavy operations

### Migration Path

When implementing chart data integration:

1. **Backward Compatibility**: Ensure existing functionality continues to work
2. **Feature Flags**: Use configuration to enable/disable chart data features
3. **Gradual Rollout**: Implement in phases, test each phase thoroughly
4. **User Feedback**: Gather feedback and iterate

### Documentation Updates

When implementing:
- Update API documentation with new endpoints
- Update component documentation
- Add usage examples
- Document configuration options
- Create migration guide

### Dependencies to Add

#### Backend
- `requests` (already in use)
- `python-krakenex` (optional, official Kraken library)
- Or use direct REST API calls

#### Frontend
- `recharts` or `chart.js` (for price charts)
- Or use existing charting library if available

### Notes

- **Exchange Selection**: Start with Kraken, but design to support multiple exchanges
- **Symbol Mapping**: Map analysis symbols (Bitcoin, XRP) to exchange symbols (BTC/USD, XRP/USD)
- **Time Zones**: Handle timezone conversions properly
- **Data Accuracy**: Ensure price data accuracy and timestamps
- **Scalability**: Design for monitoring multiple symbols efficiently

