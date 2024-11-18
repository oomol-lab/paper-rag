import React from "react";
import styles from "./ScannerPage.module.less";

import { Skeleton } from "antd";
import { val } from "value-enhancer";
import { useVal } from "use-value-enhancer";
import { ScannerStore } from "../store";
import { Sources } from "./Sources";

export const ScannerPage: React.FC = () => {
  const store$ = React.useMemo(() => val<ScannerStore | null>(null), []);
  const store = useVal(store$);
  React.useEffect(
    () => void ScannerStore.load().then((store) => store$.set(store)),
    [store$],
  );
  if (store) {
    return <Sources store={store} />;
  } else {
    return <Skeleton active />;
  }
};
