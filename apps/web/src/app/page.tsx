import { StaticAmbient } from "@/components/brand/ambient";
import { DeskCards } from "@/components/landing/desk-cards";
import { Faq } from "@/components/landing/faq";
import { LandingNav } from "@/components/landing/landing-nav";
import { OrbitManifesto } from "@/components/landing/orbit-manifesto";
import { ReadYourWay } from "@/components/landing/read-your-way";
import { World } from "@/components/landing/world";

import "@/components/landing/landing.css";

export default function Home() {
  return (
    <div className="lp brand-scope flex-1">
      <StaticAmbient />
      <LandingNav />
      <main>
        <OrbitManifesto />
        <ReadYourWay />
        <DeskCards />
        <World />
        <Faq />
      </main>
    </div>
  );
}
