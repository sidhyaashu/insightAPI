import React from "react";
import Link from "next/link";
import { Check, Zap, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const plans = [
    {
        name: "Free",
        price: "$0",
        period: "forever",
        description: "Perfect for lightweight SDK testing and personal projects.",
        features: [
            "1 autonomous crawl / day",
            "Max 10 pages per domain",
            "Markdown API report export",
            "Zero-dep Python SDK access",
            "Community Discord support"
        ],
        highlight: false,
        buttonText: "Get Started Free",
        href: "/login"
    },
    {
        name: "Starter",
        price: "$29",
        period: "/month",
        description: "Designed for small engineering teams and startup APIs.",
        features: [
            "20 autonomous crawls / day",
            "Max 50 pages per domain",
            "OpenAPI 3.1 & Postman export",
            "AI Chatbot (50 queries/day)",
            "Path Parameter Normalizer",
            "Standard email support"
        ],
        highlight: false,
        buttonText: "Start Starter Trial",
        href: "/login"
    },
    {
        name: "Pro",
        price: "$99",
        period: "/month",
        description: "For active API developers needing continuous discovery.",
        features: [
            "100 autonomous crawls / day",
            "Max 200 pages per domain",
            "3 parallel exploration agents",
            "Unlimited AI Chatbot",
            "Two-Tier Safety Guardrails",
            "Priority Slack & Email support"
        ],
        highlight: true,
        badge: "MOST POPULAR",
        buttonText: "Start Pro Trial",
        href: "/login"
    },
    {
        name: "Enterprise",
        price: "$499",
        period: "/month",
        description: "For enterprise security, compliance, & dedicated infra.",
        features: [
            "Unlimited autonomous crawls",
            "Self-Hosted Docker deployment",
            "10 parallel exploration agents",
            "Custom anti-detection driver",
            "SLA & Dedicated API Engineer"
        ],
        highlight: false,
        buttonText: "Contact Enterprise",
        href: "/login"
    }
];

export default function Pricing() {
    return (
        <div id="pricing" className="max-w-7xl mx-auto border border-gray-200 dark:border-gray-800 py-24 sm:py-32 bg-background">
            <div className="px-6 md:px-8 text-center mb-16">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-500 border border-orange-500/20 mb-4">
                    Simple Transparent Pricing
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl font-semibold tracking-tight text-foreground">
                    Choose the Right Plan for Your API Intelligence
                </h2>
                <p className="text-muted-foreground mt-4 max-w-2xl mx-auto text-base">
                    From standalone Python SDK runs to self-hosted enterprise Docker deployments.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-b border-gray-200 dark:border-gray-800">
                {plans.map((plan, idx) => (
                    <div
                        key={plan.name}
                        className={`p-6 sm:p-8 flex flex-col justify-between border-gray-200 dark:border-gray-800 ${
                            idx < plans.length - 1 ? "border-b md:border-b-0 lg:border-r" : ""
                        } ${plan.highlight ? "bg-orange-500/5 relative" : "bg-card/30"}`}
                    >
                        <div>
                            {plan.badge && (
                                <div className="absolute -top-3 right-6">
                                    <Badge className="bg-orange-500 text-white font-bold text-[10px] px-2.5 py-0.5 shadow-md">
                                        {plan.badge}
                                    </Badge>
                                </div>
                            )}

                            <h3 className="text-xl font-bold text-foreground">{plan.name}</h3>
                            <p className="text-xs text-muted-foreground mt-2 min-h-[36px]">{plan.description}</p>

                            <div className="mt-6 flex items-baseline gap-1">
                                <span className="text-4xl font-extrabold text-foreground tracking-tight">{plan.price}</span>
                                <span className="text-xs text-muted-foreground">{plan.period}</span>
                            </div>

                            <ul className="mt-8 space-y-3 text-xs text-muted-foreground">
                                {plan.features.map((feat) => (
                                    <li key={feat} className="flex items-center gap-2.5">
                                        <Check className="h-4 w-4 text-orange-500 shrink-0" />
                                        <span>{feat}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div className="mt-8 pt-6 border-t border-border">
                            <Link
                                href={plan.href}
                                className={`inline-flex items-center justify-center rounded-lg w-full py-3 text-xs font-semibold cursor-pointer transition-all ${
                                    plan.highlight
                                        ? "bg-orange-500 hover:bg-orange-600 text-white shadow-lg shadow-orange-500/20"
                                        : "border border-border bg-background hover:bg-muted text-foreground"
                                }`}
                            >
                                {plan.buttonText}
                            </Link>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
