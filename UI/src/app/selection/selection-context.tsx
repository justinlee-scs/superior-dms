import { createContext, useContext, useState, ReactNode } from "react";
import type { Document } from "@/app/components/document-card";

export interface SelectionContextValue {
  selected: Map<string, Document>;
  toggle: (doc: Document) => void;
  add: (doc: Document) => void;
  remove: (doc: Document) => void;
  clear: () => void;
  isSelected: (id: string) => boolean;
  selectRange: (docs: Document[], fromId: string, toId: string) => void;
  focusedId: string | null;
  setFocusedId: (id: string | null) => void;
}

const SelectionContext = createContext<SelectionContextValue | null>(null);

export function useSelection(): SelectionContextValue {
  const ctx = useContext(SelectionContext);
  if (!ctx) throw new Error("useSelection must be used within SelectionProvider");
  return ctx;
}

export function SelectionProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<Map<string, Document>>(new Map());
  const [focusedId, setFocusedId] = useState<string | null>(null);

  const toggle = (doc: Document) => {
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(doc.id)) next.delete(doc.id);
      else next.set(doc.id, doc);
      return next;
    });
  };

  const add = (doc: Document) => {
    setSelected((prev) => new Map(prev).set(doc.id, doc));
  };

  const remove = (doc: Document) => {
    setSelected((prev) => {
      const next = new Map(prev);
      next.delete(doc.id);
      return next;
    });
  };

  const clear = () => setSelected(new Map());

  const isSelected = (id: string) => selected.has(id);

  // Selects all docs between fromId and toId (inclusive) in the provided
  // ordered flat list of all visible docs.
  const selectRange = (docs: Document[], fromId: string, toId: string) => {
    const fromIdx = docs.findIndex((d) => d.id === fromId);
    const toIdx = docs.findIndex((d) => d.id === toId);
    if (fromIdx === -1 || toIdx === -1) return;
    const start = Math.min(fromIdx, toIdx);
    const end = Math.max(fromIdx, toIdx);
    setSelected((prev) => {
      const next = new Map(prev);
      for (let i = start; i <= end; i++) {
        next.set(docs[i].id, docs[i]);
      }
      return next;
    });
  };

  return (
    <SelectionContext.Provider
      value={{ selected, toggle, add, remove, clear, isSelected, selectRange, focusedId, setFocusedId }}
    >
      {children}
    </SelectionContext.Provider>
  );
}