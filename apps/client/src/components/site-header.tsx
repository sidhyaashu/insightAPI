"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  IconUser,
  IconHelp,
  IconCreditCard,
  IconKey,
  IconFileText,
  IconLogout,
  IconChevronDown,
} from "@tabler/icons-react";

import { useAppSelector, useAppDispatch } from "@/store";
import { authApi } from "@/features/auth/api/auth.api";
import { clearCredentials } from "@/features/auth/store/authSlice";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
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

const PAGE_TITLES: Record<string, string> = {
  "/chat": "AI Chatbot Assistant",
  "/billing": "Billing & Subscriptions",
  "/settings": "Account Settings & Profile",
};

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);

  const title = PAGE_TITLES[pathname] || "AI Chatbot";

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

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center gap-3">
        <SidebarTrigger className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted/60 transition cursor-pointer" />
        <Separator orientation="vertical" className="h-4" />
        <h1 className="text-sm font-semibold text-foreground tracking-tight">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Light / Dark Mode Toggle */}
        <ThemeToggle />

        {/* Tier Badge */}
        {user?.tier === "ADMIN" ? (
          <Badge variant="outline" className="text-[10px] px-2 py-0.5 font-mono border-primary/40 text-primary">
            ADMIN
          </Badge>
        ) : (
          <Badge variant="outline" className="text-[10px] px-2 py-0.5 font-mono text-muted-foreground">
            {user?.tier || "FREE"} TIER
          </Badge>
        )}

        {/* Top Right User Avatar Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2 rounded-full p-0.5 hover:ring-2 hover:ring-primary/20 transition focus:outline-none cursor-pointer border-none bg-transparent">
            <div className="flex size-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold text-xs shadow-sm">
              {getInitials(user?.name, user?.email)}
            </div>
            <IconChevronDown className="size-3 text-muted-foreground hidden sm:block" />
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-56 p-2 shadow-lg rounded-xl">
            <DropdownMenuGroup>
              <DropdownMenuLabel className="font-normal p-2">
                <div className="flex flex-col gap-1">
                  <p className="text-xs font-semibold leading-none text-foreground">
                    {user?.name || "Developer"}
                  </p>
                  <p className="text-[11px] leading-none text-muted-foreground truncate">
                    {user?.email || "sidhyaasutosh@gmail.com"}
                  </p>
                  <div className="pt-1">
                    {user?.tier === "ADMIN" ? (
                      <span className="inline-block text-[9px] bg-primary/10 text-primary border border-primary/20 px-1.5 py-0.5 rounded font-mono font-semibold">
                        ADMIN ACCESS
                      </span>
                    ) : (
                      <span className="inline-block text-[9px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded font-mono">
                        {user?.tier || "FREE"} Plan
                      </span>
                    )}
                  </div>
                </div>
              </DropdownMenuLabel>
            </DropdownMenuGroup>

            <DropdownMenuSeparator />

            <DropdownMenuGroup>
              <DropdownMenuItem onClick={() => router.push("/settings")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconUser className="size-4 text-muted-foreground" />
                <span>Profile & Account</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push("/billing")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconCreditCard className="size-4 text-muted-foreground" />
                <span>Billing & Subscriptions</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push("/docs")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconFileText className="size-4 text-muted-foreground" />
                <span>Documentation Reference</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push("/docs#crawling-policy")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconHelp className="size-4 text-muted-foreground" />
                <span>Support & Community</span>
              </DropdownMenuItem>
            </DropdownMenuGroup>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              onClick={handleLogout}
              className="cursor-pointer text-xs flex items-center gap-2 py-2 text-destructive focus:bg-destructive/10"
            >
              <IconLogout className="size-4" />
              <span>Sign Out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
