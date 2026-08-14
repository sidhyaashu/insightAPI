"use client";

import React from "react";
import Link from "next/link";
import { IconShieldCheck, IconScale, IconAlertTriangle, IconFileText, IconArrowLeft } from "@tabler/icons-react";
import { Button } from "@/components/ui/button";

export default function TermsOfServicePage() {
  return (
    <div className="flex flex-col min-h-0 flex-1 overflow-y-auto p-6 space-y-8 max-w-4xl mx-auto w-full font-sans pb-20">
      {/* Back link */}
      <div>
        <Link href="/chat">
          <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground hover:text-foreground">
            <IconArrowLeft className="size-3.5" /> Back to Dashboard
          </Button>
        </Link>
      </div>

      {/* Header */}
      <div className="border-b border-border/50 pb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 mb-3">
          <IconScale className="size-3.5" /> Legal Agreement & Safe Harbor
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          InsightAPI Terms of Service & Acceptable Use Policy
        </h1>
        <p className="text-xs text-muted-foreground mt-2">
          Effective Date: August 14, 2026 • Version 1.0 (Audit Controlled)
        </p>
      </div>

      {/* Policy Sections */}
      <div className="space-y-6 text-xs leading-relaxed text-muted-foreground">
        {/* Section 1 */}
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <span className="text-primary font-mono">1.</span> Authorized Crawling & Target Representation
          </h2>
          <p>
            By initiating an automated exploration session or API crawl through InsightAPI, you explicitly warrant and represent that:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-foreground/90">
            <li>You are the registered owner, administrator, or explicitly authorized security tester of the target application or domain.</li>
            <li>You have received prior written or contractual consent from the domain owner to conduct non-destructive API exploration, observation, and schema inference.</li>
            <li>Your crawl requests will adhere to all applicable national, federal, and international cyber laws, including the Computer Fraud and Abuse Act (CFAA) and GDPR.</li>
          </ul>
        </section>

        {/* Section 2 */}
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <span className="text-primary font-mono">2.</span> Prohibited Activities & Malicious Execution
          </h2>
          <p>
            InsightAPI is strictly designed for non-destructive API documentation, OpenAPI generation, and contract testing. You agree NOT to use the platform to:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-foreground/90">
            <li>Execute Denial of Service (DoS/DDoS) attacks or intentionally flood target infrastructure with disruptive request volumes.</li>
            <li>Bypass authentication walls to scrape private user data, passwords, or personally identifiable information (PII).</li>
            <li>Perform destructive mutation requests (e.g. `DELETE`, financial `PAY`, account `PURGE`). Note: InsightAPI's built-in Two-Tier Safety Guardrails actively block destructive actions.</li>
            <li>Harvest intellectual property without authorization.</li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <span className="text-primary font-mono">3.</span> Safe Harbor & Domain Ownership Verification
          </h2>
          <p>
            InsightAPI provides domain ownership challenge protocols (via DNS TXT record and `/.well-known/insightapi-verification.txt`). Targets with verified ownership status are designated as pre-authorized and are exempt from per-session ToS confirmation dialogs. Unverified domains require explicit per-crawl electronic signature confirmation and IP logging.
          </p>
        </section>

        {/* Section 4 */}
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <span className="text-primary font-mono">4.</span> Audit Logging & Legal Recordkeeping
          </h2>
          <p>
            For compliance, accountability, and fraud prevention, InsightAPI logs immutable records of all authorization acceptances, including your user ID, the target domain, destination URL, origin IP address, and timestamp. In the event of an abuse inquiry from a target domain administrator, these audit logs serve as evidentiary proof of user representation.
          </p>
        </section>

        {/* Section 5 */}
        <section className="space-y-2">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <span className="text-primary font-mono">5.</span> Limitation of Liability & Indemnification
          </h2>
          <p>
            InsightAPI and its operators assume no liability for unauthorized, negligent, or unlawful crawling performed by users. You agree to defend, indemnify, and hold harmless InsightAPI and its contributors against any third-party claims, liabilities, damages, and expenses arising from your exploration of any target domain.
          </p>
        </section>
      </div>

      {/* Footer Callout */}
      <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 flex items-start gap-3">
        <IconShieldCheck className="size-5 text-primary shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-foreground">Need to pre-authorize your staging or production domains?</p>
          <p className="text-muted-foreground">
            Visit the <Link href="/domains" className="text-primary underline font-medium">Domain Verification Dashboard</Link> to add DNS TXT challenges for your engineering domains.
          </p>
        </div>
      </div>
    </div>
  );
}
