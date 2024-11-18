import React from "react";
import styles from "./App.module.less";
import zhCN from "antd/locale/zh_CN";

import { useNavigate, BrowserRouter, Routes, Route } from "react-router-dom";
import { Button, Result, ConfigProvider } from "antd";

export const App: React.FC<{}> = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ConfigProvider>
  )
};

const AppRoutes: React.FC<{}> = () => (
  <Routes>
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