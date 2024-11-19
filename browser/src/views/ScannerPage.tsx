import React from "react";
import styles from "./ScannerPage.module.less";

import { Skeleton, Result, Steps, List, Button, Divider, Progress, Typography } from "antd";
import { ScanOutlined, ProfileTwoTone, SyncOutlined, FilePdfTwoTone } from "@ant-design/icons";
import { val } from "value-enhancer";
import { useVal } from "use-value-enhancer";
import { ScannerStore, ScanningStore, ScanningPhase } from "../store";
import { Sources } from "./Sources";

const { Title, Paragraph } = Typography;

export const ScannerPage: React.FC = () => {
  const store$ = React.useMemo(() => val<ScannerStore | null>(null), []);
  const store = useVal(store$);
  React.useEffect(
    () => {
      let shouldClose = false;
      ScannerStore.load().then((store) => {
        if (shouldClose) {
          store.close();
        }
        store$.set(store);
      });
      return () => {
        shouldClose = true;
        store$.value?.close();
      };
    },
    [store$],
  );
  if (!store) {
    return <Skeleton active />;
  }
  return (
    <div className={styles.root}>
      <Sources store={store} />
      <Divider />
      <Scanner store={store} />
      <ScanningPanel store={store.scanningStore} />
    </div>
  );
};

type ScannerProps = {
  readonly store: ScannerStore;
};

const Scanner: React.FC<ScannerProps> = ({ store }) => {
  const scanningStore = store.scanningStore;
  const isScanning = useVal(scanningStore.$.isScanning);
  const onClickScan = React.useCallback(
    () => scanningStore.scan(),
    [scanningStore],
  );
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
      disabled={isScanning}
      loading={isScanning}
      icon={<ScanOutlined />}
      onClick={onClickScan} >
      扫  描
    </Button>
  </>;
}

type ScanningPanelProps = {
  readonly store: ScanningStore;
};

const ScanningPanel: React.FC<ScanningPanelProps> = ({ store }) => {
  type Record = {
    readonly icon: React.ReactNode;
    readonly title: string;
    readonly content: string;
    readonly loading: boolean;
  };
  const records: Record[] = [];
  const phase = useVal(store.$.phase);
  const scanCount = useVal(store.$.scanCount);
  const completedFiles = useVal(store.$.completedFiles);
  const handlingFile = useVal(store.$.handlingFile);
  const error = useVal(store.$.error);

  let currentIndex: number;
  let status: "wait" | "process" | "finish" | "error" = "process";

  switch (phase) {
    case ScanningPhase.Ready: {
      return null;
    }
    case ScanningPhase.Scanning: {
      currentIndex = 0;
      break;
    }
    case ScanningPhase.HandingFiles: {
      currentIndex = 1;
      break;
    }
    case ScanningPhase.Completed: {
      currentIndex = 2;
      status = "finish";
      break;
    }
    case ScanningPhase.Error: {
      currentIndex = 2;
      status = "error";
      break;
    }
  }
  if (phase === ScanningPhase.Scanning) {
    records.push({
      icon: <ProfileTwoTone />,
      title: "扫描文件",
      content: `正在扫描文件的更新……`,
      loading: true,
    });
  } else {
    records.push({
      icon: <ProfileTwoTone />,
      title: "扫描文件",
      content: `扫描完成，发现 ${scanCount} 个文件有更新`,
      loading: false,
    });
  }
  for (const file of completedFiles) {
    records.push({
      icon: <FilePdfTwoTone />,
      title: "录入 PDF 文件",
      content: file,
      loading: false,
    });
  }
  if (handlingFile) {
    records.push({
      icon: <FilePdfTwoTone />,
      title: "录入 PDF 文件",
      content: handlingFile.path,
      loading: true,
    });
  }
  return <>
    <Steps
      className={styles["steps-bar"]}
      current={currentIndex}
      status={status}
      items={[
        { title: "扫描" },
        { title: "处理文件" },
        { title: phase === ScanningPhase.Error ? "错误" : "完成" },
      ]}
    />
    <List
      itemLayout="horizontal"
      dataSource={records}
      renderItem={item => (
        <List.Item>
          <List.Item.Meta
            avatar={item.icon}
            title={item.title}
            description={item.content}
          />
          {item.loading && (
            <SyncOutlined spin />
          )}
        </List.Item>
      )}
    />
    <ProgressBar
      name="解析"
      pdfPage={handlingFile?.handlePdfPage} />
    <ProgressBar
      name="索引"
      pdfPage={handlingFile?.indexPdfPage} />
    {error && (
      <Result
        status="error"
        title="扫描失败"
        subTitle={error}
      />
    )}
  </>;
};

type ProgressBarProps = {
  readonly name: string;
  readonly pdfPage?: {
    readonly index: number;
    readonly total: number;
  };
};

const ProgressBar: React.FC<ProgressBarProps> = ({ name, pdfPage }) => {
  if (!pdfPage) {
    return null;
  }
  const { index, total } = pdfPage;
  const percent = Math.floor(Math.min(index / total, 1.0) * 100);
  const status = percent === 100 ? "success" : "active";
  return (
    <div className={styles["progress"]}>
      <label className={styles["progress-label"]}>
        {name}
      </label>
      <Progress
        className={styles["progress-bar"]}
        percent={percent}
        size="small"
        status={status} />
    </div>
  );
};