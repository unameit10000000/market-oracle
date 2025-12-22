"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  PlusCircle,
  Trash2,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { marketOracleApi } from "@/lib/api/market-oracle";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Home() {
  const router = useRouter();

  const [urls, setUrls] = useState<string[]>([]);
  const [inputUrl, setInputUrl] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [validationComplete, setValidationComplete] = useState(false);
  const [validationSuccess, setValidationSuccess] = useState(false);
  const [validationResults, setValidationResults] = useState<
    Array<{
      url: string;
      success: boolean;
      video_id: string;
      error: string | null;
    }>
  >([]);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingAnalysisId, setExistingAnalysisId] = useState("");

  // Add a new URL
  const addUrl = () => {
    if (!inputUrl.trim()) return;

    try {
      // Basic URL validation
      new URL(inputUrl);

      // Check if it's a YouTube URL
      if (
        !inputUrl.includes("youtube.com") &&
        !inputUrl.includes("youtu.be")
      ) {
        setError("Please enter a valid YouTube URL");
        return;
      }

      setUrls([...urls, inputUrl]);
      setInputUrl("");
      setError(null);
    } catch (e) {
      setError("Please enter a valid URL");
    }
  };

  // Remove a URL
  const removeUrl = (index: number) => {
    const newUrls = [...urls];
    newUrls.splice(index, 1);
    setUrls(newUrls);
  };

  // Handle validate button click
  const handleValidate = async () => {
    if (urls.length === 0) {
      setError("Please add at least one YouTube URL");
      return;
    }

    setIsValidating(true);
    setError(null);
    setValidationComplete(false);
    setValidationSuccess(false);

    try {
      console.log("Starting validation with URLs:", urls);
      const response = await marketOracleApi.validateUrls(urls);
      console.log("Validation response:", response);

      if (response.status === "success") {
        setAnalysisId(response.analysis_id);
        setValidationResults(response.transcripts);
        setValidationComplete(true);
        setValidationSuccess(response.summary.successful > 0);

        if (response.summary.successful === 0) {
          setError("All URLs failed validation. Please check your URLs and try again.");
        }
      } else {
        throw new Error("Validation failed");
      }
    } catch (err) {
      console.error("Failed to validate URLs:", err);
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      console.error("Error details:", {
        message: errorMessage,
        stack: err instanceof Error ? err.stack : undefined,
      });
      setError(
        `Failed to validate URLs: ${errorMessage}`
      );
      setValidationComplete(true);
      setValidationSuccess(false);
    } finally {
      setIsValidating(false);
    }
  };

  const [analysisComplete, setAnalysisComplete] = useState(false);

  // Handle analyze button click
  const handleAnalyze = async () => {
    if (!analysisId) {
      setError("No analysis ID available. Please validate URLs first.");
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await marketOracleApi.analyze(analysisId);

      if (response.status === "success") {
        // Analysis started successfully
        setAnalysisComplete(true);
      } else {
        throw new Error("Analysis failed");
      }
    } catch (err) {
      console.error("Failed to analyze:", err);
      setError(
        `Failed to analyze: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle process button click
  const handleProcess = async () => {
    if (!analysisId) {
      setError("No analysis ID available.");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const response = await marketOracleApi.process(analysisId);

      if (response.status === "success") {
        // Store CSV data in sessionStorage to avoid URL length limits
        sessionStorage.setItem(`analysis_${analysisId}`, response.csv_data);
        // Redirect to dashboard with just the analysis ID
        router.push(`/dashboard?analysisId=${analysisId}`);
      } else {
        throw new Error("Processing failed");
      }
    } catch (err) {
      console.error("Failed to process:", err);
      setError(
        `Failed to process: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
      setIsProcessing(false);
    }
  };

  // Handle viewing existing analysis
  const handleViewExisting = () => {
    if (!existingAnalysisId.trim()) {
      setError("Please enter an analysis ID");
      return;
    }

    // Redirect to dashboard with the analysis ID
    router.push(`/dashboard?analysisId=${existingAnalysisId.trim()}`);
  };

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <div className="w-full max-w-3xl">
        <div className="flex flex-col items-center mb-10 text-center">
          <h2 className="text-3xl md:text-5xl lg:text-6xl font-bold mb-4">
            <span className="text-gradient">Market Oracle</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mb-6">
            Analyze YouTube videos and generate market insights
          </p>
        </div>

        {/* View Existing Analysis Card */}
        <Card className="w-full mb-6">
          <CardHeader>
            <CardTitle className="text-center">View Existing Analysis</CardTitle>
            <CardDescription className="text-center">
              Enter an analysis ID to view a previously processed analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="Enter analysis ID (e.g., 20251220_174720)"
                value={existingAnalysisId}
                onChange={(e) => setExistingAnalysisId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleViewExisting()}
                className="flex-1"
              />
              <Button onClick={handleViewExisting} variant="outline">
                View Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Main card with gradient border */}
        <Card className="w-full overflow-hidden">
          <div className="p-[2px] bg-gradient-multi rounded-lg animate-gradient">
            <div className="bg-card rounded-[calc(var(--radius)-1px)]">
              <CardHeader>
                <CardTitle className="text-center">
                  Add YouTube URLs to Analyze
                </CardTitle>
                <CardDescription className="text-center">
                  Add YouTube video URLs to extract transcripts and generate analysis
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                {/* Input for adding URLs */}
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter YouTube URL"
                    value={inputUrl}
                    onChange={(e) => setInputUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addUrl()}
                    className="flex-1"
                  />
                  <Button onClick={addUrl} size="icon">
                    <PlusCircle className="h-5 w-5" />
                  </Button>
                </div>

                {/* Error message */}
                {error && (
                  <Alert variant="destructive">
                    <XCircle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* List of added URLs */}
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-center">
                    Added URLs ({urls.length})
                  </h3>

                  {urls.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center">
                      No URLs added yet
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                      {urls.map((url, index) => {
                        const result = validationResults.find((r) => r.url === url);
                        const statusClass =
                          result?.success === true
                            ? "border-teal-500"
                            : result?.success === false
                            ? "border-red-500"
                            : "border-amber-500";

                        return (
                          <div
                            key={index}
                            className={`flex items-center justify-between p-3 bg-secondary rounded-md overflow-hidden relative gap-2 ${statusClass} border`}
                          >
                            <div className="flex items-center gap-2 overflow-hidden">
                              <Badge variant="outline">YouTube</Badge>
                              <span className="text-sm truncate">{url}</span>
                              {result && (
                                <Badge
                                  variant={
                                    result.success === true
                                      ? "default"
                                      : "destructive"
                                  }
                                >
                                  {result.success ? "Valid" : "Invalid"}
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center">
                              {result?.error && (
                                <span
                                  className="text-xs text-red-500 mr-2 max-w-[200px] truncate"
                                  title={result.error}
                                >
                                  {result.error}
                                </span>
                              )}
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => removeUrl(index)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Validation results */}
                {validationComplete && (
                  <Alert
                    variant={validationSuccess ? "default" : "destructive"}
                    className="relative overflow-hidden"
                  >
                    {validationSuccess ? (
                      <CheckCircle className="h-4 w-4 text-teal-500" />
                    ) : (
                      <XCircle className="h-4 w-4" />
                    )}
                    <AlertTitle>
                      {validationSuccess ? "Validation Complete" : "Validation Failed"}
                    </AlertTitle>
                    <AlertDescription>
                      {validationSuccess ? (
                        <>
                          {validationResults.filter((r) => r.success).length} of{" "}
                          {validationResults.length} URLs were successfully validated.
                          {validationResults.filter((r) => !r.success).length > 0 && (
                            <>
                              {" "}
                              Some URLs failed validation. Please check the error
                              messages above.
                            </>
                          )}
                        </>
                      ) : (
                        "Failed to validate URLs. Please check your URLs and try again."
                      )}
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>

              <CardFooter className="flex justify-center gap-4">
                <Button
                  variant="default"
                  onClick={handleValidate}
                  disabled={isValidating || urls.length === 0 || isAnalyzing || isProcessing}
                  className="w-32"
                >
                  {isValidating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Validating
                    </>
                  ) : (
                    "Validate"
                  )}
                </Button>

                {validationSuccess && analysisId && !analysisComplete && (
                  <Button
                    variant="default"
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || isProcessing}
                    className="bg-gradient-multi text-white w-32"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Analyzing
                      </>
                    ) : (
                      "Analyze"
                    )}
                  </Button>
                )}

                {analysisComplete && analysisId && (
                  <Button
                    variant="default"
                    onClick={handleProcess}
                    disabled={isProcessing}
                    className="bg-gradient-multi text-white w-32"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing
                      </>
                    ) : (
                      "Process"
                    )}
                  </Button>
                )}
              </CardFooter>
            </div>
          </div>
        </Card>
      </div>
    </main>
  );
}

