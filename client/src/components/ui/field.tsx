import * as React from "react"
import { cn } from "@/lib/utils"

export function FieldGroup({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex flex-col gap-4", className)} {...props}>
      {children}
    </div>
  )
}

export function Field({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex flex-col gap-2", className)} {...props}>
      {children}
    </div>
  )
}

export function FieldLabel({
  className,
  children,
  htmlFor,
  ...props
}: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn("text-xs font-semibold text-foreground tracking-tight cursor-pointer", className)}
      {...props}
    >
      {children}
    </label>
  )
}

export function FieldDescription({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn("text-xs text-muted-foreground", className)} {...props}>
      {children}
    </p>
  )
}

export function FieldSeparator({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("relative my-2 flex items-center justify-center text-xs uppercase", className)} {...props}>
      <div className="absolute inset-0 flex items-center">
        <span className="w-full border-t border-border" />
      </div>
      <span className="relative bg-background px-2 text-muted-foreground text-[10px] font-semibold">
        {children}
      </span>
    </div>
  )
}
