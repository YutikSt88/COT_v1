import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

type ButtonVariant = "default" | "ghost";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: ButtonVariant;
}

const variantStyles: Record<ButtonVariant, string> = {
  default: "bg-panel border border-border text-foreground hover:bg-[#171d25]",
  ghost: "bg-transparent text-muted hover:text-foreground hover:bg-[#171d25]",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(
          "inline-flex h-9 items-center justify-center rounded-md px-3 text-sm font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-neutral",
          variantStyles[variant],
          className,
        )}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
