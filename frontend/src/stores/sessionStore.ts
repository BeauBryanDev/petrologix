import { create } from 'zustand';
import {
  analyzeSampleWell,
  apiErrorMessage,
  getModelInfo,
  listSampleWells,
  predictFromFile,
  sendChat,
} from '../services/api';
import { ChatMessage } from '../types/chat';
import { ModelInfo, PredictionResponse } from '../types/prediction';
import { SampleWell } from '../types/wellLog';

type ServiceStatus = 'online' | 'busy' | 'offline';
type EngineStatus = 'ready' | 'computing' | 'error';

interface SessionState {
  sessionId: string;
  prediction: PredictionResponse | null;
  modelInfo: ModelInfo | null;
  samples: SampleWell[];
  activeSampleId: string | null;
  messages: ChatMessage[];
  format: 'LAS' | 'CSV';
  llmStatus: ServiceStatus;
  xgboostStatus: EngineStatus;
  ragStatus: 'pending' | 'ready' | 'syncing';
  error: string | null;

  bootstrap: () => Promise<void>;
  setFormat: (format: 'LAS' | 'CSV') => void;
  loadSampleWell: (sampleId: string) => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  toggleRag: () => void;
}

const now = () =>
  new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const newId = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;

function assistantMessage(text: string, prediction: PredictionResponse | null): ChatMessage {
  const top = prediction?.distribution_by_lithology?.[0];
  return {
    id: newId('msg-assistant'),
    sender: 'assistant',
    authorName: 'AEGIS-GEO-MIND',
    text,
    timestamp: now(),
    faciesContext: top?.lithology,
    confidenceContext: top?.mean_confidence,
  };
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessionId: newId('session'),
  prediction: null,
  modelInfo: null,
  samples: [],
  activeSampleId: null,
  messages: [],
  format: 'LAS',
  llmStatus: 'online',
  xgboostStatus: 'ready',
  ragStatus: 'pending',
  error: null,

  // Loads model metadata, the sample list, and analyses the first sample so the
  // HUD boots with a real well instead of an empty console.
  bootstrap: async () => {
    try {
      const [modelInfo, samples] = await Promise.all([getModelInfo(), listSampleWells()]);
      set({ modelInfo, samples });
      if (samples.length) await get().loadSampleWell(samples[0].id);
    } catch (err) {
      set({ error: apiErrorMessage(err), xgboostStatus: 'error', llmStatus: 'offline' });
    }
  },

  setFormat: (format) => set({ format }),

  loadSampleWell: async (sampleId) => {
    set({ xgboostStatus: 'computing', error: null });
    try {
      const prediction = await analyzeSampleWell(sampleId, get().sessionId);
      set((state) => ({
        prediction,
        activeSampleId: sampleId,
        xgboostStatus: 'ready',
        messages: [...state.messages, assistantMessage(summarize(prediction), prediction)],
      }));
    } catch (err) {
      set({ xgboostStatus: 'error', error: apiErrorMessage(err) });
    }
  },

  uploadFile: async (file) => {
    set({ xgboostStatus: 'computing', error: null });
    const format = file.name.toLowerCase().endsWith('.csv') ? 'CSV' : 'LAS';
    try {
      const prediction = await predictFromFile(file, get().sessionId);
      set((state) => ({
        prediction,
        format,
        activeSampleId: null,
        xgboostStatus: 'ready',
        messages: [...state.messages, assistantMessage(summarize(prediction), prediction)],
      }));
    } catch (err) {
      const message = apiErrorMessage(err);
      set((state) => ({
        xgboostStatus: 'error',
        error: message,
        messages: [...state.messages, assistantMessage(message, null)],
      }));
    }
  },

  sendMessage: async (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const userMsg: ChatMessage = {
      id: newId('msg-user'),
      sender: 'user',
      text: trimmed,
      timestamp: now(),
    };
    const history = get()
      .messages.slice(-6)
      .map((m) => ({ role: m.sender === 'user' ? ('user' as const) : ('assistant' as const), content: m.text }));

    set((state) => ({ messages: [...state.messages, userMsg], llmStatus: 'busy' }));

    try {
      const res = await sendChat(trimmed, get().sessionId, history);
      set((state) => ({
        llmStatus: res.llm_used ? 'online' : 'offline',
        messages: [
          ...state.messages,
          {
            id: newId('msg-assistant'),
            sender: 'assistant',
            authorName: 'AEGIS-GEO-MIND',
            text: res.answer,
            timestamp: now(),
            faciesContext: res.dominant_lithology ?? undefined,
            confidenceContext: res.mean_confidence ?? undefined,
          },
        ],
      }));
    } catch (err) {
      set((state) => ({
        llmStatus: 'offline',
        messages: [...state.messages, assistantMessage(apiErrorMessage(err), get().prediction)],
      }));
    }
  },

  toggleRag: () =>
    set((state) => ({ ragStatus: state.ragStatus === 'pending' ? 'ready' : 'pending' })),
}));

function summarize(p: PredictionResponse): string {
  if (p.distribution.status === 'out_of_distribution') return p.distribution.message;
  const top = p.distribution_by_lithology[0];
  if (!top) return `Loaded ${p.well_name}. No lithology zones resolved.`;
  return `Loaded ${p.well_name}: ${p.n_samples} depth samples, ${p.intervals.length} zones. Dominant lithology ${top.lithology} (${(top.fraction * 100).toFixed(0)}%, mean confidence ${top.mean_confidence.toFixed(2)}).`;
}
