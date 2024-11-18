import React from "react";
import cls from "classnames";
import styles from "./App.module.less";
import zhCN from "antd/locale/zh_CN";

import { useNavigate, BrowserRouter, Routes, Route } from "react-router-dom";
import { Button, Result, ConfigProvider } from "antd";
import { Navigator } from "./Navigator";
import { ScannerPage } from "./ScannerPage";

export const App: React.FC<{}> = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <div className={styles.app}>
          <header className={cls(styles.panel, styles["navigator-panel"])}>
            <Navigator />
          </header>
          <div className={cls(styles.panel, styles["main-panel"])}>
            <AppRoutes />
          </div>
        </div>
      </BrowserRouter>
    </ConfigProvider>
  )
};

const AppRoutes: React.FC<{}> = () => (
  <Routes>
    <Route path="/scanner" element={<ScannerPage />} />
    <Route path="*" element={<AppNotFound />} />
  </Routes>
);

const AppNotFound: React.FC<{}> = () => {
  const navigate = useNavigate();
  const onClick = React.useCallback(() => navigate("/"), [navigate]);
  return (
    <Result
      className={styles["not-found"]}
      status="404"
      title="404"
      subTitle="该页面不存在"
      extra={(
        <Button
          type="primary"
          onClick={onClick}>
          回到首页
        </Button>
      )}
    />
  );
};