import { MoveRight } from "lucide-react";
import React from "react";

interface CasestudyItem {
    logo: string;
    company: string;
    tags: string;
    title: string;
    subtitle: string;
    image: string;
    link?: string;
}

interface CasestudyProps {
    featuredCasestudy?: CasestudyItem;
    casestudies?: CasestudyItem[];
}

const defaultFeaturedCasestudy: CasestudyItem = {
    logo: "https://shadcnblocks.com/images/block/block-1.svg",
    company: "Acme Analytics",
    tags: "AUTONOMOUS AGENTS / API INTELLIGENCE",
    title: "Zero-Downtime Web Exploration for E-Commerce Enterprise.",
    subtitle: "How InsightAPI mapped 1,200+ hidden endpoints automatically.",
    image: "https://images.unsplash.com/photo-1664575602442-bfa721d0ac0b?q=80&w=2000&auto=format&fit=crop",
    link: "#",
};

const defaultCasestudies: CasestudyItem[] = [
    {
        logo: "https://shadcnblocks.com/images/block/block-2.svg",
        company: "FinTech Global",
        tags: "OPENAPI DISCOVERY / SECURITY AUDITING",
        title: "Automated Postman collection generation for legacy portals.",
        subtitle: "A seamless transition to modern API specifications.",
        image: "",
        link: "#",
    },
    {
        logo: "https://shadcnblocks.com/images/block/block-3.svg",
        company: "SaaS Systems",
        tags: "AI CRAWLING / GRAPHQL PARSING",
        title: "Extracting GraphQL queries from single-page web applications.",
        subtitle: "Mastering complex SPA state transitions with accessibility trees.",
        image: "",
        link: "#",
    },
];

export const Casestudy = ({
    featuredCasestudy = defaultFeaturedCasestudy,
    casestudies = defaultCasestudies,
}: CasestudyProps) => {
    return (
        <section className="">
            <div className="container mx-auto">
                <div className="border border-border">
                    <a
                        href={featuredCasestudy.link || "#"}
                        className="group grid gap-4 overflow-hidden px-6 transition-colors duration-500 ease-out hover:bg-muted/40 lg:grid-cols-2 xl:px-28"
                    >
                        <div className="flex flex-col justify-between gap-4 pt-8 md:pt-16 lg:pb-16">
                            <div className="flex items-center gap-2 text-2xl font-medium">
                                {featuredCasestudy.company}
                            </div>
                            <div>
                                <span className="text-xs text-muted-foreground sm:text-sm">
                                    {featuredCasestudy.tags}
                                </span>
                                <h2 className="mt-4 mb-5 text-2xl font-semibold text-balance sm:text-3xl sm:leading-10">
                                    {featuredCasestudy.title}
                                    <span className="font-medium text-primary/50 transition-colors duration-500 ease-out group-hover:text-primary/70">
                                        {" "}
                                        {featuredCasestudy.subtitle}
                                    </span>
                                </h2>
                                <div className="flex items-center gap-2 font-medium text-orange-500">
                                    Read case study
                                    <MoveRight className="h-4 w-4 transition-transform duration-500 ease-out group-hover:translate-x-1" />
                                </div>
                            </div>
                        </div>
                        <div className="relative isolate py-16">
                            <div className="relative isolate h-full border border-border bg-background p-2">
                                <div className="h-full overflow-hidden">
                                    <img
                                        src={featuredCasestudy.image}
                                        alt="case study preview"
                                        className="aspect-[14/9] h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                                    />
                                </div>
                            </div>
                        </div>
                    </a>
                    <div className="flex border-t border-border">
                        <div className="hidden w-28 shrink-0 bg-[radial-gradient(var(--muted-foreground)_1px,transparent_1px)] [background-size:10px_10px] opacity-15 xl:block"></div>
                        <div className="grid lg:grid-cols-2">
                            {casestudies.map((item, idx) => (
                                <a
                                    key={idx}
                                    href={item.link || "#"}
                                    className="group flex flex-col justify-between gap-4 border-b border-border p-6 transition-colors duration-500 ease-out hover:bg-muted/40 last:border-b-0 lg:border-r lg:border-b-0 lg:p-8 lg:last:border-r-0"
                                >
                                    <div>
                                        <span className="text-xs text-muted-foreground sm:text-sm">
                                            {item.tags}
                                        </span>
                                        <h3 className="mt-2 text-xl font-semibold text-balance">
                                            {item.title}{" "}
                                            <span className="font-medium text-primary/50 transition-colors duration-500 ease-out group-hover:text-primary/70">
                                                {item.subtitle}
                                            </span>
                                        </h3>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm font-medium text-orange-500">
                                        Read case study
                                        <MoveRight className="h-4 w-4 transition-transform duration-500 ease-out group-hover:translate-x-1" />
                                    </div>
                                </a>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};
