import { forwardRef } from "react";

interface SelectionCheckboxProps {
  checked: boolean;
  onToggle: () => void;
  indeterminate?: boolean;
}

export const SelectionCheckbox = forwardRef<HTMLInputElement, SelectionCheckboxProps>(
  ({ checked, onToggle, indeterminate = false }, ref) => {
    return (
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        ref={(el) => {
          if (el) el.indeterminate = indeterminate;
          if (typeof ref === "function") ref(el);
          else if (ref) ref.current = el;
        }}
      />
    );
  }
);

SelectionCheckbox.displayName = "SelectionCheckbox";