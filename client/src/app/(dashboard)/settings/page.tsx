"use client";

import { useAppSelector } from "@/store";

export default function SettingsPage() {
  const user = useAppSelector((state) => state.auth.user);

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight mb-1">Account & API Settings</h1>
        <p className="text-sm text-muted-foreground">Manage profile info and API keys for the Python SDK / CLI</p>
      </div>

      {/* User Profile Info */}
      <div className="border border-border p-6 rounded-xl bg-card shadow-sm">
        <h2 className="text-lg font-semibold mb-4">User Profile</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Full Name</label>
            <input
              type="text"
              readOnly
              value={user?.name || "N/A"}
              className="w-full px-3 py-2 border rounded-lg bg-muted text-foreground font-medium"
            />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Email Address</label>
            <input
              type="email"
              readOnly
              value={user?.email || "N/A"}
              className="w-full px-3 py-2 border rounded-lg bg-muted text-foreground font-medium"
            />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">OAuth Provider</label>
            <input
              type="text"
              readOnly
              value={user?.oauth_provider || "N/A"}
              className="w-full px-3 py-2 border rounded-lg bg-muted text-foreground font-medium capitalize"
            />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">User ID (x-user-id)</label>
            <input
              type="text"
              readOnly
              value={user?.id || "N/A"}
              className="w-full px-3 py-2 border rounded-lg bg-muted text-foreground font-mono text-xs"
            />
          </div>
        </div>
      </div>

      {/* Python SDK & CLI Credentials */}
      <div className="border border-border p-6 rounded-xl bg-card shadow-sm">
        <h2 className="text-lg font-semibold mb-2">Python SDK & CLI Credentials</h2>
        <p className="text-xs text-muted-foreground mb-4">
          Use your access token or generate an API Key to authenticate the `insightapi` Python SDK or CLI tool in your local terminal or CI/CD pipelines.
        </p>

        <div className="flex gap-2">
          <input
            type="password"
            readOnly
            value="insightapi_live_sk_8f7b2c9a1d4e"
            className="flex-1 px-3 py-2 border rounded-lg bg-muted font-mono text-xs"
          />
          <button
            onClick={() => {
              navigator.clipboard.writeText("insightapi_live_sk_8f7b2c9a1d4e");
              alert("SDK API key copied!");
            }}
            className="px-4 py-2 bg-primary text-primary-foreground text-xs rounded-lg font-medium"
          >
            Copy Key
          </button>
        </div>
      </div>
    </div>
  );
}
