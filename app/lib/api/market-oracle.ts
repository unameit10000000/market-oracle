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

  /**
   * Check if Polymarket API keys are configured
   */
  async checkPolymarketKeys(): Promise<{
    status: string;
    keys_configured: boolean;
    keys_present: {
      api_key: boolean;
      api_secret: boolean;
      api_passphrase: boolean;
    };
    error?: string;
  }> {
    console.log(`[MarketOracleAPI] Checking Polymarket API keys`);
    try {
      const response = await apiClient.get<{
        status: string;
        keys_configured: boolean;
        keys_present: {
          api_key: boolean;
          api_secret: boolean;
          api_passphrase: boolean;
        };
        error?: string;
      }>("/poly/check-keys");
      
      console.log(`[MarketOracleAPI] Keys configured: ${response.keys_configured}`);
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error checking Polymarket keys:`, error);
      throw error;
    }
  },

  /**
   * Get Polymarket event markets list
   */
  async getPolymarketMarkets(options: {
    url?: string;
    slug?: string;
  }): Promise<{
    status: string;
    event_slug: string;
    endDate?: string;  // Event resolution time (ISO 8601 format)
    markets_count: number;
    markets: Array<{
      id: string;
      question?: string;
      groupItemTitle?: string;
      details: {
        active: boolean;
        closed: boolean;
        outcomes: string;
        outcomePrices: string;
        volume: string;
      };
    }>;
    error?: string;
  }> {
    console.log(`[MarketOracleAPI] Fetching Polymarket markets:`, options);
    try {
      const params = new URLSearchParams();
      if (options.url) {
        params.append("url", options.url);
      } else if (options.slug) {
        params.append("slug", options.slug);
      } else {
        throw new Error("Either url or slug must be provided");
      }

      const response = await apiClient.get<{
        status: string;
        event_slug: string;
        markets_count: number;
        markets: Array<{
          id: string;
          details: {
            active: boolean;
            closed: boolean;
            outcomes: string;
            outcomePrices: string;
            volume: string;
          };
        }>;
        error?: string;
      }>(`/poly/event/markets/list?${params.toString()}`);
      
      console.log(`[MarketOracleAPI] Markets fetched: ${response.markets_count} markets`);
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error fetching Polymarket markets:`, error);
      throw error;
    }
  },

  /**
   * Start auto thinking mode
   */
  async startThinking(options: {
    interval: string;
    enabled_modules: string[];
    analysis_id: string;
    chat_history: Array<{ role: "user" | "assistant"; content: string }>;
  }): Promise<{
    status: string;
    message: string;
    next_fetch_at: string;
  }> {
    console.log(`[MarketOracleAPI] Starting auto thinking:`, options);
    try {
      const response = await apiClient.post<{
        status: string;
        message: string;
        next_fetch_at: string;
      }>("/ai-tracking/start-thinking", options);
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error starting auto thinking:`, error);
      throw error;
    }
  },

  /**
   * Stop auto thinking mode
   */
  async stopThinking(analysisId: string): Promise<{
    status: string;
    message: string;
  }> {
    console.log(`[MarketOracleAPI] Stopping auto thinking for: ${analysisId}`);
    try {
      const response = await apiClient.post<{
        status: string;
        message: string;
      }>("/ai-tracking/stop-thinking", {
        analysis_id: analysisId,
      });
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error stopping auto thinking:`, error);
      throw error;
    }
  },

  /**
   * Fetch analysis with module data (auto mode)
   */
  async fetchAnalysis(options: {
    analysis_id: string;
    enabled_modules: string[];
    chat_history: Array<{ role: "user" | "assistant"; content: string }>;
    polymarket_config?: {
      url?: string;
      slug?: string;
    };
  }): Promise<{
    ai_response: {
      content: string;
      timestamp: string;
    };
    polymarket_response?: {
      status: string;
      event_slug: string;
      endDate?: string;
      markets_count: number;
      markets: Array<{
        id: string;
        question?: string;
        groupItemTitle?: string;
        details: {
          active: boolean;
          closed: boolean;
          outcomes: string;
          outcomePrices: string;
          volume: string;
        };
      }>;
      error?: string;
    };
  }> {
    console.log(`[MarketOracleAPI] Fetching analysis:`, options);
    try {
      const response = await apiClient.post<{
        ai_response: {
          content: string;
          timestamp: string;
        };
        polymarket_response?: {
          status: string;
          event_slug: string;
          endDate?: string;
          markets_count: number;
          markets: Array<{
            id: string;
            question?: string;
            groupItemTitle?: string;
            details: {
              active: boolean;
              closed: boolean;
              outcomes: string;
              outcomePrices: string;
              volume: string;
            };
          }>;
          error?: string;
        };
      }>("/ai-tracking/fetch-analysis", options);
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error fetching analysis:`, error);
      throw error;
    }
  },

  /**
   * Send manual chat message
   */
  async sendChatMessage(options: {
    analysis_id: string;
    message: string;
    chat_history: Array<{ role: "user" | "assistant"; content: string }>;
    enabled_modules: string[];
    polymarket_data?: any;
  }): Promise<{
    ai_response: {
      content: string;
      timestamp: string;
    };
  }> {
    console.log(`[MarketOracleAPI] Sending chat message:`, options);
    try {
      const response = await apiClient.post<{
        ai_response: {
          content: string;
          timestamp: string;
        };
      }>("/ai-tracking/chat", options);
      return response;
    } catch (error) {
      console.error(`[MarketOracleAPI] Error sending chat message:`, error);
      throw error;
    }
  },
};

