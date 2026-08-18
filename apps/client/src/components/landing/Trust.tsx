'use client'

import React, { useState, useEffect } from 'react'
import { Activity, ArrowRight, Code2, MapPin, Terminal, Zap, ShieldCheck } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts'

const sampleChartData = [
    { time: '00:00', endpoints: 12 },
    { time: '00:05', endpoints: 45 },
    { time: '00:10', endpoints: 88 },
    { time: '00:15', endpoints: 140 },
    { time: '00:20', endpoints: 210 },
    { time: '00:25', endpoints: 340 },
    { time: '00:30', endpoints: 480 },
]

export default function Trust() {
    const [isMounted, setIsMounted] = useState(false)

    useEffect(() => {
        setIsMounted(true)
    }, [])

    return (
        <section className="bg-background">
            <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 md:grid-rows-2 border border-gray-200 dark:border-gray-800 py-24 sm:py-32">

                {/* 1. Global Crawler Network - Top Left */}
                <div className="relative overflow-hidden bg-muted/40 border border-gray-200 dark:border-gray-800 p-6 sm:p-8 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-2 text-xs font-semibold text-orange-500 mb-4">
                            <MapPin className="w-4 h-4" />
                            Distributed Crawl Nodes
                        </div>
                        <h3 className="text-xl sm:text-2xl font-semibold text-foreground">
                            Global Distributed Exploration Nodes.{' '}
                            <span className="text-muted-foreground font-normal">Autonomous Playwright agents running in isolated browser runtime containers.</span>
                        </h3>
                    </div>

                    <div className="relative mt-8 p-6 bg-black/80 border border-gray-800 rounded-xl font-mono text-xs text-gray-300">
                        <div className="flex items-center justify-between text-orange-400 mb-3 border-b border-gray-800 pb-2">
                            <span>🌍 Node Status: US-East-1</span>
                            <span className="text-green-400">● Live (500ms spacing)</span>
                        </div>
                        <p className="text-gray-400 mb-2">// Active Playwright Chromium Session</p>
                        <p><span className="text-blue-400">&gt; IP:</span> 192.0.2.45 (Stealth WebGL Spoofed)</p>
                        <p><span className="text-blue-400">&gt; Target:</span> https://app.target.com/dashboard</p>
                        <p><span className="text-blue-400">&gt; Status:</span> Snapping AXTree (14 elements found)</p>
                    </div>
                </div>

                {/* 2. Featured Benchmark Card - Top Right */}
                <div className="flex flex-col justify-between gap-6 p-6 sm:p-8 border border-gray-200 dark:border-gray-800 bg-card">
                    <div>
                        <span className="text-xs flex items-center gap-2 font-semibold text-orange-500 mb-3">
                            <Zap className="w-4 h-4" /> Enterprise Benchmark
                        </span>
                        <h3 className="text-xl sm:text-2xl font-semibold text-foreground">
                            1,200+ Hidden Endpoints Mapped{' '}
                            <span className="text-muted-foreground font-normal">without a single second of service disruption or destructive form submit.</span>
                        </h3>
                    </div>
                    <div className="bg-muted/50 border border-border p-6 rounded-xl space-y-3 font-mono text-xs">
                        <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">Path Deduplication:</span>
                            <span className="text-green-500 font-bold">100% Normalized</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">GraphQL Operations:</span>
                            <span className="text-blue-500 font-bold">Parsed (18 queries)</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">OpenAPI Spec:</span>
                            <span className="text-orange-500 font-bold">OpenAPI 3.1.0 Validated</span>
                        </div>
                    </div>
                </div>

                {/* 3. Real-Time Endpoint Discovery Chart - Bottom Left */}
                <div className="border border-gray-200 dark:border-gray-800 bg-muted/40 p-6 sm:p-8 space-y-4">
                    <div className="flex items-center gap-2 text-xs font-semibold text-orange-500">
                        <Activity className="w-4 h-4" />
                        Discovery Performance
                    </div>
                    <h3 className="text-xl sm:text-2xl font-semibold text-foreground">
                        Real-time Endpoint Capture Rate.{' '}
                        <span className="text-muted-foreground font-normal">Continuous background network observation.</span>
                    </h3>

                    <div className="h-44 w-full mt-4 min-h-[175px]">
                        {isMounted ? (
                            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={175}>
                                <AreaChart data={sampleChartData}>
                                    <defs>
                                        <linearGradient id="colorEndpoints" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#f97316" stopOpacity={0.4} />
                                            <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                    <XAxis dataKey="time" stroke="#666" fontSize={10} />
                                    <YAxis stroke="#666" fontSize={10} />
                                    <Area type="monotone" dataKey="endpoints" stroke="#f97316" fillOpacity={1} fill="url(#colorEndpoints)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-full w-full bg-muted/20 animate-pulse rounded-lg" />
                        )}
                    </div>
                </div>

                {/* 4. Feature Cards - Bottom Right */}
                <div className="grid sm:grid-cols-2 bg-card border border-gray-200 dark:border-gray-800">
                    <div className="flex flex-col gap-3 p-6 border-b sm:border-b-0 sm:border-r border-gray-200 dark:border-gray-800 bg-background hover:bg-muted/40 transition-colors">
                        <Code2 className="w-5 h-5 text-orange-500" />
                        <h4 className="font-semibold text-foreground text-base">Python SDK Mode</h4>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                            Zero-dependency lightweight in-memory mode for running crawling agents directly inside python scripts.
                        </p>
                    </div>
                    <div className="flex flex-col gap-3 p-6 bg-background hover:bg-muted/40 transition-colors">
                        <Terminal className="w-5 h-5 text-orange-500" />
                        <h4 className="font-semibold text-foreground text-base">FastAPI REST Server</h4>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                            Embed InsightAPI as a standalone service with full async support, Postgres pgvector, and Redis cache.
                        </p>
                    </div>
                </div>
            </div>
        </section>
    )
}
