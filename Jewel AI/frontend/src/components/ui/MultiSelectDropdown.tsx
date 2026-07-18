import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

type MultiSelectProps = {
  label?: string;
  options: string[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
};

/** Accessible multi-select listbox with chips. */
export function MultiSelectDropdown({
  label,
  options,
  selectedValues,
  onChange,
  placeholder = "Select...",
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const listId = useId();
  const buttonId = useId();

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (val: string) => {
    onChange(
      selectedValues.includes(val)
        ? selectedValues.filter((v) => v !== val)
        : [...selectedValues, val],
    );
  };

  return (
    <div ref={ref} className="relative">
      {label && (
        <label className="ui-label" id={`${buttonId}-label`}>
          {label}
        </label>
      )}
      <button
        type="button"
        id={buttonId}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-labelledby={label ? `${buttonId}-label` : undefined}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "ArrowDown" && !open) {
            e.preventDefault();
            setOpen(true);
          }
        }}
        className="ui-input flex items-center justify-between gap-2 text-left"
      >
        <span className="truncate">
          {selectedValues.length ? selectedValues.join(", ") : placeholder}
        </span>
        <ChevronDown className={`size-4 shrink-0 text-jewel-ink-muted transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul
          id={listId}
          role="listbox"
          aria-multiselectable="true"
          aria-labelledby={label ? `${buttonId}-label` : buttonId}
          className="absolute z-30 mt-1 max-h-48 w-full overflow-auto rounded-jewel-md border border-jewel-border bg-jewel-surface py-1 shadow-sticky"
        >
          {options.map((opt) => {
            const selected = selectedValues.includes(opt);
            return (
              <li key={opt} role="option" aria-selected={selected}>
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-jewel-ink hover:bg-jewel-muted"
                  onClick={() => toggle(opt)}
                >
                  <span
                    className={`grid size-4 place-items-center rounded-sm border ${
                      selected
                        ? "border-jewel-accent bg-jewel-accent text-white"
                        : "border-jewel-border"
                    }`}
                  >
                    {selected && <Check className="size-3" />}
                  </span>
                  {opt}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
