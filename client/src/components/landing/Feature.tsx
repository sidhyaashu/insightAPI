"use client";

import React from "react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { ShieldCheck, Cpu, Code2, Network, ArrowRight } from "lucide-react";

export default function Features() {
    const features = [
        {
            title: "Accessibility Tree DOM Snapping",
            description:
                "Filters out 100k+ raw HTML tokens down to semantic interactive elements (a, button, input, select) for 10x cheaper and faster LLM navigation.",
            skeleton: <SkeletonOne />,
            className:
                "col-span-1 md:col-span-4 lg:col-span-4 border-b md:border-r border-gray-200 dark:border-neutral-800",
        },
        {
            title: "Two-Tier Safety Guardrails",
            description:
                "Sub-millisecond regex pre-filtering to protect payment, password reset, and destructive actions automatically during exploration.",
            skeleton: <SkeletonTwo />,
            className: "col-span-1 md:col-span-2 lg:col-span-2 border-b border-gray-200 dark:border-neutral-800",
        },
        {
            title: "Network Observer & Path Normalizer",
            description:
                "Captures hidden REST & GraphQL operations in background, auto-grouping dynamic parameters like /users/101 into template routes /users/{id}.",
            skeleton: <SkeletonThree />,
            className:
                "col-span-1 md:col-span-3 lg:col-span-3 border-b md:border-r border-gray-200 dark:border-neutral-800",
        },
        {
            title: "OpenAPI 3.1 & Postman 2.1 Exporter",
            description:
                "Generates structured, validated OpenAPI specifications and Postman collections with inferred request/response JSON schemas.",
            skeleton: <SkeletonFour />,
            className: "col-span-1 md:col-span-3 lg:col-span-3 border-b md:border-none",
        },
    ];

    return (
        <div id="features" className="relative z-20 max-w-7xl mx-auto py-24 sm:py-32 border border-gray-200 dark:border-gray-800 bg-background">
            <div className="px-6 md:px-8">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-500 border border-orange-500/20 mb-4">
                    Autonomous Architecture
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl lg:leading-tight max-w-5xl mx-auto text-center tracking-tight font-medium text-foreground">
                    Packed with Autonomous Intelligence
                </h2>

                <p className="text-sm sm:text-base lg:text-lg max-w-2xl my-4 sm:my-6 mx-auto text-muted-foreground text-center font-normal">
                    From browser UI automation to deep network traffic observation and JSON Schema inference — InsightAPI turns any web application into clear API documentation.
                </p>
            </div>

            <div className="relative">
                <div className="grid grid-cols-1 md:grid-cols-6 lg:grid-cols-6 mt-8 sm:mt-12 border-y border-gray-200 dark:border-neutral-800">
                    {features.map((feature) => (
                        <FeatureCard key={feature.title} className={feature.className}>
                            <FeatureTitle>{feature.title}</FeatureTitle>
                            <FeatureDescription>{feature.description}</FeatureDescription>
                            <div className="h-full w-full">{feature.skeleton}</div>
                        </FeatureCard>
                    ))}
                </div>
            </div>
        </div>
    );
}

const FeatureCard = ({
    children,
    className,
}: {
    children?: React.ReactNode;
    className?: string;
}) => {
    return (
        <div className={cn(`p-6 sm:p-8 relative overflow-hidden bg-card/50`, className)}>
            {children}
        </div>
    );
};

const FeatureTitle = ({ children }: { children?: React.ReactNode }) => {
    return (
        <h3 className="max-w-5xl mx-auto text-left tracking-tight text-foreground text-xl md:text-2xl font-semibold">
            {children}
        </h3>
    );
};

const FeatureDescription = ({ children }: { children?: React.ReactNode }) => {
    return (
        <p className="text-sm md:text-base text-left text-muted-foreground font-normal my-2 max-w-lg">
            {children}
        </p>
    );
};

export const SkeletonOne = () => {
    return (
        <div className="relative flex py-6 px-2 gap-4 h-56 mt-4 rounded-lg bg-black/80 border border-neutral-800 font-mono text-xs text-green-400 overflow-hidden">
            <div className="w-full p-4 overflow-y-auto space-y-2">
                <div className="text-gray-500">// Interactive Accessibility Tree Snapshot</div>
                <div className="text-orange-400">&lt;AXTree root_url=&quot;https://app.example.com&quot;&gt;</div>
                <div className="pl-4 text-blue-400">&lt;Button id=&quot;btn-search&quot; role=&quot;button&quot;&gt;Search Products&lt;/Button&gt;</div>
                <div className="pl-4 text-blue-400">&lt;Input id=&quot;input-q&quot; type=&quot;text&quot; name=&quot;q&quot; /&gt;</div>
                <div className="pl-4 text-blue-400">&lt;Select id=&quot;sel-category&quot; name=&quot;category&quot;&gt;All items&lt;/Select&gt;</div>
                <div className="pl-4 text-purple-400">&lt;A href=&quot;/api/v1/checkout&quot; role=&quot;link&quot;&gt;View Cart&lt;/A&gt;</div>
                <div className="text-orange-400">&lt;/AXTree&gt;</div>
            </div>
            <div className="absolute bottom-0 inset-x-0 h-16 bg-gradient-to-t from-black to-transparent pointer-events-none" />
        </div>
    );
};

export const SkeletonTwo = () => {
    return (
        <div className="relative flex flex-col justify-center items-center p-6 gap-3 h-56 mt-4 rounded-lg bg-black/80 border border-neutral-800">
            <div className="w-full flex items-center justify-between p-3 rounded bg-neutral-900 border border-green-500/30 text-xs">
                <span className="flex items-center gap-2 text-green-400 font-medium">
                    <ShieldCheck className="h-4 w-4 text-green-400" /> Click /filter?category=tech
                </span>
                <span className="bg-green-500/20 text-green-400 px-2 py-0.5 rounded text-[10px] font-bold">SAFE (Tier 1)</span>
            </div>
            <div className="w-full flex items-center justify-between p-3 rounded bg-neutral-900 border border-red-500/30 text-xs">
                <span className="flex items-center gap-2 text-red-400 font-medium">
                    <ShieldCheck className="h-4 w-4 text-red-400" /> Submit Delete User Account
                </span>
                <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-[10px] font-bold">UNSAFE (Blocked)</span>
            </div>
        </div>
    );
};

export const SkeletonThree = () => {
    return (
        <div className="relative flex flex-col p-4 gap-2 h-56 mt-4 rounded-lg bg-black/80 border border-neutral-800 font-mono text-xs">
            <div className="flex items-center gap-2 text-gray-400 text-xs pb-2 border-b border-neutral-800">
                <Network className="h-4 w-4 text-orange-500" /> Observed Network Endpoints (Deduplicated)
            </div>
            <div className="flex items-center justify-between text-gray-300 py-1">
                <span className="text-green-400 font-bold">GET</span>
                <span className="text-yellow-300">/api/v1/users/{'{id}'}</span>
                <span className="text-gray-500 text-[10px]">Normalised (142 calls)</span>
            </div>
            <div className="flex items-center justify-between text-gray-300 py-1">
                <span className="text-blue-400 font-bold">POST</span>
                <span className="text-yellow-300">/graphql (op: GetCatalog)</span>
                <span className="text-gray-500 text-[10px]">Parsed payload</span>
            </div>
            <div className="flex items-center justify-between text-gray-300 py-1">
                <span className="text-green-400 font-bold">GET</span>
                <span className="text-yellow-300">/api/v1/orders/{'{id}'}/status</span>
                <span className="text-gray-500 text-[10px]">Path template</span>
            </div>
        </div>
    );
};

export const SkeletonFour = () => {
    return (
        <div className="relative flex flex-col p-4 gap-3 h-56 mt-4 rounded-lg bg-black/80 border border-neutral-800 font-mono text-xs">
            <div className="flex items-center justify-between text-xs text-orange-400 border-b border-neutral-800 pb-2">
                <span className="flex items-center gap-2 font-semibold">
                    <Code2 className="h-4 w-4 text-orange-500" /> openapi.json (Export Ready)
                </span>
                <span className="text-gray-400 text-[10px]">OpenAPI 3.1.0</span>
            </div>
            <div className="text-gray-300 text-[11px] leading-relaxed">
                &#123;<br />
                &nbsp;&nbsp;&quot;openapi&quot;: &quot;3.1.0&quot;,<br />
                &nbsp;&nbsp;&quot;info&quot;: &#123; &quot;title&quot;: &quot;Inferred API Spec&quot;, &quot;version&quot;: &quot;1.0.0&quot; &#125;,<br />
                &nbsp;&nbsp;&quot;paths&quot;: &#123; &quot;/api/v1/users/&#123;id&#125;&quot;: &#123; &quot;get&quot;: &#123; ... &#125; &#125; &#125;<br />
                &#125;
            </div>
        </div>
    );
};
