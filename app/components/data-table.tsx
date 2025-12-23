"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ChevronDown, ChevronUp, Download, Loader2 } from "lucide-react"
import { cleanPrice } from "@/lib/data-utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { marketOracleApi } from "@/lib/api/market-oracle"

interface DataTableProps {
  data: any[]
  hideExport?: boolean
  analysisId?: string
}

// Function to parse and compare dates
const parseDateForSort = (dateStr: string) => {
  // Handle special cases
  if (dateStr === "Current") return new Date()
  if (dateStr === "Future") return new Date("2050-01-01")
  if (dateStr === "Recent" || dateStr === "Past") return new Date("2024-01-01")

  // Try to parse specific date
  const parsedDate = new Date(dateStr)
  return isNaN(parsedDate.getTime()) ? new Date("2025-01-01") : parsedDate
}

// Function to get confidence level value for sorting
const getConfidenceValue = (confidence: string): number => {
  const values = { High: 3, Medium: 2, Low: 1 }
  return values[confidence as keyof typeof values] || 0
}

export default function DataTable({ data, hideExport = false, analysisId }: DataTableProps) {
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc")
  const [sortedData, setSortedData] = useState(data)
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [question, setQuestion] = useState("")
  const [aiResponse, setAiResponse] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Function to handle column sorting
  const handleSort = (column: string, sortType: string) => {
    // Toggle sort direction if clicking the same column
    if (column === sortColumn) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortColumn(column)
      setSortDirection("asc")
    }

    // Sort data based on column type
    const sorted = [...data].sort((a, b) => {
      let valueA, valueB

      switch (sortType) {
        case "price":
          valueA = cleanPrice(a[column]) || 0
          valueB = cleanPrice(b[column]) || 0
          break
        case "date":
          valueA = parseDateForSort(a[column]).getTime()
          valueB = parseDateForSort(b[column]).getTime()
          break
        case "confidence":
          valueA = getConfidenceValue(a[column])
          valueB = getConfidenceValue(b[column])
          break
        default:
          valueA = (a[column] || "").toLowerCase()
          valueB = (b[column] || "").toLowerCase()
      }

      if (valueA < valueB) return sortDirection === "asc" ? -1 : 1
      if (valueA > valueB) return sortDirection === "asc" ? 1 : -1
      return 0
    })

    setSortedData(sorted)
  }

  // Update sorted data when data prop changes
  if (data !== sortedData && !sortColumn) {
    setSortedData(data)
  }

  // Function to handle clicking a row to ask AI about an event
  const handleRowClick = (event: any) => {
    setSelectedEvent(event)
    setQuestion("")
    setAiResponse(null)
    setError(null)
    setIsDialogOpen(true)
  }

  // Function to submit question to AI
  const handleSubmitQuestion = async () => {
    if (!question.trim() || !selectedEvent) return

    setIsLoading(true)
    setError(null)
    setAiResponse(null)

    try {
      const response = await marketOracleApi.askAI(question, selectedEvent, {
        analysis_id: analysisId,
      })
      setAiResponse(response.response)
    } catch (err: any) {
      setError(err.message || "Failed to get AI response")
    } finally {
      setIsLoading(false)
    }
  }

  // Function to export data as CSV
  const exportToCSV = () => {
    // Get headers
    const headers = Object.keys(data[0] || {}).join(",")

    // Get rows
    const rows = data
      .map((row) => {
        return Object.values(row)
          .map((value) => {
            // Handle values with commas by wrapping in quotes
            if (typeof value === "string" && value.includes(",")) {
              return `"${value}"`
            }
            return value
          })
          .join(",")
      })
      .join("\n")

    // Combine headers and rows
    const csvContent = `${headers}\n${rows}`

    // Create a blob and download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", "market_data.csv")
    link.style.visibility = "hidden"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="overflow-x-auto">
      {!hideExport && (
        <div className="flex justify-end mb-4">
          <Button onClick={exportToCSV} variant="outline" size="sm" className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export Data
          </Button>
        </div>
      )}
      <Table className="text-xs">
        <TableHeader>
          <TableRow>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Token", "string")}>
              Token
              {sortColumn === "Token" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Date", "date")}>
              Date
              {sortColumn === "Date" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Resolve_Time", "string")}>
              Resolve Time
              {sortColumn === "Resolve_Time" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Event_Type", "string")}>
              Event Type
              {sortColumn === "Event_Type" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Forecast", "string")}>
              Forecast
              {sortColumn === "Forecast" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Timeframe", "string")}>
              Timeframe
              {sortColumn === "Timeframe" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Title", "string")}>
              Title
              {sortColumn === "Title" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead
              className="cursor-pointer hover:bg-muted text-xs"
              onClick={() => handleSort("Description", "string")}
            >
              Description
              {sortColumn === "Description" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Event_Category", "string")}>
              Category
              {sortColumn === "Event_Category" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Price_Level", "price")}>
              Price Level
              {sortColumn === "Price_Level" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Price_Type", "string")}>
              Price Type
              {sortColumn === "Price_Type" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Pattern", "string")}>
              Pattern
              {sortColumn === "Pattern" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-muted text-xs" onClick={() => handleSort("Content_Source", "string")}>
              Content Source
              {sortColumn === "Content_Source" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
            <TableHead
              className="cursor-pointer hover:bg-muted text-xs"
              onClick={() => handleSort("Confidence_Level", "confidence")}
            >
              Confidence
              {sortColumn === "Confidence_Level" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? (
                    <ChevronUp className="inline h-3 w-3" />
                  ) : (
                    <ChevronDown className="inline h-3 w-3" />
                  )}
                </span>
              )}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedData.map((row, index) => (
            <TableRow
              key={index}
              className="cursor-pointer hover:bg-muted/50 transition-colors text-xs"
              onClick={() => handleRowClick(row)}
            >
              <TableCell className="relative text-xs">
                {row.Token}
              </TableCell>
              <TableCell className="text-xs">{row.Date}</TableCell>
              <TableCell className="text-xs">{row.Resolve_Time || "N/A"}</TableCell>
              <TableCell className="text-xs">{row.Event_Type}</TableCell>
              <TableCell className="text-xs">
                <span
                  className={
                    row.Forecast?.includes("DUMP")
                      ? "text-red-600 font-semibold"
                      : row.Forecast?.includes("PUMP")
                        ? "text-teal-600 font-semibold"
                        : row.Forecast?.includes("VOLATILITY")
                          ? "text-amber-600 font-semibold"
                          : ""
                  }
                >
                  {row.Forecast || "N/A"}
                </span>
              </TableCell>
              <TableCell className="text-xs">{row.Timeframe}</TableCell>
              <TableCell className="max-w-[200px] truncate text-xs">{row.Title || "N/A"}</TableCell>
              <TableCell className="max-w-[200px] truncate text-xs">
                {row.Description || row.Event_Description || "N/A"}
              </TableCell>
              <TableCell className="text-xs">{row.Event_Category || "N/A"}</TableCell>
              <TableCell className="text-xs">{row.Price_Level}</TableCell>
              <TableCell className="text-xs">{row.Price_Type}</TableCell>
              <TableCell className="text-xs">{row.Pattern}</TableCell>
              <TableCell className="text-xs">{row.Content_Source}</TableCell>
              <TableCell className="text-xs">
                <span
                  className={
                    row.Confidence_Level === "High"
                      ? "text-teal-500"
                      : row.Confidence_Level === "Medium"
                        ? "text-amber-600"
                        : "text-red-600"
                  }
                >
                  {row.Confidence_Level}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Ask AI Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto text-xs">
          <DialogHeader>
            <DialogTitle>Ask AI</DialogTitle>
            <DialogDescription>
              Ask a question about this event. I'll search for current information and provide insights.
            </DialogDescription>
          </DialogHeader>

          {selectedEvent && (
            <div className="space-y-4">
              {/* Event Summary */}
              <div className="p-3 bg-muted rounded-md text-sm">
                <p className="font-semibold mb-1">{selectedEvent.Title || selectedEvent.Event_Description || "Event"}</p>
                <p className="text-muted-foreground">
                  {selectedEvent.Token} • {selectedEvent.Date} • {selectedEvent.Event_Type}
                </p>
              </div>

              {/* Question Input */}
              <div className="space-y-2">
                <label htmlFor="question" className="text-sm font-medium">
                  Your Question
                </label>
                <Input
                  id="question"
                  placeholder="e.g., What is the current status of this event?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      handleSubmitQuestion()
                    }
                  }}
                  disabled={isLoading}
                />
                <Button
                  onClick={handleSubmitQuestion}
                  disabled={!question.trim() || isLoading}
                  className="w-full"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Asking AI...
                    </>
                  ) : (
                    "Ask AI"
                  )}
                </Button>
              </div>

              {/* Error Display */}
              {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-sm text-destructive">
                  {error}
                </div>
              )}

              {/* AI Response */}
              {aiResponse && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">AI Response</label>
                  <div className="p-4 bg-muted rounded-md text-sm whitespace-pre-wrap">
                    {aiResponse}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

