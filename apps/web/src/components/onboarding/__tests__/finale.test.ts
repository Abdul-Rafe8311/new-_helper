import { describe, expect, it } from "vitest";

import { phaseFromStatus, stageIndex, type Phase } from "../finale";

const starting: Phase = { kind: "starting" };

describe("phaseFromStatus", () => {
  it("follows the stage the server reports", () => {
    expect(phaseFromStatus({ status: "pending", stage: "choosing" }, starting)).toEqual({
      kind: "printing",
      stage: "choosing",
    });
  });

  it("starts at gathering when no stage is reported yet", () => {
    expect(phaseFromStatus({ status: "pending" }, starting)).toEqual({ kind: "printing", stage: "gathering" });
    expect(phaseFromStatus({ status: "none" }, starting)).toEqual({ kind: "printing", stage: "gathering" });
  });

  it("never steps backwards", () => {
    const writing: Phase = { kind: "printing", stage: "writing" };
    expect(phaseFromStatus({ status: "pending", stage: "gathering" }, writing)).toEqual(writing);
    expect(phaseFromStatus({ status: "pending", stage: "typesetting" }, writing)).toEqual({
      kind: "printing",
      stage: "typesetting",
    });
  });

  it("finishes on ready and reports failures", () => {
    expect(phaseFromStatus({ status: "ready", stage: "done" }, starting)).toEqual({ kind: "ready" });
    expect(phaseFromStatus({ status: "failed" }, starting).kind).toBe("failed");
  });

  it("orders the stages", () => {
    expect(["gathering", "choosing", "writing", "typesetting"].map((s) => stageIndex(s as never))).toEqual([0, 1, 2, 3]);
  });
});
