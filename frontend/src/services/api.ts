import axios from 'axios';
import { ChatApiResponse } from '../types/chat';
import { OilPrices } from '../types/market';
import { ModelInfo, PredictionResponse } from '../types/prediction';
import { SampleWell } from '../types/wellLog';

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8006';

// Generous timeout: a cold LLM Space can take minutes to wake.
export const client = axios.create({ baseURL, timeout: 300000 });

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
