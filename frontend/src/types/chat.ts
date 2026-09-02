export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  authorName?: string;
  text: string;
  timestamp: string;
  faciesContext?: string;
  confidenceContext?: number;
}

export interface ChatApiResponse {
  answer: string;
  session_id: string;
  llm_used: boolean;
  has_well_context: boolean;
  warnings: string[];
  dominant_lithology: string | null;
  mean_confidence: number | null;
  trace: string[];
}
