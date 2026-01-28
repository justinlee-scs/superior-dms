interface SelectionCheckboxProps {
  checked: boolean;
  onToggle: () => void;
  indeterminate?: boolean;
}

export function SelectionCheckbox({
  checked,
  onToggle,
  indeterminate = false,
}: SelectionCheckboxProps) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onToggle}
      ref={(el) => {
        if (el) el.indeterminate = indeterminate;
      }}
    />
  );
}