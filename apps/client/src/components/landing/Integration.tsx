"use client";

import React from "react";
import { motion } from "framer-motion";
import { Folder, Zap, SparklesIcon, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

interface IntegrationProps {
    className?: string;
    circleText?: string;
    badgeTexts?: {
        first: string;
        second: string;
        third: string;
        fourth: string;
    };
    buttonTexts?: {
        first: string;
        second: string;
    };
    title?: string;
    lightColor?: string;
}

export const Integration = ({
    className,
    circleText,
    badgeTexts,
    buttonTexts,
    title,
    lightColor,
}: IntegrationProps) => {
    return (
        <div className="max-w-7xl mx-auto border border-gray-200 dark:border-gray-800 py-24 sm:py-32 bg-background flex flex-col items-center justify-center overflow-hidden">
            <div className="px-6 md:px-8 mb-8 text-center max-w-3xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-500 border border-orange-500/20 mb-4">
                    Real-time Data Stream
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl font-semibold tracking-tight text-foreground">
                    Seamless API Network Interception
                </h2>
                <p className="text-muted-foreground mt-3 text-sm sm:text-base">
                    Observe active REST HTTP methods and GraphQL queries in motion as InsightAPI automatically synthesizes structured OpenAPI schemas.
                </p>
            </div>

            <div
                className={cn(
                    "relative flex h-[360px] w-full max-w-[550px] flex-col items-center mx-auto",
                    className
                )}
            >
                {/* SVG Paths */}
                <svg
                    className="h-full sm:w-full text-muted-foreground/30"
                    width="100%"
                    height="100%"
                    viewBox="0 0 200 100"
                >
                    <g
                        stroke="currentColor"
                        fill="none"
                        strokeWidth="0.4"
                        strokeDasharray="100 100"
                        pathLength="100"
                    >
                        <path d="M 31 10 v 15 q 0 5 5 5 h 59 q 5 0 5 5 v 10" />
                        <path d="M 77 10 v 10 q 0 5 5 5 h 13 q 5 0 5 5 v 10" />
                        <path d="M 124 10 v 10 q 0 5 -5 5 h -14 q -5 0 -5 5 v 10" />
                        <path d="M 170 10 v 15 q 0 5 -5 5 h -60 q -5 0 -5 5 v 10" />
                        <animate
                            attributeName="stroke-dashoffset"
                            from="100"
                            to="0"
                            dur="1s"
                            fill="freeze"
                            calcMode="spline"
                            keySplines="0.25,0.1,0.5,1"
                            keyTimes="0; 1"
                        />
                    </g>
                    {/* Animated Light Circles */}
                    <g mask="url(#db-mask-1)">
                        <circle
                            className="database db-light-1"
                            cx="0"
                            cy="0"
                            r="12"
                            fill="url(#db-orange-grad)"
                        />
                    </g>
                    <g mask="url(#db-mask-2)">
                        <circle
                            className="database db-light-2"
                            cx="0"
                            cy="0"
                            r="12"
                            fill="url(#db-orange-grad)"
                        />
                    </g>
                    <g mask="url(#db-mask-3)">
                        <circle
                            className="database db-light-3"
                            cx="0"
                            cy="0"
                            r="12"
                            fill="url(#db-orange-grad)"
                        />
                    </g>
                    <g mask="url(#db-mask-4)">
                        <circle
                            className="database db-light-4"
                            cx="0"
                            cy="0"
                            r="12"
                            fill="url(#db-orange-grad)"
                        />
                    </g>
                    {/* HTTP Method Badge Buttons */}
                    <g stroke="currentColor" fill="none" strokeWidth="0.4">
                        {/* GET */}
                        <g>
                            <rect
                                fill="#18181B"
                                x="14"
                                y="5"
                                width="34"
                                height="10"
                                rx="5"
                                stroke="#f97316"
                                strokeWidth="0.3"
                            ></rect>
                            <DatabaseIcon x="18" y="7.5" />
                            <text
                                x="28"
                                y="12"
                                fill="#22c55e"
                                stroke="none"
                                fontSize="5"
                                fontWeight="700"
                            >
                                {badgeTexts?.first || "GET"}
                            </text>
                        </g>
                        {/* POST */}
                        <g>
                            <rect
                                fill="#18181B"
                                x="60"
                                y="5"
                                width="34"
                                height="10"
                                rx="5"
                                stroke="#f97316"
                                strokeWidth="0.3"
                            ></rect>
                            <DatabaseIcon x="64" y="7.5" />
                            <text
                                x="74"
                                y="12"
                                fill="#3b82f6"
                                stroke="none"
                                fontSize="5"
                                fontWeight="700"
                            >
                                {badgeTexts?.second || "POST"}
                            </text>
                        </g>
                        {/* PUT */}
                        <g>
                            <rect
                                fill="#18181B"
                                x="108"
                                y="5"
                                width="34"
                                height="10"
                                rx="5"
                                stroke="#f97316"
                                strokeWidth="0.3"
                            ></rect>
                            <DatabaseIcon x="112" y="7.5" />
                            <text
                                x="122"
                                y="12"
                                fill="#eab308"
                                stroke="none"
                                fontSize="5"
                                fontWeight="700"
                            >
                                {badgeTexts?.third || "PUT"}
                            </text>
                        </g>
                        {/* DELETE */}
                        <g>
                            <rect
                                fill="#18181B"
                                x="150"
                                y="5"
                                width="40"
                                height="10"
                                rx="5"
                                stroke="#ef4444"
                                strokeWidth="0.3"
                            ></rect>
                            <DatabaseIcon x="154" y="7.5" />
                            <text
                                x="165"
                                y="12"
                                fill="#ef4444"
                                stroke="none"
                                fontSize="5"
                                fontWeight="700"
                            >
                                {badgeTexts?.fourth || "DELETE"}
                            </text>
                        </g>
                    </g>
                    <defs>
                        <mask id="db-mask-1">
                            <path
                                d="M 31 10 v 15 q 0 5 5 5 h 59 q 5 0 5 5 v 10"
                                strokeWidth="0.5"
                                stroke="white"
                            />
                        </mask>
                        <mask id="db-mask-2">
                            <path
                                d="M 77 10 v 10 q 0 5 5 5 h 13 q 5 0 5 5 v 10"
                                strokeWidth="0.5"
                                stroke="white"
                            />
                        </mask>
                        <mask id="db-mask-3">
                            <path
                                d="M 124 10 v 10 q 0 5 -5 5 h -14 q -5 0 -5 5 v 10"
                                strokeWidth="0.5"
                                stroke="white"
                            />
                        </mask>
                        <mask id="db-mask-4">
                            <path
                                d="M 170 10 v 15 q 0 5 -5 5 h -60 q -5 0 -5 5 v 10"
                                strokeWidth="0.5"
                                stroke="white"
                            />
                        </mask>
                        <radialGradient id="db-orange-grad" fx="1">
                            <stop offset="0%" stopColor={lightColor || "#f97316"} />
                            <stop offset="100%" stopColor="transparent" />
                        </radialGradient>
                    </defs>
                </svg>

                {/* Main Engine Box */}
                <div className="absolute bottom-10 flex w-full flex-col items-center">
                    <div className="absolute -bottom-4 h-[100px] w-[62%] rounded-lg bg-orange-500/10" />
                    <div className="absolute -top-3 z-20 flex items-center justify-center rounded-lg border border-orange-500/30 bg-[#101112] px-3 py-1 text-xs">
                        <SparklesIcon className="size-3 text-orange-500 mr-1.5" />
                        <span className="text-[11px] font-medium text-foreground">
                            {title ? title : "InsightAPI Network Intelligence Engine"}
                        </span>
                    </div>
                    <div className="absolute -bottom-8 z-30 grid h-[56px] w-[56px] place-items-center rounded-full border border-orange-500/40 bg-[#141516] font-bold text-xs text-orange-500 shadow-lg">
                        {circleText ? circleText : "API"}
                    </div>
                    <div className="relative z-10 flex h-[140px] w-full items-center justify-between px-8 overflow-hidden rounded-lg border border-gray-800 bg-background shadow-md">
                        <div className="z-10 h-7 rounded-full bg-[#101112] px-3 text-xs border border-gray-800 flex items-center gap-2 text-gray-300">
                            <Zap className="size-3.5 text-orange-500" />
                            <span>{buttonTexts?.first || "OpenAPI 3.1 Spec"}</span>
                        </div>
                        <div className="z-10 h-7 rounded-full bg-[#101112] px-3 text-xs border border-gray-800 flex items-center gap-2 text-gray-300">
                            <Folder className="size-3.5 text-blue-400" />
                            <span>{buttonTexts?.second || "Postman v2.1"}</span>
                        </div>

                        {/* Animated concentric circles */}
                        <motion.div
                            className="absolute left-1/2 -translate-x-1/2 -bottom-14 h-[100px] w-[100px] rounded-full border-t border-orange-500/20 bg-orange-500/5"
                            animate={{ scale: [0.98, 1.02, 0.98] }}
                            transition={{ duration: 2, repeat: Infinity }}
                        />
                        <motion.div
                            className="absolute left-1/2 -translate-x-1/2 -bottom-20 h-[145px] w-[145px] rounded-full border-t border-orange-500/20 bg-orange-500/5"
                            animate={{ scale: [1, 0.98, 1.02] }}
                            transition={{ duration: 2, repeat: Infinity }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

const DatabaseIcon = ({ x = "0", y = "0" }: { x: string; y: string }) => {
    return (
        <svg
            x={x}
            y={y}
            xmlns="http://www.w3.org/2000/svg"
            width="5"
            height="5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#f97316"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M3 5V19A9 3 0 0 0 21 19V5" />
            <path d="M3 12A9 3 0 0 0 21 12" />
        </svg>
    );
};
