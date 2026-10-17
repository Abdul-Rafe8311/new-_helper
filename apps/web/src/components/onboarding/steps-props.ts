import type { Dispatch } from "react";

import type { Action, Draft } from "./machine";

export type StepProps = {
  draft: Draft;
  dispatch: Dispatch<Action>;
};
