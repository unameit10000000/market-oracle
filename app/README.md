# Market Oracle Frontend 🎨

**Next.js Frontend Application for Market Oracle**

A modern, interactive web application built with Next.js 15, React, and TypeScript that provides a user-friendly interface for the Market Oracle API. The frontend handles the complete workflow from YouTube URL input to comprehensive market analysis visualization.

> **Note:** This frontend is part of the Market Oracle system. See the [main README](../README.md) for the complete system overview and quick start guide.

## 🏗️ Architecture

The frontend is built with:

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - High-quality React components
- **Recharts** - Data visualization library
- **React Hook Form** - Form management

### How It Works

1. **State Management**: Uses React hooks for local state management
2. **API Integration**: Communicates with the Flask API via REST endpoints
3. **Data Flow**: Home page → Validation → Analysis → Processing → Dashboard
4. **Session Storage**: Stores CSV data in sessionStorage to avoid URL length limits
5. **Theme Support**: Dark/light mode with theme persistence

## ✨ Features

- **YouTube URL Management** - Add, remove, and validate multiple YouTube URLs
- **Real-time Validation** - Instant feedback on URL validation status
- **Analysis Workflow** - Step-by-step process: Validate → Analyze → Process
- **Interactive Dashboard** - Comprehensive visualization of analysis results:
  - Price targets and projections with visual indicators
  - Event timeline with chronological display
  - Data visualization charts (price movements, event distribution)
  - Filterable data table with search and sorting
- **View Existing Analysis** - Access previously processed analyses by ID
- **Dark/Light Theme** - Toggle between themes
- **Responsive Design** - Works on desktop, tablet, and mobile devices

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** and **pnpm** (recommended) or **npm**
- **Market Oracle API** must be running (see [API README](../api/readme.md))

### Installation

1. **Navigate to the app directory**
   ```bash
   cd app
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   # or
   npm install
   ```

3. **Set up environment variables**
   
   Create a `.env.local` file in the `/app` directory:
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:5000
   ```
   
   **Important:** Make sure the API server is running on the configured URL.

4. **Run the development server**
   ```bash
   pnpm dev
   # or
   npm run dev
   ```

5. **Open the application**
   
   Navigate to [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
pnpm build
pnpm start
# or
npm run build
npm start
```

## 🔄 User Workflow

The frontend guides users through a 4-step workflow:

### Step 1: Add YouTube URLs
- Enter YouTube video URLs in the input field
- Add multiple URLs by clicking the "+" button
- URLs are validated for format (must be youtube.com or youtu.be)
- Remove URLs by clicking the trash icon

### Step 2: Validate URLs
- Click "Validate" button to validate all URLs
- Frontend sends `POST /validate` request to API
- API validates URLs, extracts transcripts, creates analysis directory
- Returns `analysis_id` and validation results
- UI displays validation status for each URL (success/failure)
- On success, "Analyze" button becomes available

### Step 3: Analyze
- Click "Analyze" button (only available after successful validation)
- Frontend sends `POST /analyze` request with `analysis_id`
- API scrapes economic calendars and runs AI analysis
- Analysis combines:
  - YouTube transcripts
  - ForexFactory events
  - TradingEconomics events
  - Historical event patterns
- On completion, "Process" button becomes available

### Step 4: Process & View Dashboard
- Click "Process" button (only available after analysis completes)
- Frontend sends `POST /process` request with `analysis_id`
- API generates CSV data from comprehensive analysis
- Returns CSV data, full analysis text, and event counts
- CSV data is stored in sessionStorage
- User is redirected to `/dashboard?analysisId=<id>`
- Dashboard displays all visualizations and data

### Viewing Existing Analysis
- Enter an existing `analysis_id` in the "View Existing Analysis" card
- Click "View Dashboard" to load that analysis
- Dashboard will fetch CSV data from the API if not in sessionStorage

## 📁 Project Structure

```
app/
├── app/                          # Next.js App Router directory
│   ├── page.tsx                 # Home page (URL input & workflow)
│   ├── dashboard/
│   │   └── page.tsx             # Dashboard page (data visualization)
│   ├── layout.tsx               # Root layout with theme provider
│   └── globals.css              # Global styles and theme variables
│
├── components/                   # React components
│   ├── ui/                      # shadcn/ui component library
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── table.tsx
│   │   └── ...                  # Other UI primitives
│   ├── market-dashboard.tsx     # Main dashboard container
│   ├── price-targets.tsx         # Price target visualization
│   ├── event-timeline.tsx        # Event timeline component
│   ├── dashboard-charts.tsx      # Chart visualizations
│   ├── data-table.tsx            # Filterable data table
│   ├── theme-provider.tsx        # Theme context provider
│   └── theme-toggle.tsx          # Theme switcher button
│
└── lib/                          # Utilities and helpers
    ├── api/
    │   ├── index.ts              # API client base configuration
    │   └── market-oracle.ts      # Market Oracle API functions
    ├── config.ts                 # App configuration
    ├── data-utils.ts             # CSV parsing and data transformation
    └── utils.ts                  # General utility functions
```

## 🧩 Key Components

### Home Page (`app/page.tsx`)
- **URL Management**: Add/remove YouTube URLs
- **Validation UI**: Real-time validation status display
- **Workflow Buttons**: Validate → Analyze → Process progression
- **Error Handling**: Displays error messages and validation failures
- **View Existing**: Input field to view previous analyses

### Dashboard (`app/dashboard/page.tsx`)
- **Data Loading**: Fetches CSV data from sessionStorage or API
- **Market Dashboard**: Renders the main dashboard component
- **Theme Toggle**: Accessible theme switcher

### Market Dashboard (`components/market-dashboard.tsx`)
- **Main Container**: Orchestrates all dashboard components
- **Data Parsing**: Converts CSV to structured data
- **State Management**: Manages dashboard state and data flow

### Price Targets (`components/price-targets.tsx`)
- **Visualization**: Displays price targets with color-coded indicators
- **Token Grouping**: Groups predictions by cryptocurrency token
- **Magnitude Display**: Shows prediction magnitude estimates

### Event Timeline (`components/event-timeline.tsx`)
- **Chronological Display**: Shows events in timeline format
- **Event Details**: Displays event information and predictions
- **Date Grouping**: Groups events by date

### Dashboard Charts (`components/dashboard-charts.tsx`)
- **Recharts Integration**: Uses Recharts for data visualization
- **Multiple Chart Types**: Price movements, event distribution, etc.
- **Interactive**: Hover tooltips and responsive design

### Data Table (`components/data-table.tsx`)
- **Filterable Table**: Search and filter functionality
- **Sortable Columns**: Click headers to sort
- **Pagination**: Handles large datasets
- **Export Options**: Copy data functionality

## 🔌 API Integration

The frontend communicates with the API through the `marketOracleApi` client:

### API Client (`lib/api/market-oracle.ts`)

**Functions:**
- `validateUrls(youtubeUrls: string[])` - Validates YouTube URLs
- `analyze(analysisId: string, config?)` - Runs analysis
- `process(analysisId: string)` - Generates CSV data
- `askAI(question: string, event: object, options?)` - Ask AI about events

**Configuration:**
- Base URL from `NEXT_PUBLIC_API_BASE_URL` environment variable
- Error handling and logging built-in
- TypeScript types for all responses

### Data Flow

1. **User Input** → Frontend validates format
2. **API Request** → Frontend sends HTTP request to API
3. **API Processing** → API processes request (may take time)
4. **Response Handling** → Frontend receives response and updates UI
5. **State Update** → React state updates trigger re-render
6. **Data Storage** → CSV data stored in sessionStorage for dashboard

## 🎨 Styling & Theming

- **Tailwind CSS**: Utility-first CSS framework
- **CSS Variables**: Theme colors defined in `globals.css`
- **Dark Mode**: Full dark mode support with `next-themes`
- **Responsive**: Mobile-first responsive design
- **Animations**: Smooth transitions and loading states

### Theme Configuration

Themes are configured in `globals.css` using CSS variables:
- Light theme: Default colors
- Dark theme: Dark mode variants
- Gradient effects: Multi-color gradients for visual appeal

## 📊 Data Handling

### CSV Parsing
- CSV data is parsed using custom utilities in `lib/data-utils.ts`
- Data is transformed into structured TypeScript objects
- Supports filtering, sorting, and searching

### Session Storage
- CSV data is stored in `sessionStorage` to avoid URL length limits
- Key format: `analysis_<analysisId>`
- Data persists during browser session
- Dashboard can fetch from API if sessionStorage is empty

### State Management
- React hooks (`useState`, `useEffect`) for local state
- No global state management library (kept simple)
- State flows from parent to child components

## 🐛 Error Handling

- **API Errors**: Displayed in Alert components with error messages
- **Validation Errors**: Shown inline with input fields
- **Network Errors**: Handled gracefully with user-friendly messages
- **Loading States**: Spinner indicators during async operations

## 🔧 Configuration

### Environment Variables

**Required:**
- `NEXT_PUBLIC_API_BASE_URL` - API server URL (default: `http://localhost:5000`)

### Build Configuration

- **Next.js Config**: `next.config.mjs` - Next.js configuration
- **TypeScript Config**: `tsconfig.json` - TypeScript compiler options
- **Tailwind Config**: `tailwind.config.ts` - Tailwind CSS configuration
- **PostCSS Config**: `postcss.config.mjs` - PostCSS configuration

## 🧪 Development

### Available Scripts

- `pnpm dev` - Start development server
- `pnpm build` - Build for production
- `pnpm start` - Start production server
- `pnpm lint` - Run ESLint

### Development Notes

- **Hot Reload**: Automatic page refresh on file changes
- **TypeScript**: Full type checking during development
- **Console Logging**: API calls and responses logged to console
- **Error Overlay**: Next.js error overlay for runtime errors

## 📝 Important Notes

- **API Must Be Running**: The frontend requires the API server to be running
- **CORS**: API must allow requests from the frontend origin
- **Session Storage**: CSV data is stored in browser sessionStorage
- **Analysis IDs**: Format: `YYYYMMDD_HHMMSS` (timestamp)
- **URL Validation**: Only YouTube URLs (youtube.com or youtu.be) are accepted
- **Theme Persistence**: Theme preference is saved in localStorage

## 🚨 Troubleshooting

**Frontend can't connect to API:**
- Check that API is running on the configured port
- Verify `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
- Check browser console for CORS errors

**Dashboard shows no data:**
- Verify analysis was processed successfully
- Check browser console for errors
- Try refreshing the page or re-processing the analysis

**Theme not working:**
- Clear browser localStorage
- Check browser console for errors
- Verify `next-themes` is properly configured

