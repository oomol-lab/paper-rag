import React from "react";
import styles from "./Link.module.less";

import { Tag, Tooltip } from "antd";
import { FilePdfFilled } from "@ant-design/icons";

export type PDFTagLinkProps = {
  readonly path: string;
  readonly page: number;
};

export const PDFTagLink: React.FC<PDFTagLinkProps> = ({ path, page }) => {
  const fileNames = path.split(/[/\\]/);
  const fileName = fileNames[fileNames.length - 1];
  if (!fileName) {
    return null;
  }
  const fileNameWithoutExt = fileName.replace(/\.[^.]+$/, "");
  return (
    <Tag
      icon={<FilePdfFilled color="#FFFFFF" />}
      color="#FF5502">
      <Tooltip title={path}>
        <a
          className={styles["pdf-a"]}
          href={`file://${path}`}
          download>
          {fileNameWithoutExt}
        </a>
      </Tooltip>
      <span className={styles["pdf-page"]}>
        第 {page + 1} 页
      </span>
    </Tag>
  );
};