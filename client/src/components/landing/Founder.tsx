import React from 'react'
import { Testimonial } from "@/components/ui/testimonial";

const Founder = () => {
    return (
        <Testimonial
            companyLogo="https://shadcnblocks.com/images/block/block-1.svg"
            quote="InsightAPI delivers autonomous web intelligence that eliminates manual API reverse-engineering for engineering teams worldwide"
            highlightedText="InsightAPI"
            authorName="Alex Rivera"
            authorPosition="Lead Systems Architect & Creator, InsightAPI"
            authorImage="https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=400&auto=format&fit=crop"
        />
    )
}

export default Founder;
