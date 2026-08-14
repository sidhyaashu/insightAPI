"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  IconKey,
  IconPlus,
  IconRefresh,
  IconCheck,
  IconTrash,
  IconAlertTriangle,
  IconWorld,
  IconShieldLock,
  IconBrandGoogle,
  IconBrandGithub,
  IconForms,
  IconServer,
  IconPlayerPlay,
  IconEdit,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { authProfilesApi } from "@/features/auth-profiles/api/authProfiles.api";
import type { AuthProfile, AuthType, CreateAuthProfileInput } from "@/lib/api-client/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function AuthProfilesPage() {
  const [profiles, setProfiles] = useState<AuthProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<AuthProfile | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Live Testing State
  const [testingProfileId, setTestingProfileId] = useState<string | null>(null);
  const [isTestingTransient, setIsTestingTransient] = useState(false);

  // Form State
  const [formData, setFormData] = useState<{
    name: string;
    target_domain: string;
    login_url: string;
    auth_type: AuthType;
    username: string;
    password: string;
  }>({
    name: "",
    target_domain: "",
    login_url: "",
    auth_type: "form",
    username: "",
    password: "",
  });

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await authProfilesApi.listProfiles();
      setProfiles(list);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load auth profiles.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  const openCreateModal = () => {
    setEditingProfile(null);
    setFormData({
      name: "",
      target_domain: "",
      login_url: "",
      auth_type: "form",
      username: "",
      password: "",
    });
    setModalOpen(true);
  };

  const openEditModal = (profile: AuthProfile) => {
    setEditingProfile(profile);
    setFormData({
      name: profile.name,
      target_domain: profile.target_domain,
      login_url: profile.login_url,
      auth_type: profile.auth_type,
      username: profile.credentials.username || profile.credentials.email || "",
      password: "",
    });
    setModalOpen(true);
  };

  const handleTestTransient = async () => {
    if (!formData.login_url || !formData.username || !formData.password) {
      toast.error("Please enter Login URL, Username/Email, and Password before testing.");
      return;
    }

    setIsTestingTransient(true);
    try {
      const res = await authProfilesApi.testTransient({
        login_url: formData.login_url,
        auth_type: formData.auth_type,
        credentials: {
          username: formData.username,
          password: formData.password,
        },
      });

      if (res.success) {
        toast.success(`✓ Live login test passed! Captured ${res.diagnostics?.cookies_count ?? 0} session cookies.`);
      } else {
        toast.error(`Login test failed: ${res.error || "Could not authenticate"}`);
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Test request failed.";
      toast.error(msg);
    } finally {
      setIsTestingTransient(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.login_url) return;

    setIsSubmitting(true);
    try {
      const credentials: Record<string, string> = {};
      if (formData.username) credentials.username = formData.username;
      if (formData.password) credentials.password = formData.password;

      if (editingProfile) {
        await authProfilesApi.updateProfile(editingProfile.id, {
          name: formData.name,
          target_domain: formData.target_domain || undefined,
          login_url: formData.login_url,
          auth_type: formData.auth_type,
          credentials: formData.password ? credentials : undefined,
        });
        toast.success(`Auth profile '${formData.name}' updated.`);
      } else {
        if (!formData.password) {
          toast.error("Password/Secret is required for new profiles.");
          setIsSubmitting(false);
          return;
        }
        await authProfilesApi.createProfile({
          name: formData.name,
          target_domain: formData.target_domain || undefined,
          login_url: formData.login_url,
          auth_type: formData.auth_type,
          credentials,
        });
        toast.success(`Auth profile '${formData.name}' created with encrypted credentials.`);
      }

      setModalOpen(false);
      await loadProfiles();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to save auth profile.";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTestExistingProfile = async (profileId: string) => {
    setTestingProfileId(profileId);
    try {
      const res = await authProfilesApi.testProfile(profileId);
      if (res.success) {
        toast.success(`✓ Automated login flow succeeded! (${res.diagnostics?.cookies_count ?? 0} cookies captured)`);
      } else {
        toast.error(`Login test failed: ${res.error || "Target rejected authentication"}`);
      }
      await loadProfiles();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Live test request failed.";
      toast.error(msg);
    } finally {
      setTestingProfileId(null);
    }
  };

  const handleDeleteProfile = async (profile: AuthProfile) => {
    if (!confirm(`Are you sure you want to delete auth profile '${profile.name}'?`)) return;

    try {
      await authProfilesApi.deleteProfile(profile.id);
      toast.success(`Auth profile '${profile.name}' deleted.`);
      await loadProfiles();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to delete profile.";
      toast.error(msg);
    }
  };

  const getAuthTypeBadge = (authType: AuthType) => {
    switch (authType) {
      case "oauth_google":
        return (
          <Badge variant="outline" className="text-[10px] font-mono border-red-500/30 text-red-500 bg-red-500/5 gap-1">
            <IconBrandGoogle className="size-3" /> Google OAuth
          </Badge>
        );
      case "oauth_github":
        return (
          <Badge variant="outline" className="text-[10px] font-mono border-purple-500/30 text-purple-400 bg-purple-500/5 gap-1">
            <IconBrandGithub className="size-3" /> GitHub OAuth
          </Badge>
        );
      case "saml":
        return (
          <Badge variant="outline" className="text-[10px] font-mono border-cyan-500/30 text-cyan-400 bg-cyan-500/5 gap-1">
            <IconServer className="size-3" /> SAML SSO
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-[10px] font-mono border-blue-500/30 text-blue-400 bg-blue-500/5 gap-1">
            <IconForms className="size-3" /> Form Login
          </Badge>
        );
    }
  };

  const formCount = profiles.filter((p) => p.auth_type === "form").length;
  const oauthCount = profiles.length - formCount;
  const passedCount = profiles.filter((p) => p.last_test_status === "success").length;

  return (
    <div className="flex flex-col min-h-0 flex-1 overflow-y-auto p-6 space-y-6 max-w-7xl mx-auto w-full font-sans">
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <IconShieldLock className="size-6 text-primary" />
            Authenticated Crawl Profiles
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Store encrypted target credentials for automated login during crawls — eliminates manual session.json capture.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadProfiles} className="gap-1.5 text-xs">
            <IconRefresh className="size-3.5" />
            Refresh
          </Button>
          <Button size="sm" onClick={openCreateModal} className="gap-1.5 text-xs bg-primary text-primary-foreground">
            <IconPlus className="size-3.5" />
            New Auth Profile
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Total Auth Profiles</div>
          <div className="text-2xl font-bold font-mono text-foreground">{profiles.length}</div>
        </div>
        <div className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5 shadow-xs">
          <div className="text-xs text-blue-400 font-mono mb-1">Form Logins</div>
          <div className="text-2xl font-bold font-mono text-blue-400">{formCount}</div>
        </div>
        <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 shadow-xs">
          <div className="text-xs text-emerald-500 font-mono mb-1">Live Verified Tests</div>
          <div className="text-2xl font-bold font-mono text-emerald-500">{passedCount}</div>
        </div>
      </div>

      {/* Profiles Table */}
      <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
        <div className="p-4 border-b border-border/40 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Stored Login Profiles</h2>
          <span className="text-xs font-mono text-muted-foreground">{profiles.length} profiles</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-muted-foreground font-mono animate-pulse">
            Loading authentication profiles…
          </div>
        ) : error ? (
          <div className="p-8 text-center text-xs text-destructive font-medium">{error}</div>
        ) : profiles.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center gap-3">
            <div className="size-12 rounded-2xl bg-muted/40 flex items-center justify-center text-muted-foreground">
              <IconKey className="size-6" />
            </div>
            <p className="text-sm font-semibold text-foreground">No authentication profiles configured</p>
            <p className="text-xs text-muted-foreground max-w-sm">
              Add target login credentials to allow the agent crawler to autonomously log into password-protected apps.
            </p>
            <Button size="sm" onClick={openCreateModal} className="text-xs mt-2">
              <IconPlus className="size-3.5 mr-1" /> Add Your First Profile
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-border/40">
            {profiles.map((p) => (
              <div
                key={p.id}
                className="p-4 flex items-center justify-between gap-4 flex-wrap hover:bg-muted/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                    <IconKey className="size-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-foreground">{p.name}</span>
                      {getAuthTypeBadge(p.auth_type)}
                      {p.last_test_status === "success" ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono border-emerald-500/40 text-emerald-500 bg-emerald-500/10 px-1.5 py-0"
                        >
                          ✓ Verified Active
                        </Badge>
                      ) : p.last_test_status === "failed" ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] font-mono border-destructive/40 text-destructive bg-destructive/10 px-1.5 py-0"
                          title={p.last_test_error || "Login test failed"}
                        >
                          Test Failed
                        </Badge>
                      ) : null}
                    </div>
                    <div className="text-[11px] text-muted-foreground font-mono mt-0.5 flex items-center gap-3">
                      <span>Domain: <strong className="text-foreground">{p.target_domain}</strong></span>
                      <span>URL: <span className="truncate max-w-[200px] inline-block align-bottom">{p.login_url}</span></span>
                      <span>User: <span className="text-foreground">{p.credentials.username || p.credentials.email || "configured"}</span></span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleTestExistingProfile(p.id)}
                    disabled={testingProfileId === p.id}
                    className="text-xs gap-1 border-primary/40 text-primary hover:bg-primary/10"
                  >
                    <IconPlayerPlay className="size-3.5" />
                    {testingProfileId === p.id ? "Testing..." : "Test Flow"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openEditModal(p)}
                    className="text-xs gap-1"
                  >
                    <IconEdit className="size-3.5" />
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteProfile(p)}
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

      {/* Add / Edit Profile Dialog */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-md p-6 rounded-2xl bg-card text-card-foreground border border-border">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <IconShieldLock className="size-5 text-primary" />
              {editingProfile ? "Edit Auth Profile" : "Create Stored Auth Profile"}
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Credentials are encrypted with Fernet AES at rest and injected directly into Playwright.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveProfile} className="space-y-3.5 py-2 text-xs">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Profile Name</Label>
              <Input
                placeholder="e.g. Staging Admin User"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="text-xs"
                required
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Authentication Type</Label>
              <Select
                value={formData.auth_type}
                onValueChange={(val) => setFormData({ ...formData, auth_type: (val as AuthType) || "form" })}
              >
                <SelectTrigger className="text-xs">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="form" className="text-xs">Standard Form Login (Username/Password)</SelectItem>
                  <SelectItem value="oauth_google" className="text-xs">Google OAuth (Test Account)</SelectItem>
                  <SelectItem value="oauth_github" className="text-xs">GitHub OAuth (Test Account)</SelectItem>
                  <SelectItem value="saml" className="text-xs">SAML Enterprise SSO</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Login Page URL</Label>
              <Input
                placeholder="https://app.example.com/login"
                value={formData.login_url}
                onChange={(e) => setFormData({ ...formData, login_url: e.target.value })}
                className="text-xs font-mono"
                required
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Target Domain / Hostname (Optional)</Label>
              <Input
                placeholder="app.example.com"
                value={formData.target_domain}
                onChange={(e) => setFormData({ ...formData, target_domain: e.target.value })}
                className="text-xs font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1 border-t">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Username / Email</Label>
                <Input
                  placeholder="admin@example.com"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="text-xs font-mono"
                  required
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-semibold">
                  {editingProfile ? "New Password (Leave blank to keep)" : "Password / Secret"}
                </Label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="text-xs font-mono"
                  required={!editingProfile}
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleTestTransient}
                disabled={isTestingTransient}
                className="text-xs gap-1 border-primary/30 text-primary hover:bg-primary/5"
              >
                <IconPlayerPlay className="size-3" />
                {isTestingTransient ? "Testing..." : "Test Flow Live"}
              </Button>
            </div>

            <DialogFooter className="gap-2 pt-2 border-t">
              <Button type="button" variant="outline" size="sm" onClick={() => setModalOpen(false)} className="text-xs">
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmitting} className="text-xs bg-primary text-primary-foreground">
                {isSubmitting ? "Saving…" : editingProfile ? "Update Profile" : "Save Encrypted Profile"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
