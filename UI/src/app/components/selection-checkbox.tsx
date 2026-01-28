import { Check } from "lucide-react";

export function SelectionCheckbox({
  checked,
  onToggle,
}: {
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
        checked
          ? "bg-blue-600 border-blue-600 text-white"
          : "border-gray-400 hover:border-blue-500"
      }`}
    >
      {checked && <Check className="w-3 h-3" />}
    </button>
  );
}
