import { PhoneCall, HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";

const faqs = [
    {
        question: "How does InsightAPI autonomously explore web applications?",
        answer: "InsightAPI uses Playwright to launch a browser session. Rather than feeding 100k+ HTML tokens to vision LLMs, it extracts an Accessibility Tree containing interactive semantic controls (a, button, input, select) and evaluates each element with a Two-Tier Risk Classifier before taking action."
    },
    {
        question: "How does the Two-Tier Risk Classifier prevent destructive actions?",
        answer: "Tier 1 uses sub-millisecond regex pre-filtering to identify obvious safe navigation vs unsafe destructive keywords (delete, pay, purchase, update password). Tier 2 evaluates parent form context to skip high-risk form submissions automatically, logging them without halting execution."
    },
    {
        question: "Can I use InsightAPI as a Python SDK without PostgreSQL?",
        answer: "Yes! InsightAPI is designed with a decoupled architecture. You can import insightapi in Python scripts or CI/CD pipelines in zero-dependency lightweight mode using in-memory session state."
    },
    {
        question: "How does endpoint path parameter normalization work?",
        answer: "Our network observer intercepts raw HTTP/GraphQL calls and automatically normalizes dynamic URL path variations (e.g. /users/101, /users/102) into structured route templates like /users/{id}."
    },
    {
        question: "What export formats are supported?",
        answer: "InsightAPI exports valid OpenAPI 3.1.0 specifications (JSON/YAML), Postman 2.1 collections, and clean Markdown API reference documentation."
    },
    {
        question: "Does InsightAPI support SPA applications and modal states?",
        answer: "Yes. InsightAPI computes DOM State Graph hashes combining normalized URLs and structural AXTree fingerprints to distinguish tab and modal states on SPAs like React or Next.js."
    }
];

function FAQ() {
    return (
        <div id="faq" className="max-w-7xl mx-auto border border-gray-200 dark:border-gray-800 bg-background">
            <div className="grid lg:grid-cols-2 gap-10 sm:gap-12">
                <div className="flex gap-8 sm:gap-10 flex-col px-6 md:px-8 md:px-12 lg:px-20 py-16 sm:py-20">
                    <div className="flex gap-4 flex-col">
                        <div>
                            <Badge variant="outline" className="border-orange-500/30 text-orange-500 bg-orange-500/10">
                                FAQ
                            </Badge>
                        </div>
                        <div className="flex gap-2 flex-col">
                            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl tracking-tight max-w-xl text-left font-semibold text-foreground">
                                Frequently Asked Questions
                            </h2>
                            <p className="text-base sm:text-lg max-w-xl lg:max-w-lg leading-relaxed text-muted-foreground text-left">
                                Everything you need to know about autonomous web API discovery, security guardrails, Python SDK integration, and OpenAPI specification export.
                            </p>
                        </div>
                        <div className="pt-2">
                            <a href="mailto:support@insightapi.ai" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-medium text-sm transition-all cursor-pointer">
                                Have Questions? Contact API Engineers <HelpCircle className="w-4 h-4" />
                            </a>
                        </div>
                    </div>
                </div>
                <Accordion type="single" collapsible className="w-full border-t lg:border-t-0 lg:border-l border-gray-200 dark:border-gray-800">
                    {faqs.map((faq, index) => (
                        <AccordionItem key={index} value={"index-" + index} className="border-b border-gray-200 dark:border-gray-800 p-6">
                            <AccordionTrigger className="cursor-pointer text-left text-foreground font-medium text-base hover:text-orange-500 hover:no-underline">
                                {faq.question}
                            </AccordionTrigger>
                            <AccordionContent className="text-muted-foreground leading-relaxed text-sm pt-2">
                                {faq.answer}
                            </AccordionContent>
                        </AccordionItem>
                    ))}
                </Accordion>
            </div>
        </div>
    );
}

export { FAQ };
