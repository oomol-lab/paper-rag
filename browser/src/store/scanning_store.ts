import { fetchJson, fetchJsonEvents, EventFetcher } from "../utils";

type Event = {
  readonly kind: "scanning" | "completed" | "interrupted" | "heartbeat";
} | {
  readonly kind: "scanCompleted";
  readonly count: number;
} | {
  readonly kind: "completeHandingFile";
  readonly path: string;
} | {
  readonly kind: "failure";
  readonly error: string;
} | {
  readonly kind: "startHandingFile";
  readonly path: string;
} | {
  readonly kind: "completeHandingPdfPage";
  readonly index: number;
  readonly total: number;
} | {
  readonly kind: "completeIndexPdfPage";
  readonly index: number;
  readonly total: number;
};

export class ScanningStore {
  readonly #fetcher: EventFetcher<Event>;

  public constructor() {
    this.#fetcher = fetchJsonEvents<Event>("/api/scanning");
  }

  public async scan(): Promise<void> {
    await fetchJson("/api/scanning", { method: "POST" });
  }

  public close(): void {
    this.#fetcher.close();
  }

  public async runLoop(): Promise<void> {
    while (true) {
      const event = await this.#fetcher.get();
      if (!event) {
        break;
      }
      console.log("event", event);
    }
  }
}