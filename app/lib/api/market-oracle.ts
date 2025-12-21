import { apiClient } from "./index";

// Market Oracle API functions
export const marketOracleApi = {
  /**
   * Validate YouTube URLs and extract transcripts
   */
  async validateUrls(
    youtubeUrls: string[]
  ): Promise<{
    status: string;
    analysis_id: string;
    transcripts: Array<{
      url: string;
      success: boolean;
      video_id: string;
      error: string | null;
    }>;
    summary: {
      total: number;
      successful: number;
      failed: number;
    };
    message: string;
  }> {
    console.log(`[MarketOracleAPI] Validating ${youtubeUrls.length} URLs`);
    try {
      const response = await apiClient.post<{
        status: string;
        analysis_id: string;
        transcripts: Array<{
          url: string;
          success: boolean;
          video_id: string;
          error: string | null;
        }>;
        summary: {
          total: number;
          successful: number;
          failed: number;
        };
        message: string;
      }>("/validate", {
        youtube_urls: youtubeUrls,
      });
      console.log(
        `[MarketOracleAPI] Validation complete with analysis ID: ${response.analysis_id}`
      );
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error validating URLs:`, error);
      throw error;
    }
  },

  /**
   * Run analysis with economic calendar configuration
   */
  async analyze(
    analysisId: string,
    config?: {
      forexfactory_start_date?: string;
      forexfactory_use_week?: boolean;
      tradingeconomics_start_date?: string;
      tradingeconomics_end_date?: string;
    }
  ): Promise<{
    status: string;
    analysis_id: string;
    message: string;
  }> {
    console.log(`[MarketOracleAPI] Starting analysis for: ${analysisId}`);
    try {
      const response = await apiClient.post<{
        status: string;
        analysis_id: string;
        message: string;
      }>("/analyze", {
        analysis_id: analysisId,
        ...config,
      });
      console.log(`[MarketOracleAPI] Analysis started for ${analysisId}`);
      return response;
    } catch (error) {
      console.error(
        `[MarketOracleAPI] Error starting analysis for ${analysisId}:`,
        error
      );
      throw error;
    }
  },

  /**
   * Process analysis and generate CSV data
   */
  async process(
    analysisId: string
  ): Promise<{
    status: string;
    analysis_directory: string;
    csv_data: string;
    comprehensive_analysis: string;
    forexfactory_events_count: number;
    tradingeconomics_events_count: number;
    youtube_transcripts_count: number;
    message: string;
  }> {
    console.log(`[MarketOracleAPI] Processing analysis: ${analysisId}`);
    try {
      const response = await apiClient.post<{
        status: string;
        analysis_directory: string;
        csv_data: string;
        comprehensive_analysis: string;
        forexfactory_events_count: number;
        tradingeconomics_events_count: number;
        youtube_transcripts_count: number;
        message: string;
      }>("/process", {
        analysis_id: analysisId,
      });
      console.log(`[MarketOracleAPI] Processing complete for ${analysisId}`);
      return response;
    } catch (error) {
      console.error(
        `[MarketOracleAPI] Error processing analysis ${analysisId}:`,
        error
      );
      throw error;
    }
  },

  /**
   * Ask AI about a specific event
   */
  async askAI(
    question: string,
    event: Record<string, any>,
    options?: {
      analysis_id?: string;
      max_searches?: number;
      max_tokens?: number;
    }
  ): Promise<{
    status: string;
    response: string;
    question: string;
    event: Record<string, any>;
    api_type: string;
  }> {
    console.log(`[MarketOracleAPI] Asking AI about event: ${event.Title || event.Event_Description}`);
    try {
      const response = await apiClient.post<{
        status: string;
        response: string;
        question: string;
        event: Record<string, any>;
        api_type: string;
      }>("/ask-ai", {
        question,
        event,
        analysis_id: options?.analysis_id,
        max_searches: options?.max_searches || 5,
        max_tokens: options?.max_tokens || 4000,
      });
      console.log(`[MarketOracleAPI] AI response received (length: ${response.response.length})`);
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error asking AI:`, error);
      throw error;
    }
  },
};

