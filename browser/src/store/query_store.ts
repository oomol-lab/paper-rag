import { val, derive, Val, ReadonlyVal } from "value-enhancer";
import { message } from "antd";
import { fetchJson } from "../utils";

export type QueryStore$ = {
  readonly isQuerying: ReadonlyVal<boolean>;
  readonly queryResult: ReadonlyVal<QueryResult | null>;
};

export type QueryResult = {
  readonly keywords: readonly string[];
  readonly items: readonly QueryItem[];
};

export type QueryItem = PDFMetadataItem | PDFPageItem;

export type PDFMetadataItem = {
  readonly pdf_files: readonly string[];
  readonly distance: number;
  readonly metadata: {
    readonly author: string | null;
    readonly modified_at: string | null;
    readonly producer: string | null;
  };
};

export type PDFPageItem = {
  readonly pdf_files: readonly {
    readonly pdf_path: string;
    readonly page_index: number;
  }[];
  readonly distance: number;
  readonly content: string;
  readonly segments: readonly HighlightSegment[];
  readonly annotations: readonly {
    readonly index: number;
    readonly distance: number;
    readonly content: string;
    readonly segments: readonly HighlightSegment[];
  }[];
};

export type HighlightSegment = {
  readonly start: number;
  readonly end: number;
  readonly highlights: readonly [number, number][];
};

export class QueryStore {
  public readonly $: QueryStore$;

  readonly #isQuerying$: Val<boolean> = val(false);
  readonly #queryResult$: Val<QueryResult | null> = val<QueryResult | null>(null);

  public constructor() {
    this.$ = {
      isQuerying: derive(this.#isQuerying$),
      queryResult: derive(this.#queryResult$),
    };
  }

  public query(text: string): void {
    const query = new URLSearchParams({
      query: text,
    });
    this.#isQuerying$.set(true);
    fetchJson<QueryResult>(`/api/query?${query}`)
      .then((queryResults) => {
        this.#queryResult$.set(queryResults);
      })
      .catch((error) => {
        console.error(error);
        message.error(error.message);
      })
      .finally(() => {
        this.#isQuerying$.set(false);
      });
  }
}