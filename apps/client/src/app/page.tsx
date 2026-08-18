"use client";

import NavBar from "@/components/landing/NavBar";
import Hero from "@/components/landing/Hero";
import Feature from "@/components/landing/Feature";
import Values from "@/components/landing/Values";
import { Integration } from "@/components/landing/Integration";
import Strength from "@/components/landing/Strength";
import Info from "@/components/landing/Info";
import Trust from "@/components/landing/Trust";
import Pricing from "@/components/landing/Pricing";
import { FAQ } from "@/components/landing/Faq";
import Cta from "@/components/landing/Cta";
import Founder from "@/components/landing/Founder";
import { ExpandableChatWidget } from "@/components/landing/ExpandableChatWidget";
import { Footer } from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="bg-background text-foreground min-h-screen selection:bg-primary selection:text-primary-foreground font-sans transition-colors duration-150">
      <NavBar />
      <Hero />
      <Feature />
      <Values />
      <Integration />
      <Strength />
      <Info />
      <Trust />
      <Pricing />
      <FAQ />
      <Cta />
      <Founder />
      <ExpandableChatWidget />
      <Footer />
    </div>
  );
}
