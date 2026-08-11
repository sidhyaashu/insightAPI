"use client";

import { useState, useEffect } from "react";
import { useAppSelector } from "@/store";
import apiClient from "@/lib/api-client";
import { toast } from "sonner";
import { KeyIcon, CopyIcon, Trash2Icon, PlusIcon, CheckIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface APIKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  raw_key?: string | null;
}

export default function SettingsPage() {
  const user = useAppSelector((state) => state.auth.user);
  const [keys, setKeys] = useState<APIKeyItem[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Fetch active API keys
  useEffect(() => {
    async function fetchKeys() {
      try {
        const res = await apiClient.get("/users/me/api-keys", {
          headers: {
            "X-User-ID": user?.id || "",
          },
        });
        if (res.data) {
          setKeys(res.data);
        }
      } catch {}
    }
    if (user?.id) fetchKeys();
  }, [user?.id]);

  const handleGenerateKey = async () => {
    setIsGenerating(true);
    try {
      const res = await apiClient.post(
        "/users/me/api-keys",
        { name: newKeyName.trim() || "CLI Access Key" },
        {
          headers: {
            "X-User-ID": user?.id || "",
          },
        }
      );

      if (res.data) {
        setKeys((prev) => [res.data, ...prev]);
        setGeneratedKey(res.data.raw_key || null);
        setNewKeyName("");
        toast.success("New API key generated successfully!");
      }
    } catch {
      toast.error("Failed to generate API key.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyKey = (keyString: string, id: string) => {
    navigator.clipboard.writeText(keyString);
    setCopiedId(id);
    toast.success("API key copied to clipboard!");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRevokeKey = async (id: string) => {
    try {
      await apiClient.delete(`/users/me/api-keys/${id}`, {
        headers: {
          "X-User-ID": user?.id || "",
        },
      });
      setKeys((prev) => prev.filter((k) => k.id !== id));
      toast.success("API key revoked successfully.");
    } catch {
      toast.error("Failed to revoke API key.");
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6 font-sans">
      <div>
        <h1 className="text-xl font-bold tracking-tight mb-1">Account & API Credentials</h1>
        <p className="text-xs text-muted-foreground">
          View user profile details and issue API keys for Python SDK & CLI authentication (`insightapi login`).
        </p>
      </div>

      {/* User Profile Information */}
      <div className="border border-border/60 p-6 rounded-xl bg-card shadow-xs space-y-4">
        <h2 className="text-sm font-semibold text-foreground border-b border-border/40 pb-2">User Profile Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block text-muted-foreground mb-1">Full Name</label>
            <Input readOnly value={user?.name || "N/A"} className="font-medium bg-muted/30" />
          </div>
          <div>
            <label className="block text-muted-foreground mb-1">Email Address</label>
            <Input readOnly value={user?.email || "N/A"} className="font-medium bg-muted/30" />
          </div>
          <div>
            <label className="block text-muted-foreground mb-1">OAuth Provider</label>
            <Input readOnly value={user?.oauth_provider || "email"} className="font-medium capitalize bg-muted/30" />
          </div>
          <div>
            <label className="block text-muted-foreground mb-1">User ID (x-user-id)</label>
            <Input readOnly value={user?.id || "N/A"} className="font-mono text-xs bg-muted/30" />
          </div>
        </div>
      </div>

      {/* Python SDK & CLI Credentials */}
      <div className="border border-border/60 p-6 rounded-xl bg-card shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-border/40 pb-2">
          <div>
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <KeyIcon className="size-4 text-muted-foreground" /> API Keys for Python SDK & CLI
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Generate SHA-256 hashed API keys to authenticate local scripts or `insightapi login`.
            </p>
          </div>
        </div>

        {/* Generated Key Alert Notice */}
        {generatedKey && (
          <div className="p-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 text-emerald-500 text-xs space-y-1.5">
            <p className="font-semibold">Save your secret key now! It will not be shown again.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 font-mono text-[11px] bg-background/80 p-2 rounded border border-emerald-500/30 text-foreground break-all">
                {generatedKey}
              </code>
              <Button size="sm" onClick={() => handleCopyKey(generatedKey, "new")} className="bg-emerald-600 text-white shrink-0">
                Copy
              </Button>
            </div>
          </div>
        )}

        {/* Generate Key Input */}
        <div className="flex gap-2">
          <Input
            placeholder="Key name (e.g. Production CI/CD)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className="text-xs"
          />
          <Button onClick={handleGenerateKey} disabled={isGenerating} size="sm" className="shrink-0">
            <PlusIcon className="size-3.5 mr-1" /> Generate API Key
          </Button>
        </div>

        {/* API Keys Table */}
        <div className="pt-2">
          {keys.length === 0 ? (
            <p className="text-xs text-muted-foreground italic py-2">No active API keys found. Click generate to create one.</p>
          ) : (
            <div className="space-y-2">
              {keys.map((k) => (
                <div key={k.id} className="flex items-center justify-between p-3 rounded-lg border border-border/40 bg-muted/20 text-xs">
                  <div className="space-y-0.5">
                    <span className="font-semibold text-foreground">{k.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-muted-foreground">{k.key_prefix}••••••••••••</span>
                      <Badge variant="outline" className="text-[9px] px-1 py-0 font-mono">Active</Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-foreground"
                      onClick={() => handleCopyKey(k.raw_key || k.key_prefix, k.id)}
                    >
                      {copiedId === k.id ? <CheckIcon className="size-3.5 text-emerald-500" /> : <CopyIcon className="size-3.5" />}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:bg-destructive/10"
                      onClick={() => handleRevokeKey(k.id)}
                    >
                      <Trash2Icon className="size-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
