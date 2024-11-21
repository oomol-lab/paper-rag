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
  readonly fragments: readonly Omit<Fragment, "offset">[][];
};

const TextParagraph: React.FC<TextParagraphProps> = ({ fragments }) => (
  <div className={styles.paragraph}>
    {fragments.map((fragments, i) => (
      <TextLine
        key={`${i}`}
        fragments={fragments} />
    ))}
  </div>
);

type TextLineProps = {
  readonly fragments: readonly Omit<Fragment, "offset">[];
};

const TextLine: React.FC<TextLineProps> = ({ fragments }) => (
  <p>
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
);

type Fragment = {
  readonly content: string;
  readonly offset: number;
  readonly color: number;
};

enum Splitter {
  LineBreak = 0,
  Paragraph = 1,
}

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

  public split(): Omit<Fragment, "offset">[][][] {
    const paragraphs: Omit<Fragment, "offset">[][][] = [];
    let paragraph: Omit<Fragment, "offset">[][] = [];
    let line: Omit<Fragment, "offset">[] = [];

    for (const item of this.#splitWithSplitters()) {
      if (item === Splitter.LineBreak) {
        if (line.length > 0) {
          paragraph.push(line);
          line = [];
        }
      } else if (item === Splitter.Paragraph) {
        if (line.length > 0) {
          paragraph.push(line);
          line = [];
        }
        if (paragraph.length > 0) {
          paragraphs.push(paragraph);
          paragraph = [];
        }
      } else {
        line.push(item);
      }
    }
    return paragraphs;
  }

  *#splitWithSplitters(): Generator<Omit<Fragment, "offset"> | Splitter> {
    for (const fragment of this.#fragments) {
      // 令连续的多行回车变成标准的连续两个回车符（这些多行回车之间如果填充其他空白字符也会处理）
      const content = fragment.content.replace(/\n\s+\n/g, "\n\n");
      const cells = content.split("\n");

      for (let i = 0; i < cells.length; ++i) {
        const content = cells[i].trim();
        if (content === "") {
          yield Splitter.Paragraph;
        } else {
          yield {
            content: cells[i].trim(),
            color: fragment.color,
          }
        }
        if (i < cells.length - 1) {
          yield Splitter.LineBreak;
        }
      }
    }
    yield Splitter.Paragraph;
  }
}