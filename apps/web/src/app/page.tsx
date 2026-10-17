import { LandingNav } from "@/components/landing/landing-nav";
import { OrbitManifesto } from "@/components/landing/orbit-manifesto";
import { ReadYourWay } from "@/components/landing/read-your-way";

import "@/components/landing/landing.css";

export default function Home() {
  return (
    <div className="lp flex-1">
      <LandingNav />
      <main>
        <OrbitManifesto />
        <ReadYourWay />
      </main>
    </div>
  );
}
