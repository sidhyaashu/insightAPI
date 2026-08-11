"use client";

import * as React from "react";

interface CollapsibleContextValue {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CollapsibleContext = React.createContext<CollapsibleContextValue | null>(null);

export function Collapsible({
  open,
  defaultOpen = false,
  onOpenChange,
  children,
  className,
}: {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
  className?: string;
}) {
  const [isOpenState, setIsOpenState] = React.useState(defaultOpen);
  const isControlled = open !== undefined;
  const isOpen = isControlled ? open : isOpenState;

  const handleOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      if (!isControlled) {
        setIsOpenState(nextOpen);
      }
      onOpenChange?.(nextOpen);
    },
    [isControlled, onOpenChange]
  );

  return (
    <CollapsibleContext.Provider value={{ open: isOpen, onOpenChange: handleOpenChange }}>
      <div className={className}>{children}</div>
    </CollapsibleContext.Provider>
  );
}

export function CollapsibleTrigger({
  children,
  className,
  onClick,
  ...props
}: React.HTMLAttributes<HTMLButtonElement>) {
  const context = React.useContext(CollapsibleContext);
  if (!context) return null;

  return (
    <button
      type="button"
      className={className}
      onClick={(e) => {
        onClick?.(e);
        context.onOpenChange(!context.open);
      }}
      {...props}
    >
      {children}
    </button>
  );
}

export function CollapsibleContent({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const context = React.useContext(CollapsibleContext);
  if (!context || !context.open) return null;

  return (
    <div className={className} {...props}>
      {children}
    </div>
  );
}
