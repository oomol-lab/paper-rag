import React from "react";
import styles from "./Navigator.module.less";

import { Tabs } from "antd";
import { useLocation, useNavigate } from "react-router-dom";

export const Navigator: React.FC<{}> = () => {
  const navigate = useNavigate();
  const pathname = useLocation().pathname;
  const activeKey = pathname.split("/")[1] || undefined;
  const onChange = React.useCallback(
    (activeKey: string) => navigate("/" + activeKey),
    [navigate],
  );
  return (
    <div className={styles.navigator}>
      <Tabs
        activeKey={activeKey}
        onChange={onChange}
        items={[
          {
            key: "scanner",
            label: "知识库",
          },
          {
            key: "query",
            label: "查询",
          },
        ]} />
    </div>
  );
};