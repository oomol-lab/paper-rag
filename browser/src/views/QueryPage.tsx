import React from "react";
import styles from "./QueryPage.module.less";

import { Input } from "antd";
import { QueryStore } from "../store";

const { Search } = Input;

export const QueryPage: React.FC<{}> = () => {
  const store = React.useMemo(() => new QueryStore(), []);
  const onSearch = React.useCallback(
    (query: string) => store.query(query),
    [],
  );
  return <>
    <div className={styles["query-box"]}>
      <Search
        placeholder="输入你要搜索的内容"
        allowClear
        onSearch={onSearch} />
    </div>
  </>;
};