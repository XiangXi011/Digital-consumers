import { create } from 'zustand';

export const useProjectStore = create((set) => ({
  selectedProjectId: null,
  filterStatus: 'all',

  selectProject: (id) => set({ selectedProjectId: id }),
  setFilterStatus: (status) => set({ filterStatus: status }),
  clearSelection: () => set({ selectedProjectId: null }),
}));
