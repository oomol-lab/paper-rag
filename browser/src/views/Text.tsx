import React from "react";
import styles from "./Text.module.less";

import { HighlightSegment } from "../store";

export type TextProps = React.HTMLAttributes<HTMLDivElement> & {
  readonly content: string;
  readonly segments: readonly HighlightSegment[];
};

enum SegmentKind {
  Background = 0,
  Chunk = 1,
  Highlight = 2,
}

export const Text: React.FC<TextProps> = ({ content, segments, ...rest }) => {
  const dyeing = new Dyeing(content);
  for (const { start, end, highlights } of segments) {
    dyeing.dye(start, end - start, SegmentKind.Chunk);
    for (const [hStart, hEnd] of highlights) {
      dyeing.dye(start + hStart, hEnd - hStart, SegmentKind.Highlight);
    }
  }
  return (
    <div {...rest}>
      {dyeing.split().map((fragments, i) => (
        <TextParagraph
          key={`${i}`}
          fragments={fragments} />
      ))}
    </div>
  );
};

type TextParagraphProps = {
  readonly fragments: readonly Omit<Fragment, "offset">[];
};

const TextParagraph: React.FC<TextParagraphProps> = ({ fragments }) => (
  <p className={styles.p}>
    {fragments.map((fragment, i) => {
      switch (fragment.color) {
        case SegmentKind.Background: {
          return fragment.content;
        }
        case SegmentKind.Chunk: {
          return (
            <span
              key={`${i}`}
              className={styles.chunk}>
              {fragment.content}
            </span>
          );
        }
        case SegmentKind.Highlight: {
          return (
            <span
              key={`${i}`}
              className={styles.highlight}>
              {fragment.content}
            </span>
          );
        }
      }
    })}
  </p>
)

type Fragment = {
  readonly content: string;
  readonly offset: number;
  readonly color: number;
};

class Dyeing {
  #fragments: readonly Fragment[];

  public constructor(content: string) {
    this.#fragments = [{ content, offset: 0, color: 0 }];
  }

  public dye(offset: number, length: number, color: number): void {
    const newFragments: Fragment[] = [];

    for (const fragment of this.#fragments) {
      if (fragment.offset + fragment.content.length <= offset) {
        newFragments.push(fragment);
        continue;
      }
      if (fragment.offset >= offset + length) {
        newFragments.push(fragment);
        continue;
      }
      if (fragment.color >= color) {
        newFragments.push(fragment);
        continue;
      }
      const fragmentBegin = Math.max(fragment.offset, offset);
      const fragmentEnd = Math.min(fragment.offset + fragment.content.length, offset + length);
      const newContent = fragment.content.slice(fragmentBegin - fragment.offset, fragmentEnd - fragment.offset);

      if (fragmentBegin > fragment.offset) {
        newFragments.push({
          content: fragment.content.slice(0, fragmentBegin - fragment.offset),
          offset: fragment.offset,
          color: fragment.color,
        });
      }

      newFragments.push({
        content: newContent,
        offset: fragmentBegin,
        color,
      });

      if (fragmentEnd < fragment.offset + fragment.content.length) {
        newFragments.push({
          content: fragment.content.slice(fragmentEnd - fragment.offset),
          offset: fragmentEnd,
          color: fragment.color,
        });
      }
    }
    this.#fragments = newFragments;
  }

  public split(): Omit<Fragment, "offset">[][] {
    const fragmentMatrix: Omit<Fragment, "offset">[][] = [];
    let fragments: Omit<Fragment, "offset">[] = [];

    for (const fragment of this.#fragments) {
      const content = fragment.content.replace(/[\s]+/, " ");
      const cells = content.split(/[\r\n]+/)
      if (cells.length === 1) {
        fragments.push({
          content: cells[0].trim(),
          color: fragment.color,
        });
      } else {
        for (let i = 0; i < cells.length; ++ i) {
          fragments.push({
            content: cells[i].trim(),
            color: fragment.color,
          });
          if (i < cells.length - 1) {
            fragmentMatrix.push(fragments);
            fragments = [];
          }
        }
      }
    }
    if (fragments.length > 0) {
      fragmentMatrix.push(fragments);
    }
    return fragmentMatrix;
  }
}