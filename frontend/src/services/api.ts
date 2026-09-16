import axios from 'axios';
import { ChatApiResponse, ChatStreamHandlers } from '../types/chat';
import { OilPrices } from '../types/market';
import { ModelInfo, PredictionResponse } from '../types/prediction';
import { SampleWell } from '../types/wellLog';

// it has to be change within the real subdomain once deployed
const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8006';

// Generous timeout: a cold LLM Space can take minutes to wake.
export const client = axios.create({ baseURL, timeout: 300000 });

// Short timeout on purpose: this drives the footer signal light, so a slow
// backend should read as trouble rather than hang on the app-wide 300s.
export async function getHealth(): Promise<boolean> {
  try {
    const { data } = await client.get<{ status: string }>('/health', { timeout: 5000 });
    return data?.status === 'ok';
  } catch {
    return false;
  }
}

export async function getModelInfo(): Promise<ModelInfo> {
  const { data } = await client.get<ModelInfo>('/model/info');
  return data;
}

export async function listSampleWells(): Promise<SampleWell[]> {
  const { data } = await client.get<SampleWell[]>('/wells/samples');
  return data;
}

export async function analyzeSampleWell(
  sampleId: string,
  sessionId: string,
): Promise<PredictionResponse> {
  const { data } = await client.get<PredictionResponse>(
    `/wells/samples/${sampleId}/analyze`,
    { params: { session_id: sessionId } },
  );
  return data;
}

export async function predictFromFile(
  file: File,
  sessionId: string,
): Promise<PredictionResponse> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await client.post<PredictionResponse>('/predict', form, {
    params: { include_samples: true, include_curves: true, session_id: sessionId },
  });
  return data;
}

export async function sendChat(
  message: string,
  sessionId: string,
  history: { role: 'user' | 'assistant'; content: string }[],
): Promise<ChatApiResponse> {
  const { data } = await client.post<ChatApiResponse>('/chat', {
    message,
    session_id: sessionId,
    history,
  });
  return data;
}

// Same turn as sendChat, but the answer arrives as server-sent events so the
// bubble fills in as Claude writes. axios cannot read a response body
// incrementally, so this one uses fetch. Resolves after the done event.
export async function streamChat(
  message: string,
  sessionId: string,
  history: { role: 'user' | 'assistant'; content: string }[],
  handlers: ChatStreamHandlers,
): Promise<void> {
  const res = await fetch(`${baseURL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ message, session_id: sessionId, history }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`chat stream failed: HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Events are separated by a blank line; keep any partial tail for later.
    let split: number;
    while ((split = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      dispatchSse(raw, handlers);
    }
  }
}

function dispatchSse(raw: string, handlers: ChatStreamHandlers): void {
  let event = 'message';
  let data = '';
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) data += line.slice(5).trim();
  }
  if (!data) return;
  const payload = JSON.parse(data);

  switch (event) {
    case 'delta':
      handlers.onDelta(payload.text as string);
      break;
    case 'tool':
      handlers.onTool(payload.name as string);
      break;
    case 'done':
      handlers.onDone(payload as ChatApiResponse);
      break;
    case 'error':
      throw new Error(payload.detail as string);
  }
}

// Backend serves this from a 1-hour cache, so a short timeout is safe here.
export async function getOilPrices(): Promise<OilPrices> {
  const { data } = await client.get<OilPrices>('/market/oil-prices', { timeout: 15000 });
  return data;
}

export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail ?? err.message;
  }
  return String(err);
}
