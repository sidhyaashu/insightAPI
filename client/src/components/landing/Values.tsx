import { Casestudy } from "@/components/ui/casestudy";
import React from 'react';

const Values = () => {
    return (
        <div className="max-w-7xl mx-auto border border-gray-200 dark:border-gray-800 py-24 sm:py-32 bg-background">
            <Casestudy 
                featuredCasestudy={{
                    logo: "https://shadcnblocks.com/images/block/block-1.svg",
                    company: "Enterprise E-Commerce",
                    tags: "AUTONOMOUS EXPLORATION / OPENAPI GENERATION",
                    title: "Automated API Documentation for 1,200+ Endpoints.",
                    subtitle: "How a major digital platform mapped non-documented legacy endpoints in under 15 minutes.",
                    image: "https://images.unsplash.com/photo-1522071820081-009f0129c71c?q=80&w=2070&auto=format&fit=crop",
                    link: "#",
                }}
                casestudies={[
                    {
                        logo: "https://shadcnblocks.com/images/block/block-2.svg",
                        company: "FinTech Platform",
                        tags: "SECURITY AUDITING / TWO-TIER SAFETY",
                        title: "Safe exploration of sensitive web applications.",
                        subtitle: "Protecting live transaction flows while mapping API dependencies.",
                        image: "",
                        link: "#",
                    },
                    {
                        logo: "https://shadcnblocks.com/images/block/block-3.svg",
                        company: "AI Developer Stack",
                        tags: "PYTHON SDK / CI/CD INTEGRATION",
                        title: "Continuous API schema validation in GitHub Actions.",
                        subtitle: "Detecting breaking endpoint changes automatically before production release.",
                        image: "",
                        link: "#",
                    },
                ]}
            />
        </div>
    )
}

export default Values;
