"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import MarketDashboard from "@/components/market-dashboard";
import { ThemeToggle } from "@/components/theme-toggle";

export default function DashboardPage() {
  const searchParams = useSearchParams();
  const analysisId = searchParams.get("analysisId");
  const [csvData, setCsvData] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (analysisId) {
      // Try to get CSV data from sessionStorage first
      const storedData = sessionStorage.getItem(`analysis_${analysisId}`);
      if (storedData) {
        setCsvData(storedData);
      }
      // If not in sessionStorage, the MarketDashboard component will fetch it using the analysisId
    }
  }, [analysisId]);

  return (
    <main className="min-h-screen bg-background pt-4">
      <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>
      <MarketDashboard
        csvData={csvData}
        analysisId={analysisId || undefined}
      />
    </main>
  );
}

