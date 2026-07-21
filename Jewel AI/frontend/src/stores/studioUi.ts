import { create } from "zustand";

/** Cross-zone Studio UI state (not server data — that stays in React Query). */
type StudioUiState = {
  workflow: string;
  inspectorTab: "essentials" | "advanced" | "brand" | "model";
  batchFilter: "all" | "failed";
  setWorkflow: (w: string) => void;
  setInspectorTab: (t: StudioUiState["inspectorTab"]) => void;
  setBatchFilter: (f: StudioUiState["batchFilter"]) => void;
};

export const useStudioUiStore = create<StudioUiState>((set) => ({
  workflow: "CATALOG_IMAGE",
  inspectorTab: "essentials",
  batchFilter: "all",
  setWorkflow: (workflow) => set({ workflow }),
  setInspectorTab: (inspectorTab) => set({ inspectorTab }),
  setBatchFilter: (batchFilter) => set({ batchFilter }),
}));
