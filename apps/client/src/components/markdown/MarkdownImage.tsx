"use client";

import React, { useState, memo } from "react";
import { ImageIcon, AlertCircleIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { isSafeUrl } from "./markdown-utils";

export const MarkdownImage = memo(
  ({
    src,
    alt,
    className,
    ...props
  }: React.ComponentPropsWithoutRef<"img">) => {
    const [isLoaded, setIsLoaded] = useState(false);
    const [hasError, setHasError] = useState(false);

    const srcStr = typeof src === "string" ? src : undefined;

    if (!srcStr || !isSafeUrl(srcStr)) {
      return (
        <div className="my-3 p-3 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center gap-2">
          <AlertCircleIcon className="size-4 shrink-0" />
          <span>Invalid or unsafe image source</span>
        </div>
      );
    }

    if (hasError) {
      return (
        <div className="my-3 p-4 rounded-xl border border-border/70 bg-muted/30 text-muted-foreground text-xs flex items-center gap-2.5 max-w-md">
          <ImageIcon className="size-5 shrink-0 opacity-60" />
          <div className="min-w-0">
            <p className="font-medium text-foreground/80 truncate">
              {alt || "Image preview"}
            </p>
            <p className="text-[11px] opacity-75 truncate">
              Could not load image from URL
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="my-3.5 relative inline-block max-w-full overflow-hidden rounded-xl border border-border/60 bg-muted/20 shadow-xs">
        {!isLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted/40 animate-pulse min-h-[120px] w-full">
            <ImageIcon className="size-6 text-muted-foreground/40" />
          </div>
        )}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={alt || "Markdown visual content"}
          loading="lazy"
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
          className={cn(
            "max-w-full h-auto object-contain rounded-xl transition-opacity duration-300",
            isLoaded ? "opacity-100" : "opacity-0",
            className
          )}
          {...props}
        />
        {alt && (
          <div className="px-2 py-1 text-center text-[11px] text-muted-foreground bg-muted/30 border-t border-border/30 truncate">
            {alt}
          </div>
        )}
      </div>
    );
  }
);

MarkdownImage.displayName = "MarkdownImage";
