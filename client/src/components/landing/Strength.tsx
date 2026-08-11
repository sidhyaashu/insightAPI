import { Check, Cpu, Zap, Shield, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function Strength() {
    return (
        <div className="max-w-7xl mx-auto border border-gray-200 dark:border-gray-800 px-6 md:px-8 py-24 sm:py-32 bg-background">
            <div className="grid grid-cols-1 gap-10 sm:gap-12 items-center lg:grid-cols-2">
                <div className="flex gap-8 sm:gap-10 flex-col">
                    <div className="flex gap-4 flex-col">
                        <div>
                            <Badge variant="outline" className="border-orange-500/30 text-orange-500 bg-orange-500/10">
                                Platform Strength
                            </Badge>
                        </div>
                        <div className="flex gap-2 flex-col">
                            <h2 className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl tracking-tighter max-w-xl text-left font-semibold text-foreground">
                                High-Precision Autonomous Crawling Engine
                            </h2>
                            <p className="text-base sm:text-lg leading-relaxed tracking-tight text-muted-foreground max-w-xl text-left">
                                Traditional API discovery relies on manual web proxies or heavy LLM vision models. InsightAPI uses deterministic accessibility trees and smart DOM graph hashing.
                            </p>
                        </div>
                    </div>
                    <div className="grid lg:pl-6 grid-cols-1 sm:grid-cols-3 items-start lg:grid-cols-1 gap-6">
                        <div className="flex flex-row gap-6 items-start">
                            <Check className="w-5 h-5 mt-1 text-orange-500 flex-shrink-0" />
                            <div className="flex flex-col gap-1">
                                <p className="font-medium text-foreground">Zero-Dependency Python SDK</p>
                                <p className="text-muted-foreground text-sm">
                                    Embed direct Python crawling in scripts or CI/CD pipelines with lightweight in-memory storage.
                                </p>
                            </div>
                        </div>
                        <div className="flex flex-row gap-6 items-start">
                            <Check className="w-5 h-5 mt-1 text-orange-500 flex-shrink-0" />
                            <div className="flex flex-col gap-1">
                                <p className="font-medium text-foreground">Fast & Deterministic Hashing</p>
                                <p className="text-muted-foreground text-sm">
                                    Hashes (URL + structural fingerprint) to prune redundant routes and SPA modal loops.
                                </p>
                            </div>
                        </div>
                        <div className="flex flex-row gap-6 items-start">
                            <Check className="w-5 h-5 mt-1 text-orange-500 flex-shrink-0" />
                            <div className="flex flex-col gap-1">
                                <p className="font-medium text-foreground">Stealth Anti-Detection Driver</p>
                                <p className="text-muted-foreground text-sm">
                                    Spoofs WebGL signatures, patches Permissions API, and respects target site robots.txt.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="bg-neutral-900 border border-gray-800 rounded-xl aspect-square p-6 flex flex-col justify-between overflow-hidden shadow-2xl relative">
                    <div className="flex items-center justify-between border-b border-gray-800 pb-4">
                        <div className="flex items-center gap-2 text-sm font-mono text-gray-300">
                            <Zap className="h-4 w-4 text-orange-500" /> InsightAPI Engine Core
                        </div>
                        <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded font-mono">ACTIVE (500ms delay)</span>
                    </div>

                    <div className="space-y-3 font-mono text-xs my-auto">
                        <div className="p-3 bg-black/60 rounded border border-gray-800 text-gray-300">
                            <span className="text-orange-400">&gt; engine.crawl</span>(&quot;https://app.target.com&quot;)
                        </div>
                        <div className="p-3 bg-black/60 rounded border border-gray-800 text-gray-300">
                            <span className="text-blue-400">[AXTree]</span> Extracted 14 interactive DOM controls.
                        </div>
                        <div className="p-3 bg-black/60 rounded border border-gray-800 text-gray-300">
                            <span className="text-green-400">[Safety]</span> Evaluated Tier-1 guardrails: 0 unsafe elements.
                        </div>
                        <div className="p-3 bg-black/60 rounded border border-gray-800 text-gray-300">
                            <span className="text-purple-400">[Observer]</span> Captured GET /api/v1/auth/me (200 OK)
                        </div>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-gray-800 text-xs text-gray-400 font-mono">
                        <span>Endpoints: 42</span>
                        <span>Templates: 8</span>
                        <span>OpenAPI 3.1: Ready</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
