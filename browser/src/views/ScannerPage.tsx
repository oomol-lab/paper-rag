import React from "react";
import styles from "./ScannerPage.module.less";

import { Skeleton, Button, Divider, Typography } from "antd";
import { ScanOutlined } from "@ant-design/icons";
import { val } from "value-enhancer";
import { useVal } from "use-value-enhancer";
import { ScannerStore } from "../store";
import { Sources } from "./Sources";

const { Title, Paragraph } = Typography;

export const ScannerPage: React.FC = () => {
  const store$ = React.useMemo(() => val<ScannerStore | null>(null), []);
  const store = useVal(store$);
  React.useEffect(
    () => void ScannerStore.load().then((store) => store$.set(store)),
    [store$],
  );
  if (!store) {
    return <Skeleton active />;
  }
  return (
    <div>
      <Sources store={store} />
      <Divider />
      <Scanner store={store} />
    </div>
  );
};

type ScannerProps = {
  readonly store: ScannerStore;
};

const Scanner: React.FC<ScannerProps> = ({ store }) => {
  return <>
    <Typography>
      <Title>扫描</Title>
      <Paragraph>
        当知识库中的文件发生变化后，手动扫描以同步。
      </Paragraph>
    </Typography>
    <Button
      type="primary"
      shape="round"
      size="large"
      className={styles["scan-button"]}
      icon={<ScanOutlined />} >
      扫  描
    </Button>
  </>;
}