import React from "react";
import styles from "./QueryPage.module.less";

import { Tag, Empty, Skeleton, Input, List } from "antd";
import { useVal } from "use-value-enhancer";
import { useSearchParams } from "react-router-dom";
import { PDFPageItem, QueryItem, QueryKeyword, QueryStore } from "../store";
import { PDFTagLink } from "./Link";
import { HighlightProvider } from "./HighlightTag";
import { Text } from "./Text";

const { Search } = Input;

export const QueryPage: React.FC<{}> = () => {
  const store = React.useMemo(() => new QueryStore(), []);
  const isQuerying = useVal(store.$.isQuerying);
  const items = useVal(store.$.items);
  const keywords = useVal(store.$.keywords);
  const [searchParams, setSearchParams] = useSearchParams();
  let query: string | null | undefined = searchParams.get("query");

  if (typeof query !== "string" || query.trim() === "") {
    query = undefined;
  }
  React.useEffect(
    () => {
      if (typeof query === "string") {
        store.query(query);
      } else {
        store.cleanQuery();
      }
    },
    [store, query],
  );
  const onSearch = React.useCallback(
    (query: string) => {
      if (query.trim() === "") {
        setSearchParams({});
      } else {
        setSearchParams({ query });
      }
    },
    [setSearchParams],
  );
  let tailView: React.ReactNode = null;

  if (isQuerying) {
    tailView = <Skeleton active />;
  } else if (items) {
    tailView = (
      <ResultDisplay
        store={store}
        items={items}
        keywords={keywords} />
    );
  }
  return (
    <div className={styles.root}>
      <div className={styles["query-box"]}>
        <Search
          placeholder="输入你要搜索的内容"
          defaultValue={query}
          allowClear
          onSearch={onSearch} />
      </div>
      {tailView}
    </div>
  );
};

type ResultDisplayProps = {
  readonly store: QueryStore;
  readonly items: readonly QueryItem[];
  readonly keywords: readonly QueryKeyword[];
};

const ResultDisplay: React.FC<ResultDisplayProps> = ({ store, items, keywords }) => {
  return <>
    <Keywords
      store={store}
      keywords={keywords} />
    <HighlightProvider keywords={keywords}>
      <div className={styles["query-result-box"]}>
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
    </HighlightProvider>
  </>;
};

type KeywordsProps = {
  readonly store: QueryStore;
  readonly keywords: readonly QueryKeyword[];
};

const Keywords: React.FC<KeywordsProps> = ({ store, keywords }) => {
  const onChangeTag = React.useCallback(
    (name: string, checked: boolean) => store.checkTag(name, checked),
    [store],
  );
  return (
    <div className={styles["keywords-bar"]}>
      <label>关键词：</label>
      {keywords.map((keyword, index) => (
        <Tag.CheckableTag
          key={`${index}`}
          checked={keyword.checked}
          onChange={checked => onChangeTag(keyword.name, checked)} >
          {keyword.name}
        </Tag.CheckableTag>
      ))}
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
      <List>
        <List.Item>
          <List.Item.Meta
            title="距离"
            description={distance} />
          <List.Item.Meta
            title="匹配片段"
            description={segments.length} />
        </List.Item>
        <List.Item.Meta
          title="文件"
          description={
            pdf_files.map((pdf, index) => (
              <PDFTagLink
                key={`${index}`}
                path={pdf.pdf_path}
                page={pdf.page_index} />
            ))
          } />
      </List>
      <Text
        className={styles.text}
        content={content}
        segments={segments} />
    </div>
  );
};