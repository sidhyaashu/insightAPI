"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  IconUser,
  IconCreditCard,
  IconShieldLock,
  IconKey,
  IconLogout,
  IconBrain,
  IconFileText,
  IconWorld,
  IconSparkles,
} from "@tabler/icons-react";
import { useAppSelector, useAppDispatch } from "@/store";
import { authApi } from "@/features/auth/api/auth.api";
import { clearCredentials } from "@/features/auth/store/authSlice";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function UserAvatarMenu() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);
  const [open, setOpen] = React.useState(false);
  const closeTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    dispatch(clearCredentials());
    router.replace("/login");
  };

  const getInitials = (name?: string | null, email?: string | null) => {
    if (name) {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    if (email) {
      return email.slice(0, 2).toUpperCase();
    }
    return "AS";
  };

  const handleMouseEnter = () => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    setOpen(true);
  };

  const handleMouseLeave = () => {
    closeTimeoutRef.current = setTimeout(() => {
      setOpen(false);
    }, 200);
  };

  return (
    <div
      className="fixed top-3.5 right-5 z-50"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          className="relative flex size-9 items-center justify-center rounded-full bg-card hover:bg-muted/80 border border-border/80 text-foreground font-bold text-xs shadow-md transition-transform hover:scale-105 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/40 group"
          title={user?.name || user?.email || "Account"}
        >
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.name || "User Avatar"}
              className="size-full rounded-full object-cover"
            />
          ) : (
            <span>{getInitials(user?.name, user?.email)}</span>
          )}
          {/* Online green indicator badge */}
          <span className="absolute bottom-0 right-0 size-2.5 rounded-full bg-emerald-500 ring-2 ring-background shadow-xs" />
        </DropdownMenuTrigger>

        <DropdownMenuContent
          align="end"
          sideOffset={8}
          className="w-72 p-2 shadow-2xl rounded-2xl bg-card/95 backdrop-blur-xl border border-border text-card-foreground animate-in fade-in zoom-in-95 duration-150"
        >
          {/* User Profile Card */}
          <DropdownMenuGroup>
            <DropdownMenuLabel className="font-normal p-2.5">
              <div className="flex items-center gap-3">
                <div className="relative flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-sm shadow-xs">
                  {user?.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user.name || "Avatar"}
                      className="size-full rounded-full object-cover"
                    />
                  ) : (
                    getInitials(user?.name, user?.email)
                  )}
                </div>
                <div className="flex flex-col min-w-0 space-y-0.5">
                  <span className="text-xs font-bold leading-tight text-foreground truncate">
                    {user?.name || "Asutosh Sidhya"}
                  </span>
                  <span className="text-[11px] leading-tight text-muted-foreground truncate font-mono">
                    {user?.email || "sidhyaasutosh@gmail.com"}
                  </span>
                  <div className="pt-1 flex items-center gap-1.5">
                    <Badge
                      variant="outline"
                      className="text-[9px] font-mono px-1.5 py-0 border-primary/40 text-primary bg-primary/10 font-semibold"
                    >
                      {user?.tier || "FREE"}
                    </Badge>
                    <Link
                      href="/billing"
                      onClick={() => setOpen(false)}
                      className="text-[10px] text-primary hover:underline font-semibold ml-1 flex items-center gap-0.5"
                    >
                      <IconSparkles className="size-3" />
                      <span>Upgrade</span>
                    </Link>
                  </div>
                </div>
              </div>
            </DropdownMenuLabel>
          </DropdownMenuGroup>

          <DropdownMenuSeparator className="my-1 border-border/40" />

          {/* Core Navigation Links */}
          <DropdownMenuGroup className="space-y-0.5">
            <DropdownMenuItem
              onClick={() => {
                setOpen(false);
                router.push("/settings");
              }}
              className="cursor-pointer text-xs flex items-center gap-2.5 py-2 px-2.5 rounded-xl hover:bg-muted/80"
            >
              <IconUser className="size-4 text-muted-foreground" />
              <span>Profile & Account</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => {
                setOpen(false);
                router.push("/billing");
              }}
              className="cursor-pointer text-xs flex items-center gap-2.5 py-2 px-2.5 rounded-xl hover:bg-muted/80"
            >
              <IconCreditCard className="size-4 text-muted-foreground" />
              <span>Billing & Subscription</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => {
                setOpen(false);
                router.push("/security");
              }}
              className="cursor-pointer text-xs flex items-center gap-2.5 py-2 px-2.5 rounded-xl hover:bg-muted/80"
            >
              <IconShieldLock className="size-4 text-muted-foreground" />
              <span>Security Center</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => {
                setOpen(false);
                router.push("/domains");
              }}
              className="cursor-pointer text-xs flex items-center gap-2.5 py-2 px-2.5 rounded-xl hover:bg-muted/80"
            >
              <IconWorld className="size-4 text-muted-foreground" />
              <span>Verified Domains</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => {
                setOpen(false);
                router.push("/auth-profiles");
              }}
              className="cursor-pointer text-xs flex items-center gap-2.5 py-2 px-2.5 rounded-xl hover:bg-muted/80"
            >
              <IconKey className="size-4 text-muted-foreground" />
              <span>Auth Profiles</span>
            </DropdownMenuItem>
          </DropdownMenuGroup>

          <DropdownMenuSeparator className="my-1 border-border/40" />

          {/* Theme & Appearance */}
          <div className="px-2.5 py-2 flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">Theme</span>
            <ThemeToggle />
          </div>

          <DropdownMenuSeparator className="my-1 border-border/40" />

          {/* Logout */}
          <DropdownMenuItem
            onClick={() => {
              setOpen(false);
              handleLogout();
            }}
            className="cursor-pointer text-xs flex items-center gap-2.5 py-2 px-2.5 rounded-xl text-rose-500 focus:bg-rose-500/10 focus:text-rose-500 font-semibold"
          >
            <IconLogout className="size-4" />
            <span>Sign Out</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
