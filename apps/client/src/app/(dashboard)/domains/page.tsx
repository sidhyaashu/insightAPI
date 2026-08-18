"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  IconShieldCheck,
  IconShieldLock,
  IconPlus,
  IconRefresh,
  IconCheck,
  IconCopy,
  IconTrash,
  IconAlertTriangle,
  IconWorld,
  IconFileText,
  IconServer,
  IconExternalLink,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { domainsApi } from "@/features/domains/api/domains.api";
import type { VerifiedDomain } from "@/lib/api-client/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function DomainsManagementPage() {
  const [domains, setDomains] = useState<VerifiedDomain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add Domain Modal State
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newDomainInput, setNewDomainInput] = useState("");
  const [isSubmittingDomain, setIsSubmittingDomain] = useState(false);

  // Active Instructions Modal State
  const [selectedDomain, setSelectedDomain] = useState<VerifiedDomain | null>(null);
  const [isCheckingDomain, setIsCheckingDomain] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const loadDomains = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await domainsApi.listDomains();
      setDomains(list);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load verified domains.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDomains();
  }, [loadDomains]);

  const handleCopy = (text: string, fieldKey: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldKey);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleInitiateVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDomainInput.trim()) return;

    setIsSubmittingDomain(true);
    try {
      const record = await domainsApi.verifyDomain(newDomainInput.trim());
      setNewDomainInput("");
      setAddModalOpen(false);
      setSelectedDomain(record);
      await loadDomains();
      toast.success(`Domain ${record.domain} registered. Follow instructions to verify ownership.`);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to register domain.";
      toast.error(msg);
    } finally {
      setIsSubmittingDomain(false);
    }
  };

  const handleCheckVerification = async (domain: string, method: string = "auto") => {
    setIsCheckingDomain(true);
    try {
      const res = await domainsApi.checkVerification(domain, method);
      if (res.verified) {
        toast.success(`✓ Domain ${domain} verified successfully via ${res.verification_method}!`);
        if (res.domain_record) {
          setSelectedDomain(res.domain_record);
        }
        await loadDomains();
      } else {
        toast.error(res.detail || "Verification challenge not detected yet. Please allow DNS propagation.");
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Verification check failed.";
      toast.error(msg);
    } finally {
      setIsCheckingDomain(false);
    }
  };

  const handleDeleteDomain = async (domain: string) => {
    if (!confirm(`Are you sure you want to remove domain verification for ${domain}?`)) return;

    try {
      await domainsApi.deleteDomain(domain);
      toast.success(`Domain ${domain} removed.`);
      if (selectedDomain?.domain === domain) {
        setSelectedDomain(null);
      }
      await loadDomains();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to remove domain.";
      toast.error(msg);
    }
  };

  const handleToggleActiveTesting = async (domain: string, currentVal: boolean) => {
    const newVal = !currentVal;
    try {
      await domainsApi.setActiveTestingOptIn(domain, newVal);
      toast.success(`Active security testing ${newVal ? "enabled" : "disabled"} for ${domain}.`);
      setDomains((prev) =>
        prev.map((d) => (d.domain === domain ? { ...d, active_testing_opt_in: newVal } : d))
      );
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update active testing status.");
    }
  };

  const verifiedCount = domains.filter((d) => d.is_verified).length;
  const pendingCount = domains.length - verifiedCount;
  const activeTestingCount = domains.filter((d) => d.is_verified && d.active_testing_opt_in).length;

  return (
    <div className="p-4 sm:p-8 space-y-6 max-w-7xl mx-auto w-full font-sans pb-28">
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs">
            <IconWorld className="size-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              Verified Domains & Legal Compliance
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Verify domain ownership via DNS TXT records or well-known files to bypass per-crawl ToS prompts and authorize active security scans.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadDomains} className="gap-1.5 text-xs h-8">
            <IconRefresh className="size-3.5" /> Refresh
          </Button>
          <Button size="sm" onClick={() => setAddModalOpen(true)} className="gap-1.5 text-xs bg-primary text-primary-foreground font-semibold h-8 shadow-xs">
            <IconPlus className="size-3.5" /> Add New Domain
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-xs">
          <div className="text-[11px] text-muted-foreground font-mono uppercase mb-1">Total Targets</div>
          <div className="text-2xl font-extrabold font-mono text-foreground">{domains.length}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Registered API apex domains</div>
        </div>
        <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 shadow-xs">
          <div className="text-[11px] text-emerald-500 font-mono uppercase mb-1">Verified (Instant Crawl)</div>
          <div className="text-2xl font-extrabold font-mono text-emerald-400">{verifiedCount}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Challenge passed</div>
        </div>
        <div className="p-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 shadow-xs">
          <div className="text-[11px] text-amber-500 font-mono uppercase mb-1">Pending Challenge</div>
          <div className="text-2xl font-extrabold font-mono text-amber-400">{pendingCount}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Awaiting DNS propagation</div>
        </div>
        <div className="p-4 rounded-2xl border border-purple-500/20 bg-purple-500/5 shadow-xs">
          <div className="text-[11px] text-purple-400 font-mono uppercase mb-1">Active Security Opt-In</div>
          <div className="text-2xl font-extrabold font-mono text-purple-400">{activeTestingCount}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Authorized for sandbox probes</div>
        </div>
      </div>

      {/* Domain Table / List */}
      <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
        <div className="p-4 border-b border-border/40 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Registered Targets</h2>
          <span className="text-xs font-mono text-muted-foreground">{domains.length} records</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-muted-foreground font-mono animate-pulse">
            Loading domain records…
          </div>
        ) : error ? (
          <div className="p-8 text-center text-xs text-destructive font-medium">
            {error}
          </div>
        ) : domains.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center gap-3">
            <div className="size-12 rounded-2xl bg-muted/40 flex items-center justify-center text-muted-foreground">
              <IconWorld className="size-6" />
            </div>
            <p className="text-sm font-semibold text-foreground">No domains registered yet</p>
            <p className="text-xs text-muted-foreground max-w-sm">
              Add your target domains to verify ownership and avoid manual authorization confirmations on each crawl.
            </p>
            <Button size="sm" onClick={() => setAddModalOpen(true)} className="text-xs mt-2">
              <IconPlus className="size-3.5 mr-1" /> Add Your First Domain
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-border/40">
            {domains.map((dom) => (
              <div
                key={dom.id}
                className="p-4 flex items-center justify-between gap-4 flex-wrap hover:bg-muted/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                    <IconWorld className="size-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-bold font-mono text-foreground">{dom.domain}</span>
                      {dom.is_verified ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono border-emerald-500/40 text-emerald-500 bg-emerald-500/10 px-2 py-0.5"
                        >
                          ✓ Verified ({dom.verification_method || "DNS"})
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono border-amber-500/40 text-amber-500 bg-amber-500/10 px-2 py-0.5"
                        >
                          Pending Verification
                        </Badge>
                      )}

                      {dom.is_verified && (
                        <button
                          type="button"
                          onClick={() => handleToggleActiveTesting(dom.domain, !!dom.active_testing_opt_in)}
                          className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold transition-colors cursor-pointer border ${
                            dom.active_testing_opt_in
                              ? "bg-purple-500/15 border-purple-500/40 text-purple-400"
                              : "bg-muted/40 border-border text-muted-foreground hover:text-foreground"
                          }`}
                          title="Click to toggle active security testing opt-in"
                        >
                          <IconShieldLock className="size-3" />
                          <span>Active Testing: {dom.active_testing_opt_in ? "OPTED IN" : "OFF"}</span>
                        </button>
                      )}
                    </div>
                    <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                      {dom.is_verified && dom.verified_at
                        ? `Verified on ${new Date(dom.verified_at).toLocaleDateString()}`
                        : `Registered on ${new Date(dom.created_at).toLocaleDateString()}`}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedDomain(dom)}
                    className="text-xs gap-1"
                  >
                    <IconFileText className="size-3.5" />
                    Instructions
                  </Button>
                  {!dom.is_verified && (
                    <Button
                      size="sm"
                      onClick={() => handleCheckVerification(dom.domain)}
                      disabled={isCheckingDomain}
                      className="text-xs gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                    >
                      <IconCheck className="size-3.5" />
                      Verify Now
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteDomain(dom.domain)}
                    className="text-xs text-muted-foreground hover:text-destructive"
                  >
                    <IconTrash className="size-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Domain Dialog */}
      <Dialog open={addModalOpen} onOpenChange={setAddModalOpen}>
        <DialogContent className="max-w-md p-6 rounded-2xl bg-card text-card-foreground border border-border">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <IconWorld className="size-5 text-primary" />
              Register Domain for Verification
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Enter your API hostname or target apex domain (e.g. <code>api.example.com</code> or <code>example.com</code>).
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleInitiateVerification} className="space-y-4 py-2">
            <div>
              <label className="text-xs font-semibold text-foreground block mb-1.5">
                Domain / Target URL
              </label>
              <Input
                placeholder="api.example.com"
                value={newDomainInput}
                onChange={(e) => setNewDomainInput(e.target.value)}
                className="font-mono text-xs"
                autoFocus
              />
            </div>

            <DialogFooter className="gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setAddModalOpen(false)} className="text-xs">
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmittingDomain || !newDomainInput.trim()} className="text-xs bg-primary text-primary-foreground">
                {isSubmittingDomain ? "Registering…" : "Register & Get Token"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Setup Instructions Dialog */}
      <Dialog open={!!selectedDomain} onOpenChange={(open) => !open && setSelectedDomain(null)}>
        <DialogContent className="max-w-xl p-6 rounded-2xl bg-card text-card-foreground border border-border">
          <DialogHeader>
            <div className="flex items-center justify-between gap-2">
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <IconShieldCheck className="size-5 text-primary" />
                Ownership Challenge: {selectedDomain?.domain}
              </DialogTitle>
              {selectedDomain?.is_verified ? (
                <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/30 text-[10px] font-mono">
                  ✓ Verified
                </Badge>
              ) : (
                <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/30 text-[10px] font-mono">
                  Pending Challenge
                </Badge>
              )}
            </div>
            <DialogDescription className="text-xs text-muted-foreground">
              Choose one of the two verification methods below to prove administrative control over this target.
            </DialogDescription>
          </DialogHeader>

          {selectedDomain && (
            <div className="space-y-4 py-2 text-xs">
              <Tabs defaultValue="dns" className="w-full">
                <TabsList className="grid grid-cols-2 text-xs">
                  <TabsTrigger value="dns" className="text-xs flex items-center gap-1.5">
                    <IconServer className="size-3.5" /> Method 1: DNS TXT
                  </TabsTrigger>
                  <TabsTrigger value="http" className="text-xs flex items-center gap-1.5">
                    <IconFileText className="size-3.5" /> Method 2: Well-Known File
                  </TabsTrigger>
                </TabsList>

                {/* DNS TXT Instructions */}
                <TabsContent value="dns" className="space-y-3 mt-3">
                  <p className="text-muted-foreground text-xs">
                    Add a TXT record to your domain's DNS settings at your registrar (Cloudflare, Route53, Namecheap, etc.):
                  </p>

                  <div className="space-y-2 bg-muted/30 p-3 rounded-xl border border-border/50 font-mono text-[11px]">
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-sans font-semibold">Record Type</span>
                      <span className="text-foreground font-bold">TXT</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-sans font-semibold">Host / Name</span>
                      <div className="flex items-center justify-between gap-2 bg-background p-1.5 rounded-lg border border-border/40 mt-1">
                        <span className="truncate">{selectedDomain.instructions.dns.host}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(selectedDomain.instructions.dns.host, "host")}
                          className="size-6 p-0 shrink-0"
                        >
                          {copiedField === "host" ? <IconCheck className="size-3 text-emerald-500" /> : <IconCopy className="size-3" />}
                        </Button>
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-sans font-semibold">Value / Content</span>
                      <div className="flex items-center justify-between gap-2 bg-background p-1.5 rounded-lg border border-border/40 mt-1">
                        <span className="truncate">{selectedDomain.instructions.dns.value}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(selectedDomain.instructions.dns.value, "dns_val")}
                          className="size-6 p-0 shrink-0"
                        >
                          {copiedField === "dns_val" ? <IconCheck className="size-3 text-emerald-500" /> : <IconCopy className="size-3" />}
                        </Button>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* HTTP Well-Known File Instructions */}
                <TabsContent value="http" className="space-y-3 mt-3">
                  <p className="text-muted-foreground text-xs">
                    Upload a plain text file accessible over HTTP(S) at the following location:
                  </p>

                  <div className="space-y-2 bg-muted/30 p-3 rounded-xl border border-border/50 font-mono text-[11px]">
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-sans font-semibold">Target URL</span>
                      <div className="flex items-center justify-between gap-2 bg-background p-1.5 rounded-lg border border-border/40 mt-1">
                        <span className="truncate">{selectedDomain.instructions.well_known.target_url}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(selectedDomain.instructions.well_known.target_url, "url")}
                          className="size-6 p-0 shrink-0"
                        >
                          {copiedField === "url" ? <IconCheck className="size-3 text-emerald-500" /> : <IconCopy className="size-3" />}
                        </Button>
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-sans font-semibold">Required File Body</span>
                      <div className="flex items-center justify-between gap-2 bg-background p-1.5 rounded-lg border border-border/40 mt-1">
                        <span className="truncate">{selectedDomain.instructions.well_known.content}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(selectedDomain.instructions.well_known.content, "http_val")}
                          className="size-6 p-0 shrink-0"
                        >
                          {copiedField === "http_val" ? <IconCheck className="size-3 text-emerald-500" /> : <IconCopy className="size-3" />}
                        </Button>
                      </div>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}

          <DialogFooter className="flex items-center justify-between sm:justify-between w-full gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setSelectedDomain(null)}
              className="text-xs"
            >
              Close
            </Button>
            {selectedDomain && !selectedDomain.is_verified && (
              <Button
                type="button"
                size="sm"
                onClick={() => handleCheckVerification(selectedDomain.domain)}
                disabled={isCheckingDomain}
                className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white gap-1"
              >
                {isCheckingDomain ? "Verifying..." : "Verify Ownership Now"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
