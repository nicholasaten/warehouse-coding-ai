import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variantClasses: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-accent-deep",
  secondary: "border border-line-strong bg-transparent text-ink hover:bg-accent-wash",
  ghost: "bg-transparent text-ink-dim hover:bg-accent-wash hover:text-ink",
  danger: "bg-status-critical text-white hover:opacity-90",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }
>(({ className, variant = "primary", ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
      variantClasses[variant],
      className,
    )}
    {...props}
  />
));
Button.displayName = "Button";
