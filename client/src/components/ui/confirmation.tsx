"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ComponentProps, ReactNode } from "react";
import { createContext, useContext, useMemo } from "react";
import { AlertCircle, CheckCircle2, XCircle } from "lucide-react";

export type ToolUIPartApproval =
  | {
      id: string;
      approved?: boolean;
      reason?: string;
    }
  | undefined;

interface ConfirmationContextValue {
  approval: ToolUIPartApproval;
  state: "input-streaming" | "input-available" | "approval-requested" | "approval-responded" | "output-denied" | "output-available";
}

const ConfirmationContext = createContext<ConfirmationContextValue | null>(null);

const useConfirmation = () => {
  const context = useContext(ConfirmationContext);
  if (!context) {
    throw new Error("Confirmation components must be used within Confirmation");
  }
  return context;
};

export type ConfirmationProps = ComponentProps<"div"> & {
  approval?: ToolUIPartApproval;
  state: "input-streaming" | "input-available" | "approval-requested" | "approval-responded" | "output-denied" | "output-available";
};

export const Confirmation = ({
  className,
  approval,
  state,
  children,
  ...props
}: ConfirmationProps) => {
  const contextValue = useMemo(() => ({ approval, state }), [approval, state]);

  if (state === "input-streaming" || state === "input-available") {
    return null;
  }

  return (
    <ConfirmationContext.Provider value={contextValue}>
      <div
        className={cn(
          "flex flex-col gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-xs font-sans shadow-sm my-2",
          className
        )}
        {...props}
      >
        {children}
      </div>
    </ConfirmationContext.Provider>
  );
};

export type ConfirmationTitleProps = ComponentProps<"div">;

export const ConfirmationTitle = ({ className, children, ...props }: ConfirmationTitleProps) => (
  <div className={cn("flex items-center gap-2 font-semibold text-amber-500 text-sm", className)} {...props}>
    <AlertCircle className="size-4 shrink-0" />
    <span>{children}</span>
  </div>
);

export interface ConfirmationRequestProps {
  children?: ReactNode;
}

export const ConfirmationRequest = ({ children }: ConfirmationRequestProps) => {
  const { state } = useConfirmation();
  if (state !== "approval-requested") return null;
  return <div className="text-muted-foreground">{children}</div>;
};

export interface ConfirmationAcceptedProps {
  children?: ReactNode;
}

export const ConfirmationAccepted = ({ children }: ConfirmationAcceptedProps) => {
  const { approval, state } = useConfirmation();
  if (!approval?.approved || (state !== "approval-responded" && state !== "output-available")) {
    return null;
  }
  return (
    <div className="flex items-center gap-2 text-emerald-500 font-medium">
      <CheckCircle2 className="size-4" />
      <span>{children || "Action Approved & Executed"}</span>
    </div>
  );
};

export interface ConfirmationRejectedProps {
  children?: ReactNode;
}

export const ConfirmationRejected = ({ children }: ConfirmationRejectedProps) => {
  const { approval, state } = useConfirmation();
  if (approval?.approved !== false || (state !== "approval-responded" && state !== "output-denied")) {
    return null;
  }
  return (
    <div className="flex items-center gap-2 text-destructive font-medium">
      <XCircle className="size-4" />
      <span>{children || "Action Cancelled by User"}</span>
    </div>
  );
};

export type ConfirmationActionsProps = ComponentProps<"div">;

export const ConfirmationActions = ({ className, ...props }: ConfirmationActionsProps) => {
  const { state } = useConfirmation();
  if (state !== "approval-requested") return null;

  return (
    <div className={cn("flex items-center justify-end gap-2 pt-2 border-t border-amber-500/20", className)} {...props} />
  );
};

export type ConfirmationActionProps = ComponentProps<typeof Button>;

export const ConfirmationAction = (props: ConfirmationActionProps) => (
  <Button className="h-7 px-3 text-xs font-medium cursor-pointer" type="button" {...props} />
);
