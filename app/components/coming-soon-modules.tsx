"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, Zap, TrendingUp, BarChart3 } from "lucide-react";

export default function ComingSoonModules() {
  const modules = [
    {
      id: "1",
      name: "Price Alerts",
      description: "Set up automated alerts for price movements and market events",
      icon: Zap,
      status: "In Development",
    },
    {
      id: "2",
      name: "Market Sentiment",
      description: "Track social media sentiment and market indicators",
      icon: TrendingUp,
      status: "Planned",
    },
    {
      id: "3",
      name: "Advanced Analytics",
      description: "Deep dive into market trends with advanced charting tools",
      icon: BarChart3,
      status: "Planned",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-muted-foreground" />
              Other Modules
            </CardTitle>
            <CardDescription className="mt-1">
              Additional tracking modules coming soon
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {modules.map((module) => {
            const Icon = module.icon;
            return (
              <div
                key={module.id}
                className="flex items-start gap-4 p-4 border rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
              >
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-sm">{module.name}</h3>
                    <Badge variant="secondary" className="text-xs">
                      {module.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {module.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

