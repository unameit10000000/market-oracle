"use client"

import { useState, useEffect } from "react"
import { cleanPrice } from "@/lib/data-utils"

interface PricePoint {
  type: string
  price: number
  description?: string
}

interface PriceData {
  [token: string]: {
    currentPrice: number | null
    allPrices: PricePoint[]
  }
}

interface PriceTargetsProps {
  data: any[]
}

export default function PriceTargets({ data }: PriceTargetsProps) {
  const [priceData, setPriceData] = useState<PriceData>({})
  const [expandedToken, setExpandedToken] = useState<string | null>(null)

  useEffect(() => {
    // Process data for price meters
    const tokens = [...new Set(data.filter((d) => d.Token !== "Market").map((d) => d.Token))]
    const processedData: PriceData = {}

    tokens.forEach((token) => {
      const tokenData = data.filter((d) => d.Token === token)
      const currentPrices = tokenData.filter((d) => d?.Price_Type === "Current" && cleanPrice(d?.Price_Level))
      const targets = tokenData.filter((d) => d?.Price_Type?.includes("Target") && cleanPrice(d?.Price_Level))
      const supports = tokenData.filter((d) => d?.Price_Type === "Support" && cleanPrice(d?.Price_Level))
      const resistances = tokenData.filter((d) => d?.Price_Type === "Resistance" && cleanPrice(d?.Price_Level))

      let currentPrice = null
      if (currentPrices.length > 0) {
        currentPrice = cleanPrice(currentPrices[0].Price_Level)
      }

      const allPrices: PricePoint[] = []

      supports.forEach((support) => {
        const price = cleanPrice(support.Price_Level)
        if (price)
          allPrices.push({
            type: "support",
            price,
            description: support.Description || support.Event_Description || `Support level at ${support.Price_Level}`,
          })
      })

      resistances.forEach((resistance) => {
        const price = cleanPrice(resistance.Price_Level)
        if (price)
          allPrices.push({
            type: "resistance",
            price,
            description: resistance.Description || resistance.Event_Description || `Resistance level at ${resistance.Price_Level}`,
          })
      })

      targets.forEach((target) => {
        const price = cleanPrice(target.Price_Level)
        if (price)
          allPrices.push({
            type: "target",
            price,
            description: target.Description || target.Event_Description || `Price target at ${target.Price_Level}`,
          })
      })

      if (currentPrice) {
        allPrices.push({
          type: "current",
          price: currentPrice,
          description: currentPrices[0].Description || currentPrices[0].Event_Description || `Current price at ${currentPrices[0].Price_Level}`,
        })
      }

      if (allPrices.length > 0) {
        processedData[token] = {
          currentPrice,
          allPrices: allPrices.sort((a, b) => a.price - b.price),
        }
      }
    })

    setPriceData(processedData)
  }, [data])

  if (Object.keys(priceData).length === 0) {
    return <div className="text-center py-8">No price data available</div>
  }

  const toggleExpand = (token: string) => {
    if (expandedToken === token) {
      setExpandedToken(null)
    } else {
      setExpandedToken(token)
    }
  }

  return (
    <div className="space-y-8">
      {Object.entries(priceData).map(([token, data]) => {
        if (data.allPrices.length === 0) return null

        const minPrice = Math.min(...data.allPrices.map((p) => p.price))
        const maxPrice = Math.max(...data.allPrices.map((p) => p.price))
        const isExpanded = expandedToken === token

        // Group price points by type for the detailed view
        const supports = data.allPrices.filter((p) => p.type === "support")
        const resistances = data.allPrices.filter((p) => p.type === "resistance")
        const targets = data.allPrices.filter((p) => p.type === "target")
        const current = data.allPrices.find((p) => p.type === "current")

        return (
          <div key={token} className="space-y-2">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-semibold">{token}</h3>
              <button onClick={() => toggleExpand(token)} className="text-sm text-primary hover:underline">
                {isExpanded ? "Collapse" : "View Details"}
              </button>
            </div>

            <div className="w-full">
              <div className="relative h-10 bg-muted rounded-full overflow-hidden">
                {data.currentPrice && (
                  <div
                    className="absolute h-full bg-gradient-multi"
                    style={{
                      width: `${((data.currentPrice - minPrice) / (maxPrice - minPrice)) * 100}%`,
                    }}
                  />
                )}

                {data.allPrices
                  .filter((p) => p.type !== "current")
                  .slice(0, isExpanded ? data.allPrices.length : 3)
                  .map((pricePoint, index) => {
                    const percentPosition = ((pricePoint.price - minPrice) / (maxPrice - minPrice)) * 100
                    let bgColor = "bg-primary"
                    const textColor = "text-white"

                    switch (pricePoint.type) {
                      case "support":
                        bgColor = "bg-teal-500"
                        break
                      case "resistance":
                        bgColor = "bg-red-500"
                        break
                      case "target":
                        bgColor = "bg-blue-500"
                        break
                    }

                    const topPosition = index % 2 === 0 ? "-top-7" : "-top-12"

                    return (
                      <div
                        key={`${token}-${pricePoint.type}-${index}`}
                        className={`absolute ${topPosition} transform -translate-x-1/2 px-2 py-1 rounded text-xs ${textColor} ${bgColor}`}
                        style={{
                          left: `${percentPosition}%`,
                          maxWidth: "120px",
                          zIndex: 10,
                        }}
                      >
                        ${pricePoint.price.toFixed(2)}
                      </div>
                    )
                  })}

                {data.currentPrice && (
                  <div
                    className="absolute top-full mt-1 transform -translate-x-1/2 px-2 py-1 rounded text-xs bg-primary text-white"
                    style={{
                      left: `${((data.currentPrice - minPrice) / (maxPrice - minPrice)) * 100}%`,
                    }}
                  >
                    ${data.currentPrice.toFixed(2)}
                  </div>
                )}
              </div>

              <div className="flex justify-between mt-8 text-sm text-muted-foreground">
                <span>${minPrice.toFixed(2)}</span>
                <span>${maxPrice.toFixed(2)}</span>
              </div>
            </div>

            {isExpanded && (
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                {current && (
                  <div className="col-span-full bg-secondary p-4 rounded-lg">
                    <h4 className="font-semibold text-primary mb-1">Current Price: ${current.price.toFixed(2)}</h4>
                    <p className="text-sm">{current.description}</p>
                  </div>
                )}

                {targets.length > 0 && (
                  <div className="bg-secondary p-4 rounded-lg">
                    <h4 className="font-semibold text-primary mb-2">Price Targets</h4>
                    <ul className="space-y-2">
                      {targets.map((target, i) => (
                        <li key={i} className="text-sm border-l-4 border-blue-500 pl-2">
                          <span className="font-medium">${target.price.toFixed(2)}</span>
                          {target.description && (
                            <p className="text-xs text-muted-foreground mt-1">{target.description}</p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {supports.length > 0 && (
                  <div className="bg-secondary p-4 rounded-lg">
                    <h4 className="font-semibold text-teal-500 mb-2">Support Levels</h4>
                    <ul className="space-y-2">
                      {supports.map((support, i) => (
                        <li key={i} className="text-sm border-l-4 border-teal-500 pl-2">
                          <span className="font-medium">${support.price.toFixed(2)}</span>
                          {support.description && (
                            <p className="text-xs text-muted-foreground mt-1">{support.description}</p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {resistances.length > 0 && (
                  <div className="bg-secondary p-4 rounded-lg">
                    <h4 className="font-semibold text-red-500 mb-2">Resistance Levels</h4>
                    <ul className="space-y-2">
                      {resistances.map((resistance, i) => (
                        <li key={i} className="text-sm border-l-4 border-red-500 pl-2">
                          <span className="font-medium">${resistance.price.toFixed(2)}</span>
                          {resistance.description && (
                            <p className="text-xs text-muted-foreground mt-1">{resistance.description}</p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

