import { ReactNode, useState } from "react";
import { ChevronDown } from "lucide-react";

type AccordionProps = {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
};

export function Accordion({ title, defaultOpen = true, children }: AccordionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-gray-100 last:border-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between py-3 px-4 text-left text-[11px] font-bold uppercase tracking-wider text-gray-900 transition-colors hover:bg-gray-50"
      >
        {title}
        <ChevronDown
          className={`size-4 text-gray-500 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ${
          open ? "max-h-auto opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        {open && <div className="p-4 pt-1 space-y-4">{children}</div>}
      </div>
    </div>
  );
}
