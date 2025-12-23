"use client";

import { useState, useEffect } from "react";
import { parseCSVData } from "@/lib/data-utils";
import { marketOracleApi } from "@/lib/api/market-oracle";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import PriceTargets from "@/components/price-targets";
import EventTimeline from "@/components/event-timeline";
import DashboardCharts from "@/components/dashboard-charts";
import DataTable from "@/components/data-table";
import PolymarketTracking from "@/components/polymarket-tracking";
import TrackingChat from "@/components/tracking-chat";
import ComingSoonModules from "@/components/coming-soon-modules";
import { Input } from "@/components/ui/input";
import { Search, Maximize2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface MarketDashboardProps {
  csvData?: string;
  analysisId?: string;
}

export default function MarketDashboard({
  csvData,
  analysisId,
}: MarketDashboardProps) {
  const [data, setData] = useState<any[]>([]);
  const [filteredData, setFilteredData] = useState<any[]>([]);
  const [tokenFilter, setTokenFilter] = useState("all");
  const [timeframeFilter, setTimeframeFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreenOpen, setIsFullscreenOpen] = useState(false);

  // Fetch data from API or use provided CSV data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);

        let marketData;
        let rawCsvData = "";

        if (csvData) {
          // Parse the provided CSV data
          rawCsvData = csvData;
          console.log("[MarketDashboard] Using provided CSV data, length:", csvData.length);
          console.log("[MarketDashboard] CSV preview (first 500 chars):", csvData.substring(0, 500));
          marketData = parseCSVData(csvData);
        } else if (analysisId) {
          // Fetch from API if analysis ID provided
          console.log("[MarketDashboard] Fetching data for analysis ID:", analysisId);
          const response = await marketOracleApi.process(analysisId);
          console.log("[MarketDashboard] Process response:", {
            status: response.status,
            csv_data_length: response.csv_data?.length || 0,
            csv_preview: response.csv_data?.substring(0, 500) || "No data",
          });
          rawCsvData = response.csv_data;
          marketData = parseCSVData(response.csv_data);
        } else {
          throw new Error("No CSV data or analysis ID provided");
        }

        console.log("[MarketDashboard] Parsed data:", {
          rowCount: marketData.length,
          firstRow: marketData[0],
          headers: marketData.length > 0 ? Object.keys(marketData[0]) : [],
        });

        if (marketData.length === 0) {
          console.warn("[MarketDashboard] No data parsed from CSV!");
          console.warn("[MarketDashboard] Raw CSV data:", rawCsvData);
        }

        setData(marketData);
        setFilteredData(marketData);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch data:", err);
        setError(`Failed to load data: ${err instanceof Error ? err.message : "Unknown error"}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [csvData, analysisId]);

  // Apply filters to data
  const applyFilters = (data: any[]) => {
    return data.filter((row) => {
      let match = true;

      // Apply token filter
      if (tokenFilter !== "all" && row.Token !== tokenFilter) {
        match = false;
      }

      // Apply timeframe filter
      if (timeframeFilter !== "all" && row.Timeframe !== timeframeFilter) {
        match = false;
      }

      // Apply confidence filter
      if (
        confidenceFilter !== "all" &&
        row.Confidence_Level !== confidenceFilter
      ) {
        match = false;
      }

      // Apply source filter
      if (sourceFilter !== "all" && row.Content_Source !== sourceFilter) {
        match = false;
      }

      // Apply search query filter
      if (searchQuery) {
        const searchLower = searchQuery.toLowerCase();
        const searchableFields = [
          row.Token,
          row.Event_Type,
          row.Forecast,
          row.Title,
          row.Description,
          row.Event_Description, // Keep for backward compatibility
          row.Price_Level,
          row.Price_Type,
          row.Pattern,
          row.Timeframe,
          row.Content_Source,
          row.Confidence_Level,
        ];

        const hasMatch = searchableFields.some(
          (field) => field && field.toString().toLowerCase().includes(searchLower)
        );

        if (!hasMatch) {
          match = false;
        }
      }

      return match;
    });
  };

  // Apply filters when filter values change
  useEffect(() => {
    setFilteredData(applyFilters(data));
  }, [tokenFilter, timeframeFilter, confidenceFilter, sourceFilter, data, searchQuery]);

  // Get unique tokens for the filter dropdown
  const uniqueTokens = [...new Set(data.map((item) => item.Token))].sort();
  const uniqueSources = [...new Set(data.map((item) => item.Content_Source))].sort();
  const uniqueTimeframes = [...new Set(data.map((item) => item.Timeframe))].sort();
  const uniqueConfidence = [...new Set(data.map((item) => item.Confidence_Level))].sort();

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-center h-[60vh]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-lg">Loading dashboard data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-destructive/10 p-6 rounded-lg text-center">
          <h2 className="text-xl font-bold text-destructive mb-2">Error</h2>
          <p>{error}</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => window.location.reload()}
          >
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  // Debug info
  if (data.length === 0 && !isLoading) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-6 rounded-lg">
          <h2 className="text-xl font-bold mb-4">No Data Found</h2>
          <p className="mb-4">The dashboard received no data to display.</p>
          <div className="space-y-2 text-sm">
            <p><strong>Analysis ID:</strong> {analysisId || "Not provided"}</p>
            <p><strong>CSV Data provided:</strong> {csvData ? "Yes" : "No"}</p>
            <p><strong>CSV Data length:</strong> {csvData?.length || 0} characters</p>
            <p><strong>Parsed rows:</strong> {data.length}</p>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            Check the browser console for detailed debugging information.
          </p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => window.location.reload()}
          >
            Reload
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 pt-4 pb-0 h-full flex flex-col">
      <div className="flex flex-col flex-1 min-h-0">
        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4 flex-shrink-0">
          <Select value={tokenFilter} onValueChange={setTokenFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Select Token" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Tokens</SelectItem>
              {uniqueTokens.map((token) => (
                <SelectItem key={token} value={token}>
                  {token}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={timeframeFilter} onValueChange={setTimeframeFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Select Timeframe" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Timeframes</SelectItem>
              {uniqueTimeframes.map((timeframe) => (
                <SelectItem key={timeframe} value={timeframe}>
                  {timeframe}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={confidenceFilter}
            onValueChange={setConfidenceFilter}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select Confidence" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Confidence Levels</SelectItem>
              {uniqueConfidence.map((confidence) => (
                <SelectItem key={confidence} value={confidence}>
                  {confidence}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={sourceFilter} onValueChange={setSourceFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Select Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              {uniqueSources.map((source) => (
                <SelectItem key={source} value={source}>
                  {source}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>

        <div className="flex-1 min-h-0 flex flex-col">
          <Tabs defaultValue="price-targets" className="w-full flex flex-col flex-1 min-h-0">
            <TabsList className="grid w-full grid-cols-5 mb-4 flex-shrink-0">
              <TabsTrigger value="price-targets">Price Targets</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="charts">Charts</TabsTrigger>
              <TabsTrigger value="data">Raw Data</TabsTrigger>
              <TabsTrigger value="tracking">Tracking</TabsTrigger>
            </TabsList>

            <TabsContent value="price-targets" className="flex-1 overflow-y-auto">
              <Card>
                <CardHeader>
                  <CardTitle>Price Targets & Projections</CardTitle>
                </CardHeader>
                <CardContent>
                  <PriceTargets data={filteredData} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="timeline" className="flex-1 overflow-y-auto">
              <Card>
                <CardHeader>
                  <CardTitle>Event Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                  <EventTimeline data={filteredData} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="charts" className="flex-1 overflow-y-auto">
              <DashboardCharts data={filteredData} />
            </TabsContent>

            <TabsContent value="data" className="flex-1 overflow-y-auto">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Data Table</CardTitle>
                    <button
                      onClick={() => setIsFullscreenOpen(true)}
                      className="p-2 rounded-md hover:bg-muted transition-colors"
                      title="Open in fullscreen"
                    >
                      <Maximize2 className="h-5 w-5" />
                    </button>
                  </div>
                </CardHeader>
                <CardContent>
                  <DataTable data={filteredData} analysisId={analysisId} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="tracking" className="flex-1 min-h-0 pb-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
                {/* Tracking Modules - 2/3 width */}
                <div className="lg:col-span-2 flex flex-col h-full min-h-0">
                  <div className="flex-1 overflow-y-auto space-y-4 pr-2 pb-4">
                    <PolymarketTracking />
                    <ComingSoonModules />
                  </div>
                </div>
                
                {/* Chat Module - 1/3 width */}
                <div className="lg:col-span-1 h-full min-h-0 pb-4">
                  <TrackingChat />
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Fullscreen Data Table Dialog */}
        <Dialog open={isFullscreenOpen} onOpenChange={setIsFullscreenOpen}>
          <DialogContent className="max-w-[98vw] max-h-[98vh] w-[98vw] h-[98vh] p-6 flex flex-col">
            <DialogHeader className="flex-shrink-0">
              <DialogTitle>Data Table</DialogTitle>
            </DialogHeader>
            <div className="flex-1 overflow-auto min-h-0">
              <DataTable data={filteredData} hideExport={true} analysisId={analysisId} />
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

