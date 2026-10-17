import { Globe } from "./globe";

/** Section: the topic taxonomy includes world regions, so the paper can follow them. */
export function World() {
  return (
    <section id="world" className="lp-world" aria-labelledby="lp-world-title">
      <div className="lp-world__copy">
        <h2 id="lp-world-title">The world, on your terms</h2>
        <p>
          Follow World, Europe or Pakistan, or any of the other topics in the paper. Stories are gathered from many sources across the
          web and kept only if they match what you chose.
        </p>
      </div>
      <Globe />
    </section>
  );
}
