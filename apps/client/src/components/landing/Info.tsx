"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { Monitor, LayoutDashboard, Users, Zap, ShieldCheck } from "lucide-react";

const CountUp = dynamic(() => import("react-countup"), { ssr: false });

function usePrefersReducedMotion() {
    const [reduced, setReduced] = useState(false);
    useEffect(() => {
        if (typeof window === "undefined" || !("matchMedia" in window)) return;
        const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
        const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
        setReduced(mq.matches);
        mq.addEventListener?.("change", onChange);
        return () => mq.removeEventListener?.("change", onChange);
    }, []);
    return reduced;
}

function parseMetricValue(raw: string) {
    const value = (raw ?? "").toString().trim();
    const m = value.match(
        /^([^\d\-+]*?)\s*([\-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*([^\d\s]*)$/
    );
    if (!m) {
        return { prefix: "", end: 0, suffix: value, decimals: 0 };
    }
    const [, prefix, num, suffix] = m;
    const normalized = num.replace(/,/g, "");
    const end = parseFloat(normalized);
    const decimals = (normalized.split(".")[1]?.length ?? 0);
    return {
        prefix: prefix ?? "",
        end: isNaN(end) ? 0 : end,
        suffix: suffix ?? "",
        decimals,
    };
}

function MetricStat({
    value,
    label,
    sub,
    duration = 1.6,
}: {
    value: string;
    label: string;
    sub?: string;
    duration?: number;
}) {
    const reduceMotion = usePrefersReducedMotion();
    const { prefix, end, suffix, decimals } = parseMetricValue(value);

    return (
        <div className="flex flex-col gap-2 text-left p-6 sm:p-8 border border-gray-200 dark:border-gray-800 bg-card/40">
            <p
                className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground tracking-tight"
                aria-label={`${label} ${value}`}
            >
                {prefix}
                {reduceMotion ? (
                    <span>
                        {end.toLocaleString(undefined, {
                            minimumFractionDigits: decimals,
                            maximumFractionDigits: decimals,
                        })}
                    </span>
                ) : (
                    <CountUp
                        end={end}
                        decimals={decimals}
                        duration={duration}
                        separator=","
                        enableScrollSpy
                        scrollSpyOnce
                    />
                )}
                <span className="text-orange-500">{suffix}</span>
            </p>
            <p className="font-semibold text-foreground text-left text-base mt-2">
                {label}
            </p>
            {sub ? (
                <p className="text-muted-foreground text-sm text-left">{sub}</p>
            ) : null}
        </div>
    );
}

export default function Info() {
    return (
        <div className="max-w-7xl mx-auto border border-gray-200 dark:border-gray-800 py-24 sm:py-32 bg-background">
            <div className="px-6 md:px-8 mb-12 text-center">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-500 border border-orange-500/20 mb-4">
                    Proven Speed & Scale
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl font-semibold tracking-tight text-foreground">
                    Engineered for Maximum Discovery Precision
                </h2>
                <p className="text-muted-foreground mt-4 max-w-2xl mx-auto text-base sm:text-lg">
                    Real metrics from production web app explorations across complex SaaS platforms and enterprise portals.
                </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-0 max-w-6xl mx-auto px-6 md:px-8">
                <MetricStat
                    value="100,000+"
                    label="Endpoints Mapped"
                    sub="Across REST, GraphQL, & WebSockets"
                />
                <MetricStat
                    value="99.4%"
                    label="Route Template Accuracy"
                    sub="Automatic parameter normalization"
                />
                <MetricStat
                    value="50ms"
                    label="DOM Fingerprint Speed"
                    sub="Sub-second state graph deduplication"
                />
                <MetricStat
                    value="10x"
                    label="Faster Documentation"
                    sub="Compared to manual OpenAPI writing"
                />
            </div>
        </div>
    );
}
