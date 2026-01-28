import { createContext, useContext, useState, ReactNode } from "react";
import type { Document } from "@/app/components/document-card";

export interface SelectionContextValue {
  selected: Map<string, Document>;
  toggle: (doc: Document) => void;
  add: (doc: Document) => void;
  remove: (doc: Document) => void;
  clear: () => void;
  isSelected: (id: string) => boolean;
}

const SelectionContext = createContext<SelectionContextValue | null>(null);

export function useSelection(): SelectionContextValue {
  const ctx = useContext(SelectionContext);
  if (!ctx) throw new Error("useSelection must be used within SelectionProvider");
  return ctx;
}

export function SelectionProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<Map<string, Document>>(new Map());

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

  return (
    <SelectionContext.Provider value={{ selected, toggle, add, remove, clear, isSelected }}>
      {children}
    </SelectionContext.Provider>
  );
}
