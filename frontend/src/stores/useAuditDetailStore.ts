import { create } from 'zustand';

interface AuditDetailState {
  /** Whether the detail drawer is open */
  drawerOpen: boolean;
  /** The currently selected finding (any record with an id) */
  selectedFinding: Record<string, unknown> | null;
  /** Type of finding: 'slither' | 'fuzz' | 'llm' | 'vulnerability' */
  findingType: 'slither' | 'fuzz' | 'llm' | 'vulnerability' | null;

  openDrawer: (finding: Record<string, unknown>, type: AuditDetailState['findingType']) => void;
  closeDrawer: () => void;
}

export const useAuditDetailStore = create<AuditDetailState>((set) => ({
  drawerOpen: false,
  selectedFinding: null,
  findingType: null,

  openDrawer: (finding, type) => set({
    drawerOpen: true,
    selectedFinding: finding,
    findingType: type,
  }),
  closeDrawer: () => set({
    drawerOpen: false,
    selectedFinding: null,
    findingType: null,
  }),
}));
