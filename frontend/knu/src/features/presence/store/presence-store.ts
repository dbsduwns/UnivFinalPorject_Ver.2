import { create } from "zustand";

type PresenceState = {
  activeRoomId: number | null;
  setActiveRoomId: (roomId: number | null) => void;
};

export const usePresenceStore = create<PresenceState>((set) => ({
  activeRoomId: null,
  setActiveRoomId: (activeRoomId) => set({ activeRoomId }),
}));
