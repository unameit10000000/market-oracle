"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Send, Bot, User, Sparkles } from "lucide-react";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

// Dummy data for the chat
const dummyMessages: ChatMessage[] = [
  {
    id: "1",
    role: "assistant",
    content: "Welcome! I can help you analyze market data and provide insights about your tracking modules.",
    timestamp: "10:30 AM",
  },
  {
    id: "2",
    role: "user",
    content: "What can you tell me about the current market trends?",
    timestamp: "10:31 AM",
  },
  {
    id: "3",
    role: "assistant",
    content: "Based on the current tracking data, I can see several key indicators. The market shows strong volatility patterns, with significant price movements in the tracked assets. Would you like me to dive deeper into any specific metric?",
    timestamp: "10:31 AM",
  },
  {
    id: "4",
    role: "user",
    content: "Show me insights about the Polymarket data",
    timestamp: "10:32 AM",
  },
  {
    id: "5",
    role: "assistant",
    content: "The Polymarket tracking module shows active markets with varying probabilities. Key observations include high-volume trading in certain price ranges and notable probability shifts in the last 24 hours. The countdown timers indicate upcoming resolution events that may impact market dynamics.",
    timestamp: "10:32 AM",
  },
];

export default function TrackingChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(dummyMessages);
  const [inputValue, setInputValue] = useState("");

  const handleSend = () => {
    if (!inputValue.trim()) return;

    const newUserMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue,
      timestamp: new Date().toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    // Add user message
    setMessages((prev) => [...prev, newUserMessage]);

    // Simulate assistant response
    setTimeout(() => {
      const assistantResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "This is a template response. Backend integration will be implemented soon to provide real-time insights about your tracking data.",
        timestamp: new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setMessages((prev) => [...prev, assistantResponse]);
    }, 500);

    setInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0 border-b">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI Assistant
            </CardTitle>
            <CardDescription className="mt-1">
              Get insights about your tracking modules
            </CardDescription>
          </div>
          <Badge variant="secondary" className="bg-primary/10 text-primary">
            Beta
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 min-h-0">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
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
                <p
                  className={`text-xs mt-1 ${
                    message.role === "user"
                      ? "text-primary-foreground/70"
                      : "text-muted-foreground"
                  }`}
                >
                  {message.timestamp}
                </p>
              </div>
              {message.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-4 w-4 text-primary" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="flex-shrink-0 border-t p-4">
          <div className="flex gap-2">
            <Input
              placeholder="Ask about your tracking data..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1"
            />
            <Button onClick={handleSend} disabled={!inputValue.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Template UI - Backend integration coming soon
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

