"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Send, Bot, User, Sparkles, AlertTriangle, X, Trash2, Square } from "lucide-react";
import { marketOracleApi } from "@/lib/api/market-oracle";
import {
  saveAiResponseToCookie,
  loadChatHistoryFromCookies,
  clearSessionCookies,
  type ChatMessage,
} from "@/lib/utils";

interface TrackingChatProps {
  analysisId?: string;
  trackingEnabled?: boolean;
  onTrackingEnabledChange?: (enabled: boolean) => void;
  onAutoModeData?: (data: any) => void;
  polymarketConfig?: { url?: string; slug?: string } | null;
}

export default function TrackingChat({
  analysisId,
  trackingEnabled: externalTrackingEnabled,
  onTrackingEnabledChange,
  onAutoModeData,
  polymarketConfig,
}: TrackingChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [enableThinking, setEnableThinking] = useState(false);
  const [thinkingInterval, setThinkingInterval] = useState<string | null>(null);
  const [isThinkingActive, setIsThinkingActive] = useState(false);
  const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null);
  const [showStartDialog, setShowStartDialog] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const autoModeIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load chat history from cookies on mount
  useEffect(() => {
    if (analysisId) {
      const history = loadChatHistoryFromCookies(analysisId);
      if (history.length > 0) {
        setMessages(history);
      } else {
        // Show welcome message if no history
        setMessages([
          {
            role: "assistant",
            content: "Welcome! I can help you analyze market data and provide insights about our enabled tracking modules.",
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    }
  }, [analysisId]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (autoModeIntervalRef.current) {
        clearInterval(autoModeIntervalRef.current);
      }
    };
  }, []);

  // Get interval in milliseconds
  const getIntervalMs = (interval: string): number => {
    const map: Record<string, number> = {
      "5m": 300000,
      "15m": 900000,
      "30m": 1800000,
      "1h": 3600000,
      "4h": 14400000,
    };
    return map[interval] || 900000;
  };

  // Start auto mode
  const startAutoMode = async () => {
    if (!analysisId || !thinkingInterval) return;

    setIsLoading(true);
    setError(null);

    try {
      // Get enabled modules (polymarket if we have config)
      const enabledModules = polymarketConfig ? ["polymarket"] : [];

      // Load chat history
      const chatHistory = loadChatHistoryFromCookies(analysisId);

      // Call start-thinking endpoint
      await marketOracleApi.startThinking({
        interval: thinkingInterval,
        enabled_modules: enabledModules,
        analysis_id: analysisId,
        chat_history: chatHistory,
      });

      // Set up interval
      const intervalMs = getIntervalMs(thinkingInterval);
      setIsThinkingActive(true);
      if (onTrackingEnabledChange) {
        onTrackingEnabledChange(true);
      }

      // Perform initial fetch
      await performAutoFetch();

      // Set up recurring interval
      autoModeIntervalRef.current = setInterval(async () => {
        await performAutoFetch();
      }, intervalMs);

      setShowStartDialog(false);
    } catch (err) {
      console.error("Error starting auto mode:", err);
      setError(err instanceof Error ? err.message : "Failed to start auto mode");
    } finally {
      setIsLoading(false);
    }
  };

  // Stop auto mode
  const stopAutoMode = async () => {
    if (!analysisId) return;

    try {
      // Clear interval
      if (autoModeIntervalRef.current) {
        clearInterval(autoModeIntervalRef.current);
        autoModeIntervalRef.current = null;
      }

      // Call stop-thinking endpoint
      await marketOracleApi.stopThinking(analysisId);

      setIsThinkingActive(false);
      if (onTrackingEnabledChange) {
        onTrackingEnabledChange(false);
      }
    } catch (err) {
      console.error("Error stopping auto mode:", err);
      setError(err instanceof Error ? err.message : "Failed to stop auto mode");
    }
  };

  // Perform auto fetch
  const performAutoFetch = async () => {
    if (!analysisId) return;

    try {
      const enabledModules = polymarketConfig ? ["polymarket"] : [];

      const chatHistory = loadChatHistoryFromCookies(analysisId);

      const response = await marketOracleApi.fetchAnalysis({
        analysis_id: analysisId,
        enabled_modules: enabledModules,
        chat_history: chatHistory,
        polymarket_config: polymarketConfig || undefined,
      });

      // Update chat with AI response
      const aiMessage: ChatMessage = {
        role: "assistant",
        content: response.ai_response.content,
        timestamp: response.ai_response.timestamp,
      };

      setMessages((prev) => [...prev, aiMessage]);
      saveAiResponseToCookie(aiMessage, analysisId);
      setLastFetchTime(new Date());

      // Update module data if provided
      if (response.polymarket_response && onAutoModeData) {
        onAutoModeData(response.polymarket_response);
      }
    } catch (err) {
      console.error("Error performing auto fetch:", err);
      // Don't stop auto mode on error, just log it
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: `Error fetching analysis: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  // Handle manual chat send
  const handleSend = async () => {
    if (!inputValue.trim() || !analysisId || isThinkingActive) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setError(null);

    try {
      const chatHistory = loadChatHistoryFromCookies(analysisId);
      const enabledModules = polymarketConfig ? ["polymarket"] : [];

      const response = await marketOracleApi.sendChatMessage({
        analysis_id: analysisId,
        message: inputValue,
        chat_history: chatHistory,
        enabled_modules: enabledModules,
        polymarket_data: undefined, // Could be passed from parent if available
      });

      const aiMessage: ChatMessage = {
        role: "assistant",
        content: response.ai_response.content,
        timestamp: response.ai_response.timestamp,
      };

      setMessages((prev) => [...prev, aiMessage]);
      saveAiResponseToCookie(userMessage, analysisId);
      saveAiResponseToCookie(aiMessage, analysisId);
    } catch (err) {
      console.error("Error sending chat message:", err);
      setError(err instanceof Error ? err.message : "Failed to send message");
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Failed to get response"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Clear session
  const handleClearSession = () => {
    if (!analysisId) return;
    clearSessionCookies(analysisId);
    setMessages([
      {
        role: "assistant",
        content: "Session cleared. How can I help you?",
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  // Format time for display
  const formatTime = (date: Date | null): string => {
    if (!date) return "";
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Format interval for display
  const formatInterval = (interval: string | null): string => {
    if (!interval) return "";
    const map: Record<string, string> = {
      "5m": "5 minutes",
      "15m": "15 minutes",
      "30m": "30 minutes",
      "1h": "1 hour",
      "4h": "4 hours",
    };
    return map[interval] || interval;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Sync external tracking enabled state
  useEffect(() => {
    if (externalTrackingEnabled !== undefined && externalTrackingEnabled !== isThinkingActive) {
      if (externalTrackingEnabled && !isThinkingActive && thinkingInterval) {
        // External wants to enable, but we're not active - start if we have interval
        startAutoMode();
      } else if (!externalTrackingEnabled && isThinkingActive) {
        // External wants to disable
        stopAutoMode();
      }
    }
  }, [externalTrackingEnabled]);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0 border-b">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI Tracking
            </CardTitle>
            <CardDescription className="mt-1">
              Get insights about our enabled tracking modules
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {isThinkingActive && (
              <Badge variant="default" className="bg-primary/10 text-primary">
                Auto: {formatInterval(thinkingInterval)}
              </Badge>
            )}
            <Badge variant="secondary" className="bg-primary/10 text-primary">
              Beta
            </Badge>
          </div>
        </div>

        {/* Enable Thinking Toggle */}
        <div className="mt-4 flex items-center gap-2">
          <input
            type="checkbox"
            id="enable-thinking"
            checked={enableThinking}
            onChange={(e) => {
              setEnableThinking(e.target.checked);
              if (!e.target.checked) {
                // If disabling, stop auto mode
                if (isThinkingActive) {
                  stopAutoMode();
                }
                setThinkingInterval(null);
              }
            }}
            disabled={isThinkingActive}
            className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary disabled:opacity-50"
          />
          <label htmlFor="enable-thinking" className="text-sm font-medium cursor-pointer">
            Enable Thinking
          </label>
        </div>

        {/* Interval Selection (only visible when enableThinking is checked) */}
        {enableThinking && (
          <div className="mt-3 space-y-2">
            <label className="text-sm font-medium">Thinking Interval:</label>
            <div className="flex flex-wrap gap-2">
              {["5m", "15m", "30m", "1h", "4h"].map((interval) => (
                <button
                  key={interval}
                  onClick={() => setThinkingInterval(interval)}
                  disabled={isThinkingActive}
                  className={`px-3 py-1 text-sm rounded-md border transition-colors ${
                    thinkingInterval === interval
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background border-border hover:bg-muted"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {formatInterval(interval)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Start Thinking Button (only visible when interval is selected) */}
        {enableThinking && thinkingInterval && !isThinkingActive && (
          <div className="mt-3">
            <Button
              onClick={() => setShowStartDialog(true)}
              disabled={!analysisId}
              className="w-full"
            >
              Start Thinking
            </Button>
          </div>
        )}

        {/* Auto Mode Indicators */}
        {isThinkingActive && (
          <div className="mt-3 space-y-2">
            {lastFetchTime && (
              <p className="text-xs text-muted-foreground">
                Last updated: {formatTime(lastFetchTime)}
              </p>
            )}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={stopAutoMode}
                className="flex-1"
              >
                <Square className="h-4 w-4 mr-2" />
                Stop
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearSession}
                className="flex-1"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Clear Session
              </Button>
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 min-h-0">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {message.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                {message.timestamp && (
                  <p
                    className={`text-xs mt-1 ${
                      message.role === "user"
                        ? "text-primary-foreground/70"
                        : "text-muted-foreground"
                    }`}
                  >
                    {new Date(message.timestamp).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                )}
              </div>
              {message.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-4 w-4 text-primary" />
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary animate-pulse" />
              </div>
              <div className="bg-muted rounded-lg px-4 py-2">
                <p className="text-sm text-muted-foreground">Thinking...</p>
              </div>
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
            {error}
          </div>
        )}

        {/* Input Area */}
        <div className="flex-shrink-0 border-t p-4">
          <div className="flex gap-2">
            <Input
              placeholder={
                isThinkingActive
                  ? "Auto mode active - chat disabled"
                  : "Ask about your tracking data..."
              }
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1"
              disabled={isThinkingActive || isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={!inputValue.trim() || isThinkingActive || isLoading}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>

      {/* Start Thinking Confirmation Dialog */}
      <Dialog open={showStartDialog} onOpenChange={setShowStartDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Start Auto Thinking?
            </DialogTitle>
            <DialogDescription>
              This will start automated thinking that fetches data and generates AI insights at regular intervals.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                ⚠️ API Cost Warning
              </p>
              <p className="text-sm text-yellow-700 dark:text-yellow-300">
                Each automated fetch uses AI API (OpenRouter or Anthropic) and costs money.
                The system will fetch data every {formatInterval(thinkingInterval)} automatically.
                Make sure you understand the costs before proceeding.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowStartDialog(false)}>
              Abort
            </Button>
            <Button onClick={startAutoMode} disabled={isLoading}>
              {isLoading ? "Starting..." : "Start"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
