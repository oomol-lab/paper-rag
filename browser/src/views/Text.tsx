import React from "react";

import { HighlightSegment } from "../store";

export type TextProps = React.HTMLAttributes<HTMLDivElement> & {
  readonly content: string;
  readonly segments: readonly HighlightSegment[];
};

export const Text: React.FC<TextProps> = ({ content, segments, ...rest }) => {
  return (
    <div {...rest}>
      {content}
    </div>
  );
};