import React from "react";
import styles from "./QueryPage.module.less";

import { Skeleton, Input, Divider } from "antd";
import { QueryResult, QueryStore } from "../store";
import { useVal } from "use-value-enhancer";

const { Search } = Input;

export const QueryPage: React.FC<{}> = () => {
  const store = React.useMemo(() => new QueryStore(), []);
  const isQuerying = useVal(store.$.isQuerying);
  const queryResults = useVal(store.$.queryResult);
  const onSearch = React.useCallback(
    (query: string) => store.query(query),
    [],
  );
  let tailView: React.ReactNode = null;

  if (isQuerying) {
    tailView = <Skeleton active />;
  } else if (queryResults) {
    tailView = <ResultDisplay result={queryResults} />;
  }
  return <>
    <div className={styles["query-box"]}>
      <Search
        placeholder="输入你要搜索的内容"
        allowClear
        onSearch={onSearch} />
      {tailView && <>
        <Divider />
        {tailView}
      </>}
    </div>
  </>;
};

type ResultDisplayProps = {
  readonly result: QueryResult;
};

const ResultDisplay: React.FC<ResultDisplayProps> = ({ result }) => {
  return (
    <div className={styles["query-result-box"]}>
      {JSON.stringify(result, undefined, 2)}
    </div>
  );
};