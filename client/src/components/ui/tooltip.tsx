"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

interface TooltipContextType {
  isOpen: boolean;
  setIsOpen: React.Dispatch<React.SetStateAction<boolean>>;
  triggerRect: DOMRect | null;
  setTriggerRect: React.Dispatch<React.SetStateAction<DOMRect | null>>;
  side: "top" | "bottom" | "left" | "right";
  setSide: React.Dispatch<React.SetStateAction<"top" | "bottom" | "left" | "right">>;
}

const TooltipContext = createContext<TooltipContextType | null>(null);

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export interface TooltipProps {
  content?: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  align?: string;
  sideOffset?: number;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function Tooltip({
  content,
  children,
  side: defaultSide = "top",
  open: controlledOpen,
  onOpenChange,
}: TooltipProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);
  const [side, setSide] = useState<"top" | "bottom" | "left" | "right">(defaultSide);
  const [triggerRect, setTriggerRect] = useState<DOMRect | null>(null);
  const [mounted, setMounted] = useState(false);
  const triggerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isOpen = controlledOpen !== undefined ? controlledOpen : uncontrolledOpen;
  const setIsOpen: React.Dispatch<React.SetStateAction<boolean>> = (value) => {
    const next = typeof value === "function" ? value(isOpen) : value;
    if (controlledOpen === undefined) {
      setUncontrolledOpen(next);
    }
    onOpenChange?.(next);
  };

  const updateRect = () => {
    if (triggerRef.current) {
      setTriggerRect(triggerRef.current.getBoundingClientRect());
    }
  };

  // If content prop is provided directly: <Tooltip content="Hello"><button /></Tooltip>
  if (content !== undefined) {
    const sideOffset = 8;
    let style: React.CSSProperties = { position: "fixed", zIndex: 99999 };

    if (triggerRect) {
      if (side === "right") {
        style = {
          position: "fixed",
          zIndex: 99999,
          top: triggerRect.top + triggerRect.height / 2,
          left: triggerRect.right + sideOffset,
          transform: "translateY(-50%)",
        };
      } else if (side === "left") {
        style = {
          position: "fixed",
          zIndex: 99999,
          top: triggerRect.top + triggerRect.height / 2,
          left: triggerRect.left - sideOffset,
          transform: "translate(-100%, -50%)",
        };
      } else if (side === "bottom") {
        style = {
          position: "fixed",
          zIndex: 99999,
          top: triggerRect.bottom + sideOffset,
          left: triggerRect.left + triggerRect.width / 2,
          transform: "translateX(-50%)",
        };
      } else {
        // top
        style = {
          position: "fixed",
          zIndex: 99999,
          top: triggerRect.top - sideOffset,
          left: triggerRect.left + triggerRect.width / 2,
          transform: "translate(-50%, -100%)",
        };
      }
    }

    return (
      <>
        <div
          ref={triggerRef}
          className="inline-flex items-center justify-center"
          onMouseEnter={() => {
            updateRect();
            setIsOpen(true);
          }}
          onMouseLeave={() => setIsOpen(false)}
          onFocus={() => {
            updateRect();
            setIsOpen(true);
          }}
          onBlur={() => setIsOpen(false)}
        >
          {children}
        </div>
        {mounted &&
          isOpen &&
          triggerRect &&
          createPortal(
            <div
              role="tooltip"
              style={style}
              className="px-2.5 py-1 text-xs font-medium text-popover-foreground bg-popover border border-border rounded-md shadow-lg whitespace-nowrap pointer-events-none select-none animate-in fade-in-0 zoom-in-95"
            >
              {content}
            </div>,
            document.body
          )}
      </>
    );
  }

  // Compound component usage: <Tooltip><TooltipTrigger>...</TooltipTrigger><TooltipContent>...</TooltipContent></Tooltip>
  return (
    <TooltipContext.Provider
      value={{
        isOpen,
        setIsOpen,
        triggerRect,
        setTriggerRect,
        side,
        setSide,
      }}
    >
      {children}
    </TooltipContext.Provider>
  );
}

export function TooltipTrigger({
  children,
  asChild,
  render,
  ...props
}: {
  children?: React.ReactNode;
  asChild?: boolean;
  render?: any;
  [key: string]: any;
}) {
  const context = useContext(TooltipContext);
  const elementRef = useRef<HTMLElement | null>(null);

  if (!context) {
    return <>{children}</>;
  }

  const { setIsOpen, setTriggerRect } = context;

  const handleOpen = (e: React.SyntheticEvent) => {
    const target = (elementRef.current || e.currentTarget) as HTMLElement;
    if (target && typeof target.getBoundingClientRect === "function") {
      setTriggerRect(target.getBoundingClientRect());
    }
    setIsOpen(true);
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  const handlers = {
    onMouseEnter: (e: React.MouseEvent) => {
      handleOpen(e);
      props.onMouseEnter?.(e);
    },
    onMouseLeave: (e: React.MouseEvent) => {
      handleClose();
      props.onMouseLeave?.(e);
    },
    onFocus: (e: React.FocusEvent) => {
      handleOpen(e);
      props.onFocus?.(e);
    },
    onBlur: (e: React.FocusEvent) => {
      handleClose();
      props.onBlur?.(e);
    },
  };

  if (render) {
    return React.cloneElement(render, {
      ...props,
      ...handlers,
      ref: (node: any) => {
        elementRef.current = node;
        if (typeof render.ref === "function") render.ref(node);
        else if (render.ref) render.ref.current = node;
      },
    });
  }

  if (asChild && React.isValidElement(children)) {
    const child = children as React.ReactElement<any>;
    return React.cloneElement(child, {
      ...props,
      ...handlers,
      ref: (node: any) => {
        elementRef.current = node;
        if (typeof (child as any).ref === "function") (child as any).ref(node);
        else if ((child as any).ref) (child as any).ref.current = node;
      },
      onMouseEnter: (e: React.MouseEvent) => {
        handleOpen(e);
        child.props.onMouseEnter?.(e);
        props.onMouseEnter?.(e);
      },
      onMouseLeave: (e: React.MouseEvent) => {
        handleClose();
        child.props.onMouseLeave?.(e);
        props.onMouseLeave?.(e);
      },
      onFocus: (e: React.FocusEvent) => {
        handleOpen(e);
        child.props.onFocus?.(e);
        props.onFocus?.(e);
      },
      onBlur: (e: React.FocusEvent) => {
        handleClose();
        child.props.onBlur?.(e);
        props.onBlur?.(e);
      },
    });
  }

  return (
    <div
      ref={(node) => {
        elementRef.current = node;
      }}
      className="inline-flex items-center justify-center"
      {...props}
      {...handlers}
    >
      {children}
    </div>
  );
}

export function TooltipContent({
  children,
  className = "",
  side: propSide,
  align,
  sideOffset = 8,
  ...props
}: {
  children?: React.ReactNode;
  className?: string;
  side?: "top" | "bottom" | "left" | "right";
  align?: string;
  sideOffset?: number;
  [key: string]: any;
}) {
  const context = useContext(TooltipContext);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!context || !context.isOpen || !context.triggerRect || !mounted) {
    return null; // Don't render until hovered and mounted
  }

  const side = propSide || context.side || "right";
  const { triggerRect } = context;

  let style: React.CSSProperties = { position: "fixed", zIndex: 99999 };

  if (side === "right") {
    style = {
      position: "fixed",
      zIndex: 99999,
      top: triggerRect.top + triggerRect.height / 2,
      left: triggerRect.right + sideOffset,
      transform: "translateY(-50%)",
    };
  } else if (side === "left") {
    style = {
      position: "fixed",
      zIndex: 99999,
      top: triggerRect.top + triggerRect.height / 2,
      left: triggerRect.left - sideOffset,
      transform: "translate(-100%, -50%)",
    };
  } else if (side === "bottom") {
    style = {
      position: "fixed",
      zIndex: 99999,
      top: triggerRect.bottom + sideOffset,
      left: triggerRect.left + triggerRect.width / 2,
      transform: "translateX(-50%)",
    };
  } else {
    // top
    style = {
      position: "fixed",
      zIndex: 99999,
      top: triggerRect.top - sideOffset,
      left: triggerRect.left + triggerRect.width / 2,
      transform: "translate(-50%, -100%)",
    };
  }

  return createPortal(
    <div
      role="tooltip"
      style={style}
      className={cn(
        "px-2.5 py-1 text-xs font-medium text-popover-foreground bg-popover border border-border rounded-md shadow-lg whitespace-nowrap pointer-events-none select-none animate-in fade-in-0 zoom-in-95",
        className
      )}
      {...props}
    >
      {children}
    </div>,
    document.body
  );
}
