import { val, derive, Val, ReadonlyVal } from "value-enhancer";
import { fetchJson, fetchJsonEvents, EventFetcher } from "../utils";

type Event = {
  readonly kind: "scanning" | "completed" | "interrupted" | "heartbeat";
} | {
  readonly kind: "scanCompleted";
  readonly count: number;
} | {
  readonly kind: "startHandingFile";
  readonly path: string;
}| {
  readonly kind: "completeHandingFile";
  readonly path: string;
} | {
  readonly kind: "completeHandingPdfPage";
  readonly index: number;
  readonly total: number;
} | {
  readonly kind: "completeIndexPdfPage";
  readonly index: number;
  readonly total: number;
} | {
  readonly kind: "failure";
  readonly error: string;
};

export type ScanningStore$ = {
  readonly phase: ReadonlyVal<ScanningPhase>;
  readonly scanCount: ReadonlyVal<number>;
  readonly handlingFile: ReadonlyVal<HandingFile | null>;
  readonly completedFiles: ReadonlyVal<readonly string[]>;
  readonly error: ReadonlyVal<string | null>;
};

export enum ScanningPhase {
  Ready,
  Scanning,
  HandingFiles,
  Completed,
  Error,
}

export type HandingFile = {
  readonly path: string;
  readonly handlePdfPage?: {
    readonly index: number;
    readonly total: number;
  };
  readonly indexPdfPage?: {
    readonly index: number;
    readonly total: number;
  };
};

export class ScanningStore {
  public readonly $: ScanningStore$;

  readonly #fetcher: EventFetcher<Event>;
  readonly #phase$: Val<ScanningPhase> = val(ScanningPhase.Ready);
  readonly #scanCount$: Val<number> = val(0);
  readonly #handlingFile$: Val<HandingFile | null> = val<HandingFile | null>(null);
  readonly #completedFiles$: Val<readonly string[]> = val<readonly string[]>([]);
  readonly #error$: Val<string | null> = val<string | null>(null);

  public constructor() {
    this.#fetcher = fetchJsonEvents<Event>("/api/scanning");
    this.$ = {
      phase: derive(this.#phase$),
      scanCount: derive(this.#scanCount$),
      handlingFile: derive(this.#handlingFile$),
      completedFiles: derive(this.#completedFiles$),
      error: derive(this.#error$),
    };
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
      switch (event.kind) {
        case "scanning": {
          this.#phase$.set(ScanningPhase.Scanning);
          this.#scanCount$.set(0);
          this.#handlingFile$.set(null);
          this.#completedFiles$.set([]);
          this.#error$.set(null);
          break;
        }
        case "scanCompleted": {
          this.#phase$.set(ScanningPhase.HandingFiles);
          this.#scanCount$.set(event.count);
          break;
        }
        case "startHandingFile": {
          this.#handlingFile$.set({ path: event.path });
          break;
        }
        case "completeHandingFile": {
          this.#handlingFile$.set(null);
          this.#completedFiles$.set([
            ...this.#completedFiles$.value,
            event.path,
          ]);
          break;
        }
        case "completeHandingPdfPage": {
          this.#handlingFile$.set({
            ...this.#handlingFile$.value!,
            handlePdfPage: {
              index: event.index,
              total: event.total,
            },
          });
          break;
        }
        case "completeIndexPdfPage": {
          this.#handlingFile$.set({
            ...this.#handlingFile$.value!,
            indexPdfPage: {
              index: event.index,
              total: event.total,
            },
          });
          break;
        }
        case "completed": {
          this.#phase$.set(ScanningPhase.Completed);
          break;
        }
        case "failure": {
          this.#phase$.set(ScanningPhase.Error);
          this.#error$.set(event.error);
          break;
        }
      }
    }
  }
}