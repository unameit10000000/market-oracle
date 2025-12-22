"use client"

import { useState } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface EventTimelineProps {
  data: any[]
}

// Helper function to parse dates for sorting
const parseDateForSort = (dateStr: string) => {
  // Handle special cases
  if (dateStr === "Current") return new Date()
  if (dateStr === "Future") return new Date("2050-01-01")
  if (dateStr === "Recent" || dateStr === "Past") return new Date("2024-01-01")

  // Try to parse specific date
  const parsedDate = new Date(dateStr)
  return isNaN(parsedDate.getTime()) ? new Date("2025-01-01") : parsedDate
}

// Function to determine timeframe order
const getTimeframeOrder = (timeframe: string) => {
  const order = { Past: 1, Present: 2, Future: 3 }
  return order[timeframe as keyof typeof order] || 2
}

export default function EventTimeline({ data }: EventTimelineProps) {
  const [sortOption, setSortOption] = useState("chronological")

  // Function to sort timeline based on selected option
  const sortTimeline = (events: any[], option: string) => {
    const sortedEvents = [...events]

    switch (option) {
      case "chronological":
        sortedEvents.sort((a, b) => parseDateForSort(a.Date).getTime() - parseDateForSort(b.Date).getTime())
        break
      case "reverse-chronological":
        sortedEvents.sort((a, b) => parseDateForSort(b.Date).getTime() - parseDateForSort(a.Date).getTime())
        break
      case "future-first":
        sortedEvents.sort((a, b) => {
          const timeframeOrderA = getTimeframeOrder(a.Timeframe)
          const timeframeOrderB = getTimeframeOrder(b.Timeframe)
          if (timeframeOrderA !== timeframeOrderB) {
            return timeframeOrderB - timeframeOrderA // Future first
          }
          return parseDateForSort(a.Date).getTime() - parseDateForSort(b.Date).getTime()
        })
        break
      case "past-first":
        sortedEvents.sort((a, b) => {
          const timeframeOrderA = getTimeframeOrder(a.Timeframe)
          const timeframeOrderB = getTimeframeOrder(b.Timeframe)
          if (timeframeOrderA !== timeframeOrderB) {
            return timeframeOrderA - timeframeOrderB // Past first
          }
          return parseDateForSort(a.Date).getTime() - parseDateForSort(b.Date).getTime()
        })
        break
    }

    return sortedEvents
  }

  const sortedEvents = sortTimeline(data, sortOption)

  return (
    <div>
      <div className="flex justify-end mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm">Sort by:</span>
          <Select value={sortOption} onValueChange={setSortOption}>
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder="Sort order" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="chronological">Chronological</SelectItem>
              <SelectItem value="reverse-chronological">Reverse Chronological</SelectItem>
              <SelectItem value="future-first">Future → Present → Past</SelectItem>
              <SelectItem value="past-first">Past → Present → Future</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="relative">
        {/* Timeline center line with gradient */}
        <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-primary transform -translate-x-1/2" />

        <div className="relative">
          {sortedEvents.map((event, index) => {
            const confidenceClass =
              event.Confidence_Level === "High"
                ? "border-teal-500"
                : event.Confidence_Level === "Medium"
                  ? "border-amber-500"
                  : "border-red-500"

            return (
              <div
                key={index}
                className={`relative mb-8 w-[calc(50%-20px)] ${index % 2 === 0 ? "ml-auto" : "mr-auto"}`}
              >
                <div className={`bg-card p-4 rounded-lg shadow-sm border-l-4 ${confidenceClass}`}>
                  <div className="text-primary font-semibold mb-1">{event.Date}</div>
                  <div className="font-bold mb-1">
                    {event.Token}: {event.Event_Type}
                  </div>
                  <div className="text-sm text-muted-foreground mb-2">
                    {event.Title && event.Title !== "N/A" && (
                      <div className="font-semibold mb-1">{event.Title}</div>
                    )}
                    {event.Description || event.Event_Description || "N/A"}
                    {event.Forecast && event.Forecast !== "N/A" && (
                      <div className="mt-1">
                        <span
                          className={
                            event.Forecast.includes("DUMP")
                              ? "text-red-600 font-semibold"
                              : event.Forecast.includes("PUMP")
                                ? "text-teal-600 font-semibold"
                                : event.Forecast.includes("VOLATILITY")
                                  ? "text-amber-600 font-semibold"
                                  : ""
                          }
                        >
                          Forecast: {event.Forecast}
                        </span>
                      </div>
                    )}
                  </div>
                  {event.Price_Level && event.Price_Level !== "N/A" && (
                    <div className="text-sm">
                      Price: {event.Price_Level} ({event.Price_Type})
                    </div>
                  )}
                </div>

                {/* Timeline connector */}
                <div
                  className="absolute top-6 h-0.5 bg-primary"
                  style={{
                    [index % 2 === 0 ? "left" : "right"]: "-20px",
                    width: "20px",
                  }}
                />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

