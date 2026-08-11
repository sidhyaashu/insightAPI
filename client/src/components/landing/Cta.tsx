import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { ArrowRight, Terminal } from 'lucide-react'

export default function Cta() {
    return (
        <section>
            <div className="mx-auto max-w-7xl border border-gray-200 dark:border-gray-800 px-6 md:px-8 py-24 sm:py-32 bg-background">
                <div className="space-y-6 text-center max-w-3xl mx-auto">
                    <h2 className="text-foreground text-balance text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight">
                        Start Autonomously Mapping Web APIs in Seconds
                    </h2>
                    <p className="text-muted-foreground text-base sm:text-lg">
                        Turn raw web applications into complete, validated OpenAPI 3.1 & Postman documentation automatically.
                    </p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4">
                        <Link
                            href="/login"
                            className="inline-flex items-center justify-center rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-medium cursor-pointer px-8 py-4 text-base shadow-lg shadow-orange-500/20 transition-all">
                            Get Started Free <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                        <Link
                            href="/docs"
                            className="inline-flex items-center justify-center rounded-lg border border-gray-700 bg-background hover:bg-muted font-medium cursor-pointer px-8 py-4 text-base transition-all">
                            <Terminal className="mr-2 h-4 w-4 text-orange-500" /> Explore Python SDK
                        </Link>
                    </div>
                </div>
            </div>
        </section>
    )
}
