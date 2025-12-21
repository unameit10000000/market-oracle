import API_CONFIG from "@/lib/config";

// Base API client for making requests to the external Flask API
export class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
    console.log(`[API] Initializing API client with base URL: ${this.baseUrl}`);
  }

  // GET request
  async get<T>(endpoint: string): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    console.log(`[API] GET request to: ${url}`);

    try {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };

      const response = await fetch(url, {
        method: "GET",
        headers,
        mode: "cors",
      });

      console.log(`[API] Response status: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[API] Error response: ${errorText}`);
        throw new Error(`API error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log(`[API] Response data:`, data);
      return data as T;
    } catch (error) {
      console.error(`[API] Error in GET request to ${url}:`, error);
      throw error;
    }
  }

  // POST request
  async post<T>(endpoint: string, body: any): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    console.log(`[API] POST request to: ${url}`);
    console.log(`[API] Request body:`, body);

    try {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };

      const response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        mode: "cors",
      });

      console.log(`[API] Response status: ${response.status}`);
      console.log(`[API] Response headers:`, Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        let errorText = "";
        try {
          errorText = await response.text();
        } catch (e) {
          errorText = `Failed to read error response: ${e}`;
        }
        console.error(`[API] Error response: ${errorText}`);
        throw new Error(`API error: ${response.status} - ${errorText}`);
      }

      let data;
      try {
        const text = await response.text();
        console.log(`[API] Response text:`, text);
        data = JSON.parse(text);
      } catch (e) {
        console.error(`[API] Failed to parse JSON response:`, e);
        throw new Error(`Failed to parse response as JSON: ${e}`);
      }

      console.log(`[API] Response data:`, data);
      return data as T;
    } catch (error) {
      console.error(`[API] Error in POST request to ${url}:`, error);
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error(`Network error: Unable to connect to API at ${url}. Make sure the API server is running.`);
      }
      throw error;
    }
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();

