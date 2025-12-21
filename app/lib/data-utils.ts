// Helper function to parse CSV data
export function parseCSVData(csvString: string) {
  console.log("[parseCSVData] Input string length:", csvString.length);
  console.log("[parseCSVData] Input preview:", csvString.substring(0, 200));
  
  // Clean up the CSV string - remove code block markers and "txt" prefix
  let cleaned = csvString.trim();
  
  // Remove code block markers if present
  if (cleaned.includes("```")) {
    const parts = cleaned.split("```");
    if (parts.length >= 2) {
      cleaned = parts[1].trim();
      // Remove language identifier (.txt, txt, csv, etc.)
      if (cleaned.startsWith(".txt") || cleaned.startsWith("txt")) {
        cleaned = cleaned.replace(/^\.?txt\s*\n?/i, "");
      } else if (cleaned.startsWith("csv")) {
        cleaned = cleaned.replace(/^csv\s*\n?/i, "");
      }
    }
  }
  
  // This is a simplified CSV parser that handles quoted values
  const lines = cleaned.trim().split("\n")
  console.log("[parseCSVData] Total lines after cleanup:", lines.length);
  
  if (lines.length === 0) {
    console.warn("[parseCSVData] No lines found in CSV string");
    return [];
  }

  // Skip "txt" if it's the first line
  let headerLineIndex = 0;
  if (lines[0].trim().toLowerCase() === "txt") {
    console.warn("[parseCSVData] Found 'txt' prefix, skipping first line");
    headerLineIndex = 1;
  }

  if (headerLineIndex >= lines.length) {
    console.warn("[parseCSVData] No header line found after skipping 'txt'");
    return [];
  }

  const headers = parseCSVLine(lines[headerLineIndex])
  console.log("[parseCSVData] Headers:", headers);

  const data = []

  // Start from the line after the header
  const dataStartIndex = headerLineIndex + 1;
  for (let i = dataStartIndex; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue; // Skip empty lines
    
    const values = parseCSVLine(line)
    if (values.length === headers.length) {
      const row: Record<string, string> = {}

      headers.forEach((header, index) => {
        row[header] = values[index] || ""
      })

      data.push(row)
    } else {
      console.warn(`[parseCSVData] Line ${i + 1} has ${values.length} values but expected ${headers.length}:`, values);
    }
  }

  console.log("[parseCSVData] Parsed rows:", data.length);
  return data
}

// Helper function to parse a CSV line with quoted values
function parseCSVLine(line: string): string[] {
  const result: string[] = []
  let current = ""
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const char = line[i]

    if (char === '"') {
      inQuotes = !inQuotes
    } else if (char === "," && !inQuotes) {
      result.push(current.trim())
      current = ""
    } else {
      current += char
    }
  }

  // Add the last field
  result.push(current.trim())

  return result
}

// Helper function to clean price values
export function cleanPrice(price: string | null | undefined): number | null {
  if (!price || price === "N/A") return null

  // Handle price ranges like "$8.00-$10.00"
  if (price.includes("-")) {
    const parts = price.split("-")
    // Take the average of the range
    const min = Number.parseFloat(parts[0].replace(/[^\d.-]/g, ""))
    const max = Number.parseFloat(parts[1].replace(/[^\d.-]/g, ""))
    return (min + max) / 2
  }

  // Handle prices with "+" like "$54000+"
  if (price.includes("+")) {
    return Number.parseFloat(price.replace(/[^\d.-]/g, ""))
  }

  return Number.parseFloat(price.replace(/[^\d.-]/g, ""))
}

