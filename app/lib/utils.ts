import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Cookie management utilities for AI Tracking
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

/**
 * Save AI response to cookies
 */
export function saveAiResponseToCookie(aiResponse: ChatMessage, analysisId: string): void {
  try {
    const cookieKey = `ai_response_${analysisId}`;
    const existing = loadChatHistoryFromCookies(analysisId);
    const updated = [...existing, aiResponse];
    
    // Store as JSON string
    const cookieValue = JSON.stringify(updated);
    
    // Set cookie with expiration (30 days)
    const expirationDate = new Date();
    expirationDate.setDate(expirationDate.getDate() + 30);
    
    document.cookie = `${cookieKey}=${encodeURIComponent(cookieValue)}; expires=${expirationDate.toUTCString()}; path=/`;
  } catch (error) {
    console.error("Error saving AI response to cookie:", error);
  }
}

/**
 * Load chat history from cookies
 */
export function loadChatHistoryFromCookies(analysisId: string): ChatMessage[] {
  try {
    const cookieKey = `ai_response_${analysisId}`;
    const cookies = document.cookie.split(';');
    
    for (const cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === cookieKey && value) {
        const decoded = decodeURIComponent(value);
        const parsed = JSON.parse(decoded);
        return Array.isArray(parsed) ? parsed : [];
      }
    }
    
    return [];
  } catch (error) {
    console.error("Error loading chat history from cookies:", error);
    return [];
  }
}

/**
 * Clear session cookies for a specific analysis
 */
export function clearSessionCookies(analysisId: string): void {
  try {
    const cookieKey = `ai_response_${analysisId}`;
    // Set expiration to past date to delete cookie
    document.cookie = `${cookieKey}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
  } catch (error) {
    console.error("Error clearing session cookies:", error);
  }
}

/**
 * Clear all AI response cookies
 */
export function clearAllAiResponseCookies(): void {
  try {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [key] = cookie.trim().split('=');
      if (key.startsWith('ai_response_')) {
        document.cookie = `${key}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      }
    }
  } catch (error) {
    console.error("Error clearing all AI response cookies:", error);
  }
}

