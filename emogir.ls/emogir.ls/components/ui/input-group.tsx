interface InputGroupProps {
  prefix?: string;
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  name?: string;
  defaultValue?: string;
  className?: string;
  type?: string;
  label?: string;
}

export function InputGroup({
  prefix,
  placeholder,
  value,
  onChange,
  name,
  defaultValue,
  className,
  type,
  label,
}: InputGroupProps) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="text-sm font-medium text-white/80">{label}</label>
      )}
      <div className={`group flex items-stretch ${className}`}>
        {prefix && (
          <span className="flex items-center bg-black/20 border border-r-0 border-primary/10 rounded-l-lg px-3 py-2 text-sm text-white/60 transition-colors group-focus-within:border-primary/30 whitespace-nowrap">
            {prefix}
          </span>
        )}
        <input
          type={type || "text"}
          name={name}
          value={value}
          defaultValue={defaultValue}
          onChange={(e) => onChange?.(e.target.value)}
          className={`flex-1 bg-black/20 border border-primary/10 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-primary/30 transition-colors ${
            prefix
              ? "rounded-r-lg border-l-0 group-focus-within:border-l-0 pl-0.5 pr-3"
              : "rounded-lg px-3"
          }`}
          placeholder={placeholder}
        />
      </div>
    </div>
  );
}
