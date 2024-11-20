import { val, derive, Val, ReadonlyVal } from "value-enhancer";
import { message } from "antd";
import { fetchJson } from "../utils";

export type QueryStore$ = {
  readonly isQuerying: ReadonlyVal<boolean>;
  readonly queryResult: ReadonlyVal<QueryResult | null>;
};

export type QueryResult = {};

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