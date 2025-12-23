"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader2, XCircle, CheckCircle2, ExternalLink, AlertTriangle } from "lucide-react";
import { marketOracleApi } from "@/lib/api/market-oracle";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface PolymarketMarket {
  id: string;
  question?: string;
  groupItemTitle?: string;  // Price range label (e.g., "<78,000", "86,000-88,000")
  details: {
    active: boolean;
    closed: boolean;
    outcomes: string;
    outcomePrices: string;
    volume: string;
  };
}

interface PolymarketMarketsResponse {
  status: string;
  event_slug: string;
  endDate?: string;  // Event resolution time (ISO 8601 format)
  markets_count: number;
  markets: PolymarketMarket[];
  error?: string;
}

export default function PolymarketTracking() {
  const [enabled, setEnabled] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [inputType, setInputType] = useState<"url" | "slug">("url");
  const [isLoading, setIsLoading] = useState(false);
  const [marketsData, setMarketsData] = useState<PolymarketMarketsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showKeysDialog, setShowKeysDialog] = useState(false);
  const [isCheckingKeys, setIsCheckingKeys] = useState(false);
  const [timezone, setTimezone] = useState<string>(Intl.DateTimeFormat().resolvedOptions().timeZone);
  const [timeRemaining, setTimeRemaining] = useState<{ hours: number; minutes: number; seconds: number } | null>(null);
  const [currentTime, setCurrentTime] = useState<string>("");

  const handleToggle = async () => {
    // If enabling, check for API keys first
    if (!enabled) {
      setIsCheckingKeys(true);
      try {
        const keysResponse = await marketOracleApi.checkPolymarketKeys();
        
        if (!keysResponse.keys_configured) {
          // Show dialog if keys are not configured
          setShowKeysDialog(true);
          setIsCheckingKeys(false);
          return; // Don't enable yet, wait for user decision
        }
      } catch (err) {
        console.error("Failed to check API keys:", err);
        // On error, assume keys might be missing and show dialog
        setShowKeysDialog(true);
        setIsCheckingKeys(false);
        return;
      } finally {
        setIsCheckingKeys(false);
      }
    }
    
    // If disabling or keys are configured, proceed with toggle
    setEnabled(!enabled);
    if (!enabled) {
      // Reset state when enabling
      setMarketsData(null);
      setError(null);
    }
  };

  const handleDialogContinue = () => {
    setShowKeysDialog(false);
    setEnabled(true);
    // Reset state when enabling
    setMarketsData(null);
    setError(null);
  };

  const handleDialogAbort = () => {
    setShowKeysDialog(false);
    // Keep enabled as false (checkbox will remain unchecked)
    setEnabled(false);
  };

  const handleFetchMarkets = async () => {
    if (!inputValue.trim()) {
      setError("Please enter a Polymarket URL or event slug");
      return;
    }

    setIsLoading(true);
    setError(null);
    setMarketsData(null);

    try {
      const options = inputType === "url" 
        ? { url: inputValue.trim() }
        : { slug: inputValue.trim() };

      const response = await marketOracleApi.getPolymarketMarkets(options);

      if (response.status === "success") {
        if (response.markets && response.markets.length > 0) {
          setMarketsData(response);
        } else {
          setError("No markets found for this event. The event may not have any markets available.");
        }
      } else {
        const errorMsg = response.error || "No Polymarket data available. Please check your URL or slug and try again.";
        setError(errorMsg);
      }
    } catch (err) {
      console.error("Failed to fetch Polymarket markets:", err);
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(`Failed to fetch Polymarket data: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const parseOutcomes = (outcomesStr: string): string[] => {
    try {
      return JSON.parse(outcomesStr);
    } catch {
      return [];
    }
  };

  const parsePrices = (pricesStr: string): number[] => {
    try {
      return JSON.parse(pricesStr).map((p: string) => parseFloat(p));
    } catch {
      return [];
    }
  };

  const formatVolume = (volume: string): string => {
    const num = parseFloat(volume);
    if (num >= 1000000) {
      return `$${(num / 1000000).toFixed(2)}M`;
    } else if (num >= 1000) {
      return `$${(num / 1000).toFixed(2)}K`;
    }
    return `$${num.toFixed(2)}`;
  };

  // Countdown timer effect
  useEffect(() => {
    if (!marketsData?.endDate) {
      setTimeRemaining(null);
      return;
    }

    const updateCountdown = () => {
      try {
        const endDate = new Date(marketsData.endDate!);
        const now = new Date();
        const diff = endDate.getTime() - now.getTime();

        if (diff <= 0) {
          setTimeRemaining({ hours: 0, minutes: 0, seconds: 0 });
          return;
        }

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        setTimeRemaining({ hours, minutes, seconds });

        // Update current time display
        const formatter = new Intl.DateTimeFormat('en-US', {
          timeZone: timezone,
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: true,
        });
        setCurrentTime(formatter.format(now));
      } catch (err) {
        console.error("Error calculating countdown:", err);
        setTimeRemaining(null);
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);

    return () => clearInterval(interval);
  }, [marketsData?.endDate, timezone]);

  const extractOutcomeLabel = (question: string | undefined): string => {
    if (!question) return "Unknown";
    
    // Try to extract price range from question (fallback if groupItemTitle is not available)
    // Examples:
    // "Will the price of Bitcoin be between $86,000 and $88,000 on December 22?" -> "86,000-88,000"
    // "Will the price of Bitcoin be < $78,000 on December 23?" -> "<78,000"
    // "Will the price of Bitcoin be > $96,000 on December 23?" -> ">96,000"
    
    // Match patterns like "between $86,000 and $88,000"
    const betweenMatch = question.match(/between\s+\$?([\d,]+)\s+and\s+\$?([\d,]+)/i);
    if (betweenMatch) {
      return `${betweenMatch[1]}-${betweenMatch[2]}`;
    }
    
    // Match patterns like "< $78,000" or "less than $78,000"
    const lessThanMatch = question.match(/[<]|less than\s+\$?([\d,]+)/i);
    if (lessThanMatch && lessThanMatch[1]) {
      return `<${lessThanMatch[1]}`;
    }
    
    // Match patterns like "> $96,000" or "greater than $96,000"
    const greaterThanMatch = question.match(/[>]|greater than\s+\$?([\d,]+)/i);
    if (greaterThanMatch && greaterThanMatch[1]) {
      return `>${greaterThanMatch[1]}`;
    }
    
    // Fallback: return first part of question or a shortened version
    const shortQuestion = question.length > 50 ? question.substring(0, 50) + "..." : question;
    return shortQuestion;
  };

  return (
    <div className="space-y-4">
      {/* Enable/Disable Toggle */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Polymarket Tracking</CardTitle>
              <CardDescription>
                Track real-time Polymarket event data and market probabilities
              </CardDescription>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={enabled}
                onChange={handleToggle}
                disabled={isCheckingKeys}
                className="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <span className="text-sm font-medium">
                {isCheckingKeys ? (
                  <>
                    <Loader2 className="inline h-4 w-4 animate-spin mr-1" />
                    Checking...
                  </>
                ) : enabled ? (
                  "Enabled"
                ) : (
                  "Disabled"
                )}
              </span>
            </label>
          </div>
        </CardHeader>

        {enabled && (
          <CardContent className="space-y-4">
            {/* Configuration Input */}
            <div className="space-y-2">
              <div className="flex gap-2">
                <select
                  value={inputType}
                  onChange={(e) => setInputType(e.target.value as "url" | "slug")}
                  className="px-3 py-2 border rounded-md bg-background"
                >
                  <option value="url">URL</option>
                  <option value="slug">Event Slug</option>
                </select>
                <Input
                  placeholder={
                    inputType === "url"
                      ? "https://polymarket.com/event/..."
                      : "event-slug"
                  }
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleFetchMarkets()}
                  className="flex-1"
                />
                <Button
                  onClick={handleFetchMarkets}
                  disabled={isLoading || !inputValue.trim()}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading
                    </>
                  ) : (
                    "Fetch Markets"
                  )}
                </Button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Markets List */}
            {marketsData && marketsData.markets && marketsData.markets.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold">Markets</h3>
                    <p className="text-sm text-muted-foreground">
                      Event: <span className="font-mono">{marketsData.event_slug}</span>
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Total Markets: {marketsData.markets_count}
                    </p>
                  </div>
                  
                  {/* Countdown Timer */}
                  {marketsData.endDate && timeRemaining !== null && (
                    <div className="flex flex-col items-end gap-2">
                      <Select value={timezone} onValueChange={setTimezone}>
                        <SelectTrigger className="w-[200px]">
                          <SelectValue placeholder="Select timezone" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="America/New_York">Eastern Time (ET)</SelectItem>
                          <SelectItem value="America/Chicago">Central Time (CT)</SelectItem>
                          <SelectItem value="America/Denver">Mountain Time (MT)</SelectItem>
                          <SelectItem value="America/Los_Angeles">Pacific Time (PT)</SelectItem>
                          <SelectItem value="Europe/London">London (GMT)</SelectItem>
                          <SelectItem value="Europe/Paris">Paris (CET)</SelectItem>
                          <SelectItem value="Asia/Tokyo">Tokyo (JST)</SelectItem>
                          <SelectItem value="Asia/Shanghai">Shanghai (CST)</SelectItem>
                          <SelectItem value="UTC">UTC</SelectItem>
                          <SelectItem value={Intl.DateTimeFormat().resolvedOptions().timeZone}>
                            Local Time
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      
                      <div className="text-right">
                        <div className="flex items-end justify-end gap-4">
                          <div className="text-center">
                            <div className="text-3xl font-bold text-red-600 dark:text-red-500 leading-none">
                              {String(timeRemaining.hours).padStart(2, '0')}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">HRS</div>
                          </div>
                          <div className="text-center">
                            <div className="text-3xl font-bold text-red-600 dark:text-red-500 leading-none">
                              {String(timeRemaining.minutes).padStart(2, '0')}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">MNS</div>
                          </div>
                          <div className="text-center">
                            <div className="text-3xl font-bold text-red-600 dark:text-red-500 leading-none">
                              {String(timeRemaining.seconds).padStart(2, '0')}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">SECS</div>
                          </div>
                        </div>
                        {currentTime && (
                          <p className="text-xs text-muted-foreground mt-2">
                            Current Time ({timezone}): {currentTime}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {marketsData.markets.map((market) => {
                    const outcomes = parseOutcomes(market.details.outcomes);
                    const prices = parsePrices(market.details.outcomePrices);
                    const isResolved = market.details.closed;
                    
                    // Find the index of "Yes" outcome (case-insensitive)
                    const yesIndex = outcomes.findIndex((outcome: string) => 
                      outcome.toLowerCase() === "yes"
                    );
                    const noIndex = outcomes.findIndex((outcome: string) => 
                      outcome.toLowerCase() === "no"
                    );
                    
                    // Get prices - use index if found, otherwise fallback to first/second
                    const yesPrice = yesIndex >= 0 && prices[yesIndex] !== undefined 
                      ? prices[yesIndex] 
                      : prices[0] ?? 0;
                    const noPrice = noIndex >= 0 && prices[noIndex] !== undefined 
                      ? prices[noIndex] 
                      : prices[1] ?? 0;
                    
                    // Calculate chance percentage (Yes outcome probability)
                    // Match Polymarket's display format exactly:
                    // - For values >= 1%: round to nearest whole number
                    // - For values < 1%: show as "<1%" or with 1 decimal if needed
                    const chancePercentValue = yesPrice * 100;
                    let chancePercent: string;
                    if (chancePercentValue < 1) {
                      chancePercent = chancePercentValue < 0.1 ? "<1" : chancePercentValue.toFixed(1);
                    } else {
                      // Round to nearest whole number
                      chancePercent = Math.round(chancePercentValue).toString();
                    }
                    
                    // Calculate buy prices in cents
                    // Polymarket shows buy prices with 1 decimal for values < 10¢, whole numbers for >= 10¢
                    const buyYesCentsValue = yesPrice * 100;
                    const buyNoCentsValue = noPrice * 100;
                    const buyYesCents = buyYesCentsValue < 10 
                      ? buyYesCentsValue.toFixed(1)
                      : Math.round(buyYesCentsValue).toString();
                    const buyNoCents = buyNoCentsValue < 10 
                      ? buyNoCentsValue.toFixed(1)
                      : Math.round(buyNoCentsValue).toString();
                    
                    // Get price label (prefer groupItemTitle, fallback to extracted from question)
                    const priceLabel = market.groupItemTitle || extractOutcomeLabel(market.question);

                    return (
                      <Card key={market.id} className="border-l-4 border-l-primary">
                        <CardContent className="pt-4">
                          <div className="grid grid-cols-3 gap-4">
                            {/* Column 1: ID, Status, Price, Volume */}
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-sm font-mono text-muted-foreground">
                                  ID: {market.id}
                                </span>
                                <Badge
                                  variant={market.details.active ? "default" : "secondary"}
                                  className="text-xs"
                                >
                                  {market.details.active ? "Active" : "Inactive"}
                                </Badge>
                                <Badge
                                  variant={isResolved ? "destructive" : "outline"}
                                  className="text-xs"
                                >
                                  {isResolved ? "Resolved" : "Open"}
                                </Badge>
                              </div>
                              
                              <div className="pt-1">
                                <span className="text-sm font-semibold">
                                  Price: {priceLabel}
                                </span>
                              </div>
                              
                              <div className="pt-1">
                                <span className="text-sm text-muted-foreground">
                                  Volume:{" "}
                                  <span className="font-semibold">
                                    {formatVolume(market.details.volume)}
                                  </span>
                                </span>
                              </div>
                            </div>

                            {/* Column 2: Chance Percentage */}
                            <div className="flex items-center justify-center">
                              <div className="text-center">
                                <div className="text-2xl font-bold">
                                  {chancePercent}%
                                </div>
                                <div className="text-xs text-muted-foreground mt-1">
                                  Chance
                                </div>
                                <div className="w-32 h-2 bg-secondary rounded-full overflow-hidden mt-2 mx-auto">
                                  <div
                                    className="h-full bg-primary transition-all"
                                    style={{ width: `${chancePercent}%` }}
                                  />
                                </div>
                              </div>
                            </div>

                            {/* Column 3: Buy Yes/No Prices */}
                            <div className="flex flex-col justify-center space-y-2">
                              <div className="flex items-center justify-between p-2 bg-teal-500/10 border-2 border-teal-500 rounded-md">
                                <span className="text-sm font-medium text-teal-600 dark:text-teal-400">Buy Yes:</span>
                                <span className="text-sm font-semibold text-teal-600 dark:text-teal-400">{buyYesCents}¢</span>
                              </div>
                              <div className="flex items-center justify-between p-2 bg-red-500/10 border-2 border-red-500 rounded-md">
                                <span className="text-sm font-medium text-red-600 dark:text-red-400">Buy No:</span>
                                <span className="text-sm font-semibold text-red-600 dark:text-red-400">{buyNoCents}¢</span>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!isLoading && !error && !marketsData && (
              <Alert>
                <AlertDescription>
                  Enter a Polymarket URL or event slug above and click "Fetch Markets" to load market data.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        )}

        {!enabled && (
          <CardContent>
            <Alert>
              <AlertDescription>
                Enable Polymarket tracking to view real-time market data and probabilities.
              </AlertDescription>
            </Alert>
          </CardContent>
        )}
      </Card>

      {/* API Keys Warning Dialog */}
      <Dialog open={showKeysDialog} onOpenChange={(open) => {
        if (!open) {
          // If dialog is closed (X button or outside click), abort
          handleDialogAbort();
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Important Notice
            </DialogTitle>
            <DialogDescription>
              Polymarket API keys are not configured in your environment.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Alert variant="default" className="bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
              <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
              <AlertTitle className="text-yellow-800 dark:text-yellow-200">
                API Keys are not configured!
              </AlertTitle>
              <AlertDescription className="text-yellow-700 dark:text-yellow-300 mt-2">
                Add Polymarket relevant keys to access enhanced features.
              </AlertDescription>
            </Alert>
            <p className="mt-4 text-sm text-muted-foreground">
              Would you like to continue without API keys? You can still access public market data,
              but some features may be limited.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleDialogAbort}>
              Abort
            </Button>
            <Button onClick={handleDialogContinue}>
              Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

