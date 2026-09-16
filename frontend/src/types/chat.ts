export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  authorName?: string;
  text: string;
  timestamp: string;
  faciesContext?: string;
  confidenceContext?: number;
  // True while the backend is still streaming this answer.
  streaming?: boolean;
  // Short status line shown in place of text, e.g. which tool is running.
  status?: string;
}

export interface ChatStreamHandlers {
  onDelta: (text: string) => void;
  onTool: (name: string) => void;
  onDone: (response: ChatApiResponse) => void;
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
