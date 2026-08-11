"use client"

import * as React from "react"
import Link from "next/link"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Moon, Sun, Zap } from "lucide-react"
import { cn } from "@/lib/utils"

function Footer() {
    const [isDarkMode, setIsDarkMode] = React.useState(true)

    React.useEffect(() => {
        if (isDarkMode) {
            document.documentElement.classList.add("dark")
        } else {
            document.documentElement.classList.remove("dark")
        }
    }, [isDarkMode])

    const footerSections = [
        {
            title: "Products & Engine",
            links: [
                { name: "Autonomous Crawler", href: "/docs" },
                { name: "Accessibility Snapper", href: "/docs" },
                { name: "Two-Tier Guardrails", href: "/docs" },
                { name: "Network Observer", href: "/docs" },
                { name: "OpenAPI Exporter", href: "/docs" }
            ]
        },
        {
            title: "Use Cases",
            links: [
                { name: "API Reverse Engineering", href: "/docs" },
                { name: "Legacy System Audit", href: "/docs" },
                { name: "CI/CD Schema Validation", href: "/docs" },
                { name: "Postman Collection Export", href: "/docs" },
                { name: "Security & Compliance", href: "/docs" }
            ]
        },
        {
            title: "Documentation & SDK",
            links: [
                { name: "Getting Started Guide", href: "/docs" },
                { name: "Python SDK Reference", href: "/docs" },
                { name: "FastAPI REST API Specs", href: "/docs" },
                { name: "Docker Deployment", href: "/docs" },
                { name: "GitHub Integration", href: "/docs" }
            ]
        },
        {
            title: "Company & Platform",
            links: [
                { name: "About InsightAPI", href: "/" },
                { name: "Open Source SDK", href: "https://github.com" },
                { name: "Architecture & Roadmap", href: "/docs" },
                { name: "Community & OSS", href: "https://github.com" }
            ]
        }
    ]

    const legalLinks = [
        "© 2026 InsightAPI.AI",
        "Terms of Service",
        "Privacy Policy",
        "Security & Compliance"
    ]

    return (
        <footer className="relative bg-background text-foreground transition-colors duration-300">
            <div className="max-w-7xl mx-auto border-x border-gray-200 dark:border-gray-800">
                
                {/* Brand Banner */}
                <div className="p-8 sm:p-10 border border-gray-200 dark:border-gray-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-muted/20">
                    <div className="flex items-center gap-3">
                        <div className="bg-orange-500/10 p-2 rounded-lg border border-orange-500/30">
                            <Zap className="h-6 w-6 text-orange-500 fill-orange-500" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold tracking-tight text-foreground">InsightAPI<span className="text-orange-500">.AI</span></h3>
                            <p className="text-xs text-muted-foreground">Autonomous Web API Intelligence Platform & Python SDK</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3 bg-background px-4 py-2 rounded-full border border-border">
                        <Sun className="h-4 w-4 text-muted-foreground" />
                        <Switch
                            checked={isDarkMode}
                            onCheckedChange={setIsDarkMode}
                            id="dark-mode-toggle"
                        />
                        <Moon className="h-4 w-4 text-orange-500" />
                        <Label htmlFor="dark-mode-toggle" className="text-xs font-medium text-muted-foreground cursor-pointer">
                            Dark Theme
                        </Label>
                    </div>
                </div>

                {/* Main Grid Section */}
                <div className="grid grid-cols-2 md:grid-cols-4 border border-gray-200 dark:border-gray-800">
                    {footerSections.map((section, idx) => (
                        <div key={section.title} className={cn(
                            "flex flex-col border border-gray-200 dark:border-gray-800",
                            idx % 4 !== 3 && "md:border border-gray-200 dark:border-gray-800",
                            idx % 2 === 0 && "border md:border-r-0"
                        )}>
                            <div className="p-6 border-b border-gray-200 dark:border-gray-800 bg-muted/40">
                                <h3 className="text-xs font-semibold tracking-wider text-orange-500 uppercase">
                                    {section.title}
                                </h3>
                            </div>
                            <nav className="flex flex-col">
                                {section.links.map((link) => (
                                    <Link
                                        key={link.name}
                                        href={link.href}
                                        className="p-5 text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground border-b border-gray-100 dark:border-gray-800/50 last:border-0"
                                    >
                                        {link.name}
                                    </Link>
                                ))}
                            </nav>
                        </div>
                    ))}
                </div>

                {/* Empty Spacer Row (As seen in reference Spraxi grid) */}
                <div className="grid grid-cols-4 border border-gray-200 dark:border-gray-800 h-16 md:h-20 bg-muted/10">
                    <div className="border-r border-gray-200 dark:border-gray-800" />
                    <div className="border-r border-gray-200 dark:border-gray-800" />
                    <div className="border-r border-gray-200 dark:border-gray-800" />
                    <div />
                </div>

                {/* Legal / Bottom Row Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 border border-gray-200 dark:border-gray-800">
                    {legalLinks.map((link, idx) => (
                        <div
                            key={link}
                            className={cn(
                                "p-6 text-xs text-muted-foreground border-gray-200 dark:border-gray-800 flex items-center justify-center text-center",
                                idx < 3 && "border-r"
                            )}
                        >
                            {link}
                        </div>
                    ))}
                </div>
            </div>
        </footer>
    )
}

export { Footer }
