import React from "react";
import styles from "./QueryPage.module.less";

import { Tag, Empty, Skeleton, Input, Divider, Descriptions } from "antd";
import { useVal } from "use-value-enhancer";
import { PDFPageItem, QueryResult, QueryStore } from "../store";
import { PDFTagLink } from "./Link";
import { Text } from "./Text";

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
  const { keywords, items } = result;
  return (
    <div className={styles["query-result-box"]}>
      <div className={styles["keywords-bar"]}>
        <label>关键词：</label>
        {keywords.map((keyword, index) => (
          <Tag key={`${index}`}>{keyword}</Tag>
        ))}
      </div>
      {items.length === 0 && (
        <Empty
          className={styles.empty}
          description="没有搜索到内容" />
      )}
      {items.map((item, index) => {
        if (!("content" in item)) {
          // TODO: 对 PDF Metadata 本身的搜索
          return null;
        }
        return (
          <PDFPageCard key={`${index}`} item={item} />
        );
      })}
    </div>
  );
};

type PDFPageCardProps = {
  readonly item: PDFPageItem;
};

const PDFPageCard: React.FC<PDFPageCardProps> = ({ item }) => {
  const { distance, pdf_files, content, segments } = item;
  return (
    <div className={styles["pdf-page-card"]}>
      <Descriptions
        layout="vertical"
        items={[{
          key: "1",
          label: "文件",
          children: pdf_files.map((pdf, index) => (
            <PDFTagLink
              key={`${index}`}
              path={pdf.pdf_path}
              page={pdf.page_index} />
          )),
        }, {
          key: "2",
          label: "距离",
          children: distance,
        }, {
          key: "3",
          label: "匹配片段",
          children: segments.length,
        }]} />
      <Text
        className={styles.text}
        content={content}
        segments={segments} />
    </div>
  );
};