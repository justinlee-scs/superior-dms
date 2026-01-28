import { createContext, useContext, useState, ReactNode } from "react";
import type { Document } from "@/app/components/document-card";

interface SelectionContextValue {
  selected: Map<string, Document>;
  toggle: (doc: Document) => void;
  clear: () => void;
  isSelected: (id: string) => boolean;
}

const SelectionContext = createContext<SelectionContextValue | null>(null);

export function SelectionProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<Map<string, Document>>(new Map());

  const toggle = (doc: Document) => {
    setSelected((prev) => {
      const next = new Map(prev);
      next.has(doc.id) ? next.delete(doc.id) : next.set(doc.id, doc);
      return next;
    });
  };

  const clear = () => setSelected(new Map());

  const isSelected = (id: string) => selected.has(id);

  return (
    <SelectionContext.Provider value={{ selected, toggle, clear, isSelected }}>
      {children}
    </SelectionContext.Provider>
  );
}

export function useSelection() {
  const ctx = useContext(SelectionContext);
  if (!ctx) throw new Error("useSelection must be used inside SelectionProvider");
  return ctx;
}
