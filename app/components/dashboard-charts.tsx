"use client"

import { useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import Chart from "chart.js/auto"
import { cleanPrice } from "@/lib/data-utils"

interface DashboardChartsProps {
  data: any[]
}

export default function DashboardCharts({ data }: DashboardChartsProps) {
  const tokenDistributionRef = useRef<HTMLCanvasElement>(null)
  const eventTypesRef = useRef<HTMLCanvasElement>(null)
  const confidenceLevelRef = useRef<HTMLCanvasElement>(null)

  const chartRefs = useRef<{ [key: string]: Chart | null }>({
    tokenDistribution: null,
    eventTypes: null,
    confidenceLevel: null,
  })

  useEffect(() => {
    // Define custom gradient colors
    const gradientColors = [
      "rgba(22, 163, 74, 0.8)", // Vibrant Green (primary)
      "rgba(14, 165, 233, 0.8)", // Azure Blue
      "rgba(20, 184, 166, 0.8)", // Teal
      "rgba(132, 204, 22, 0.8)", // Lime Green
      "rgba(253, 187, 65, 0.8)", // Yellow
    ]

    // Destroy previous charts
    Object.values(chartRefs.current).forEach((chart) => {
      if (chart) chart.destroy()
    })

    // Create token distribution chart
    if (tokenDistributionRef.current) {
      const ctx = tokenDistributionRef.current.getContext("2d")
      if (ctx) {
        // Count tokens
        const tokenCounts: { [key: string]: number } = {}
        data.forEach((row) => {
          tokenCounts[row.Token] = (tokenCounts[row.Token] || 0) + 1
        })

        chartRefs.current.tokenDistribution = new Chart(ctx, {
          type: "bar",
          data: {
            labels: Object.keys(tokenCounts),
            datasets: [
              {
                label: "Number of Data Points",
                data: Object.values(tokenCounts),
                backgroundColor: Object.keys(tokenCounts).map((_, i) => gradientColors[i % gradientColors.length]),
                borderWidth: 1,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
              },
            },
          },
        })
      }
    }

    // Create event types chart
    if (eventTypesRef.current) {
      const ctx = eventTypesRef.current.getContext("2d")
      if (ctx) {
        // Get all event types
        const eventTypes = [...new Set(data.map((d) => d.Event_Type))]

        // Get all tokens
        const tokens = [...new Set(data.map((d) => d.Token))]

        // Prepare datasets
        const datasets: any = []

        // For each token, count how many events of each type
        tokens.forEach((token, index) => {
          const tokenData = data.filter((d) => d.Token === token)
          const counts = eventTypes.map((type) => tokenData.filter((d) => d.Event_Type === type).length)

          // Only add non-empty datasets
          if (counts.some((count) => count > 0)) {
            datasets.push({
              label: token,
              data: counts,
              backgroundColor: gradientColors[index % gradientColors.length],
              borderWidth: 1,
            })
          }
        })

        chartRefs.current.eventTypes = new Chart(ctx, {
          type: "bar",
          data: {
            labels: eventTypes,
            datasets: datasets,
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                stacked: true,
              },
              x: {
                stacked: true,
              },
            },
          },
        })
      }
    }

    // Create confidence level chart
    if (confidenceLevelRef.current) {
      const ctx = confidenceLevelRef.current.getContext("2d")
      if (ctx) {
        // Get confidence levels for each token
        const tokens = [...new Set(data.map((d) => d.Token))]
        const highData = tokens.map(
          (token) => data.filter((d) => d.Token === token && d.Confidence_Level === "High").length,
        )
        const mediumData = tokens.map(
          (token) => data.filter((d) => d.Token === token && d.Confidence_Level === "Medium").length,
        )
        const lowData = tokens.map(
          (token) => data.filter((d) => d.Token === token && d.Confidence_Level === "Low").length,
        )

        chartRefs.current.confidenceLevel = new Chart(ctx, {
          type: "bar",
          data: {
            labels: tokens,
            datasets: [
              {
                label: "High Confidence",
                data: highData,
                backgroundColor: gradientColors[0], // Green
                borderWidth: 1,
              },
              {
                label: "Medium Confidence",
                data: mediumData,
                backgroundColor: gradientColors[4], // Yellow
                borderWidth: 1,
              },
              {
                label: "Low Confidence",
                data: lowData,
                backgroundColor: gradientColors[1], // Blue
                borderWidth: 1,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                stacked: true,
              },
              x: {
                stacked: true,
              },
            },
          },
        })
      }
    }

    // Cleanup function
    return () => {
      Object.values(chartRefs.current).forEach((chart) => {
        if (chart) chart.destroy()
      })
    }
  }, [data])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Data Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <canvas ref={tokenDistributionRef} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Event Types Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <canvas ref={eventTypesRef} />
          </div>
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>Confidence Level Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <canvas ref={confidenceLevelRef} />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

