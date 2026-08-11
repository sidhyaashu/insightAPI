"use client"

import Link from "next/link"
import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import {
    NavigationMenu,
    NavigationMenuContent,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    NavigationMenuTrigger,
} from "@/components/ui/navigation-menu"
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion"
import {
    Zap,
    Menu,
    Bot,
    Search,
    Globe,
    FileText,
    Sparkles,
    LineChart,
    ArrowRight,
    ChevronRight,
    Shield,
    Code,
    Cpu,
    Terminal,
    Network
} from "lucide-react"

import { useAppSelector } from "@/store"

interface ListItemProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
    title: string;
    icon?: React.ReactNode;
    children: React.ReactNode;
}

const ListItem = React.forwardRef<HTMLAnchorElement, ListItemProps>(
    ({ className, title, children, icon, href, ...props }, ref) => {
        return (
            <li>
                <NavigationMenuLink asChild>
                    <Link
                        ref={ref}
                        href={href || "#"}
                        className="block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                        {...props}
                    >
                        <div className="flex items-center gap-2 text-sm font-medium leading-none">
                            {icon}
                            <span>{title}</span>
                        </div>
                        <p className="line-clamp-2 text-xs leading-snug text-muted-foreground mt-1">
                            {children}
                        </p>
                    </Link>
                </NavigationMenuLink>
            </li>
        )
    }
)
ListItem.displayName = "ListItem"

export default function NavBar() {
    const [isScrolled, setIsScrolled] = useState(false)
    const [isOpen, setIsOpen] = useState(false)
    const { isAuthenticated, user } = useAppSelector((state) => state.auth)

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 10)
        }
        window.addEventListener("scroll", handleScroll)
        return () => window.removeEventListener("scroll", handleScroll)
    }, [])

    return (
        <header
            className={`sticky top-0 z-50 w-full transition-all duration-300 ${isScrolled
                ? "bg-background/80 backdrop-blur-md border-b border-border"
                : "bg-transparent"
                }`}
        >
            <div className="max-w-7xl mx-auto px-6 md:px-8 border-x border-gray-200 dark:border-gray-800">
                <div className="flex h-16 items-center justify-between">
                    {/* Logo */}
                    <div className="flex items-center gap-2 mr-4">
                        <Link href="/" className="flex items-center gap-2">
                            <div className="bg-orange-500/10 p-1.5 rounded-lg border border-orange-500/30">
                                <Zap className="h-5 w-5 text-orange-500 fill-orange-500" />
                            </div>
                            <span className="text-xl font-bold tracking-tight text-foreground">InsightAPI<span className="text-orange-500">.AI</span></span>
                        </Link>
                    </div>

                    {/* Desktop Navigation */}
                    <div className="hidden md:flex items-center gap-1">
                        <NavigationMenu className="static">
                            <NavigationMenuList>
                                <NavigationMenuItem>
                                    <NavigationMenuTrigger className="bg-transparent cursor-pointer text-sm font-medium text-muted-foreground hover:text-primary data-[state=open]:bg-transparent hover:bg-transparent focus:bg-transparent">
                                        Products
                                    </NavigationMenuTrigger>
                                    <NavigationMenuContent className="!w-screen !max-w-[100vw] left-[50%] right-[50%] -ml-[50vw] -mr-[50vw]">
                                        <div className="container mx-auto grid grid-cols-1 md:grid-cols-[1fr_1fr_1.2fr] h-full w-full">
                                            {/* Column 1: Discovery */}
                                            <div className="flex flex-col border-r border-border py-8 px-6">
                                                <h4 className="text-sm font-medium text-muted-foreground mb-6 px-2">Discovery Engine</h4>
                                                <ul className="grid gap-1">
                                                    <ListItem href="/docs" title="Autonomous Crawler" icon={<Bot className="h-4 w-4 text-orange-500" />}>
                                                        Playwright AI driver with smart form populator & SPA state navigation
                                                    </ListItem>
                                                    <ListItem href="/docs" title="Accessibility Snapper" icon={<Cpu className="h-4 w-4 text-orange-500" />}>
                                                        Token-efficient AXTree extraction filtering raw 100k+ HTML bloat
                                                    </ListItem>
                                                    <ListItem href="/docs" title="Two-Tier Risk Classifier" icon={<Shield className="h-4 w-4 text-orange-500" />}>
                                                        Guardrail system protecting target sites from destructive actions
                                                    </ListItem>
                                                </ul>
                                            </div>

                                            {/* Column 2: Intelligence */}
                                            <div className="flex flex-col border-r border-border py-8 px-6">
                                                <h4 className="text-sm font-medium text-muted-foreground mb-6 px-2">Intelligence & Exports</h4>
                                                <ul className="grid gap-1">
                                                    <ListItem href="/docs" title="OpenAPI 3.1 & Postman" icon={<FileText className="h-4 w-4 text-orange-500" />}>
                                                        Instant one-click specification export with auto schemas
                                                    </ListItem>
                                                    <ListItem href="/docs" title="Network Observer" icon={<Network className="h-4 w-4 text-orange-500" />}>
                                                        Intercepts hidden AJAX/XHR, GraphQL operations & REST routes
                                                    </ListItem>
                                                    <ListItem href="/docs" title="Path Normalizer" icon={<Sparkles className="h-4 w-4 text-orange-500" />}>
                                                        Normalizes dynamic resource URLs into parameterized /users/{'{id}'}
                                                    </ListItem>
                                                </ul>
                                            </div>

                                            {/* Column 3: Platform Highlight */}
                                            <div className="flex flex-col justify-between py-8 px-6 bg-muted/40">
                                                <div>
                                                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-500 border border-orange-500/20 mb-4">
                                                        <Terminal className="h-3.5 w-3.5" /> Python SDK Available
                                                    </div>
                                                    <h3 className="text-lg font-semibold tracking-tight text-foreground mb-2">
                                                        Embed Autonomous API Extraction directly into your CI/CD pipeline
                                                    </h3>
                                                    <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                                                        Run <code className="bg-background px-1.5 py-0.5 rounded border border-border text-foreground font-mono">pip install insightapi</code> for zero-dependency in-memory session mode.
                                                    </p>
                                                </div>
                                                <Link href="/docs" className="inline-flex items-center justify-center rounded-md text-xs font-medium px-3 py-1.5 w-fit cursor-pointer bg-orange-500 hover:bg-orange-600 text-white transition-colors">
                                                    Explore Python SDK <ArrowRight className="ml-1 h-3.5 w-3.5" />
                                                </Link>
                                            </div>
                                        </div>
                                    </NavigationMenuContent>
                                </NavigationMenuItem>
                            </NavigationMenuList>
                        </NavigationMenu>

                        <Link href="/docs" className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                            Docs & SDK
                        </Link>
                        <Link href="#features" className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                            Features
                        </Link>
                        <Link href="#pricing" className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                            Pricing
                        </Link>
                        <Link href="#faq" className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                            FAQ
                        </Link>
                    </div>

                    {/* Action Buttons */}
                    <div className="hidden md:flex items-center gap-3">
                        {isAuthenticated ? (
                            <Link href="/dashboard" className="inline-flex items-center justify-center rounded-md text-sm font-medium px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white cursor-pointer transition-colors">
                                Dashboard ({user?.name || user?.email?.split('@')[0]})
                            </Link>
                        ) : (
                            <>
                                <Link href="/login" className="inline-flex items-center justify-center rounded-md text-xs font-medium px-3 py-1.5 hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors">
                                    Sign In
                                </Link>
                                <Link href="/login" className="inline-flex items-center justify-center rounded-md text-xs font-medium px-3.5 py-1.5 bg-orange-500 hover:bg-orange-600 text-white cursor-pointer transition-colors">
                                    Get Started Free
                                </Link>
                            </>
                        )}
                    </div>

                    {/* Mobile Menu Button */}
                    <div className="flex md:hidden">
                        <Sheet open={isOpen} onOpenChange={setIsOpen}>
                            <SheetTrigger className="p-2 rounded-md hover:bg-accent cursor-pointer">
                                <Menu className="h-6 w-6" />
                            </SheetTrigger>
                            <SheetContent side="right" className="w-[300px] sm:w-[350px]">
                                <SheetTitle className="text-left font-bold flex items-center gap-2">
                                    <Zap className="h-5 w-5 text-orange-500 fill-orange-500" />
                                    InsightAPI AI
                                </SheetTitle>
                                <div className="flex flex-col gap-4 mt-6">
                                    <Accordion type="single" collapsible className="w-full">
                                        <AccordionItem value="products">
                                            <AccordionTrigger className="text-sm font-medium">Products & Engine</AccordionTrigger>
                                            <AccordionContent className="flex flex-col gap-2 pt-2">
                                                <Link href="/docs" onClick={() => setIsOpen(false)} className="text-sm text-muted-foreground hover:text-foreground">Autonomous Crawler</Link>
                                                <Link href="/docs" onClick={() => setIsOpen(false)} className="text-sm text-muted-foreground hover:text-foreground">Accessibility Snapper</Link>
                                                <Link href="/docs" onClick={() => setIsOpen(false)} className="text-sm text-muted-foreground hover:text-foreground">OpenAPI & Postman Export</Link>
                                                <Link href="/docs" onClick={() => setIsOpen(false)} className="text-sm text-muted-foreground hover:text-foreground">Python SDK</Link>
                                            </AccordionContent>
                                        </AccordionItem>
                                    </Accordion>
                                    <Link href="/docs" onClick={() => setIsOpen(false)} className="text-sm font-medium">Docs & SDK</Link>
                                    <Link href="#features" onClick={() => setIsOpen(false)} className="text-sm font-medium">Features</Link>
                                    <Link href="#pricing" onClick={() => setIsOpen(false)} className="text-sm font-medium">Pricing</Link>
                                    <Link href="#faq" onClick={() => setIsOpen(false)} className="text-sm font-medium">FAQ</Link>

                                    <div className="flex flex-col gap-2 mt-4 pt-4 border-t border-border">
                                        {isAuthenticated ? (
                                            <Link href="/dashboard" onClick={() => setIsOpen(false)} className="inline-flex items-center justify-center rounded-md text-sm font-medium px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white w-full text-center">
                                                Go to Dashboard
                                            </Link>
                                        ) : (
                                            <>
                                                <Link href="/login" onClick={() => setIsOpen(false)} className="inline-flex items-center justify-center rounded-md text-sm font-medium px-4 py-2 border border-border hover:bg-accent w-full text-center">
                                                    Sign In
                                                </Link>
                                                <Link href="/login" onClick={() => setIsOpen(false)} className="inline-flex items-center justify-center rounded-md text-sm font-medium px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white w-full text-center">
                                                    Get Started Free
                                                </Link>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </SheetContent>
                        </Sheet>
                    </div>
                </div>
            </div>
        </header>
    )
}
