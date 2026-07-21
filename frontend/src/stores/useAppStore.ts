import { create } from 'zustand';

interface AppState {
  /** Currently selected project ID (for header project selector) */
  currentProjectId: number | null;
  currentProjectName: string;
  /** SSE connection status */
  sseConnected: boolean;

  setCurrentProject: (id: number | null, name?: string) => void;
  setSseConnected: (connected: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentProjectId: null,
  currentProjectName: '',
  sseConnected: false,

  setCurrentProject: (id, name) => set({
    currentProjectId: id,
    currentProjectName: name ?? '',
  }),
  setSseConnected: (connected) => set({ sseConnected: connected }),
}));
