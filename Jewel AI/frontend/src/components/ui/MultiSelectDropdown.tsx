import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";

type MultiSelectProps = {
  label?: string;
  options: string[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
};

/** Accessible multi-select dropdown with search filter, sorting, and chips. */
export function MultiSelectDropdown({
  label,
  options,
  selectedValues,
  onChange,
  placeholder = "Select...",
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const buttonId = useId();

  // Sort options alphabetically
  const sortedOptions = [...options].sort((a, b) => a.localeCompare(b));

  // Filter options based on search query
  const filteredOptions = sortedOptions.filter((opt) =>
    opt.toLowerCase().includes(query.toLowerCase().trim()),
  );

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (open) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [open]);

  const toggle = (val: string) => {
    onChange(
      selectedValues.includes(val)
        ? selectedValues.filter((v) => v !== val)
        : [...selectedValues, val],
    );
  };

  const handleSelectAll = () => {
    const allFiltered = Array.from(new Set([...selectedValues, ...filteredOptions]));
    onChange(allFiltered);
  };

  const handleClearAll = () => {
    onChange([]);
  };

  return (
    <div ref={ref} className="relative">
      {label && (
        <div className="flex items-center justify-between mb-1">
          <label className="ui-label" id={`${buttonId}-label`}>
            {label}
          </label>
          {selectedValues.length > 0 ? (
            <span className="text-[10px] font-semibold text-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)] px-1.5 py-0.5 rounded">
              {selectedValues.length} selected
            </span>
          ) : null}
        </div>
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
        className="ui-input flex items-center justify-between gap-2 text-left cursor-pointer"
      >
        <span className="truncate text-xs font-medium">
          {selectedValues.length ? selectedValues.join(", ") : placeholder}
        </span>
        <ChevronDown
          className={`size-4 shrink-0 text-jewel-ink-muted transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-[var(--jewel-border)] bg-white py-1.5 shadow-card animate-in fade-in-50 zoom-in-95">
          {/* Search Input Bar */}
          <div className="px-2 pb-1.5 border-b border-[var(--jewel-hairline)] flex items-center gap-1.5">
            <Search className="size-3.5 shrink-0 text-slate-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search jewelry..."
              className="w-full bg-transparent text-xs outline-none placeholder:text-slate-400 py-1"
            />
            {query ? (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="size-3.5" />
              </button>
            ) : null}
          </div>

          {/* Quick Actions Header */}
          <div className="flex items-center justify-between px-3 py-1 border-b border-[var(--jewel-hairline)] bg-slate-50/50 text-[10px] font-semibold text-slate-500">
            <button
              type="button"
              onClick={handleSelectAll}
              className="hover:text-[var(--jewel-accent)]"
            >
              Select All
            </button>
            <button
              type="button"
              onClick={handleClearAll}
              className="hover:text-rose-600"
            >
              Clear All
            </button>
          </div>

          {/* Options List */}
          <ul
            id={listId}
            role="listbox"
            aria-multiselectable="true"
            aria-labelledby={label ? `${buttonId}-label` : buttonId}
            className="max-h-52 overflow-y-auto py-1"
          >
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt) => {
                const selected = selectedValues.includes(opt);
                return (
                  <li key={opt} role="option" aria-selected={selected}>
                    <button
                      type="button"
                      className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors ${
                        selected
                          ? "bg-[var(--jewel-accent-soft)] font-semibold text-[var(--jewel-accent)]"
                          : "text-slate-700 hover:bg-slate-50"
                      }`}
                      onClick={() => toggle(opt)}
                    >
                      <span
                        className={`grid size-4 shrink-0 place-items-center rounded-md border transition-colors ${
                          selected
                            ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent)] text-white"
                            : "border-slate-300 bg-white"
                        }`}
                      >
                        {selected && <Check className="size-3 stroke-[3]" />}
                      </span>
                      <span className="truncate">{opt}</span>
                    </button>
                  </li>
                );
              })
            ) : (
              <li className="px-3 py-3 text-center text-xs text-slate-400 font-medium">
                No matching jewelry types found
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
