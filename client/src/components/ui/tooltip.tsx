"use client";

import React, { useState } from "react";

export interface TooltipProps {
  content?: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  align?: string;
  sideOffset?: number;
}

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export function TooltipTrigger({ children, render, ...props }: any) {
  if (render) {
    return React.cloneElement(render, props, children);
  }
  return <div {...props}>{children}</div>;
}

export function TooltipContent({ children, className = "", align, sideOffset, ...props }: any) {
  return (
    <div className={`px-3 py-1.5 text-xs bg-popover text-popover-foreground border rounded-md shadow-md ${className}`} {...props}>
      {children}
    </div>
  );
}

export function Tooltip({ content, children, side = "top" }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  const sideClasses = {
    top: "bottom-full mb-2 left-1/2 -translate-x-1/2",
    bottom: "top-full mt-2 left-1/2 -translate-x-1/2",
    left: "right-full mr-2 top-1/2 -translate-y-1/2",
    right: "left-full ml-2 top-1/2 -translate-y-1/2",
  };

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && content && (
        <div
          className={`absolute z-50 px-3 py-1.5 text-xs text-popover-foreground bg-popover border border-border rounded-md shadow-md whitespace-nowrap animate-in fade-in-0 zoom-in-95 ${sideClasses[side]}`}
        >
          {content}
        </div>
      )}
    </div>
  );
}
