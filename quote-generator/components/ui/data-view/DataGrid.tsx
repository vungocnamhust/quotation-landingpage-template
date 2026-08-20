"use client";

import React from "react";
import { cn } from "../../../utils/cn.ts";

export interface DataGridProps<T> {
  items: T[];
  keyExtractor: (item: T, index: number) => string;
  renderItem: (item: T, index: number) => React.ReactNode;
  gridClassName?: string;
}

export function DataGrid<T>({
  items,
  keyExtractor,
  renderItem,
  gridClassName,
}: DataGridProps<T>) {
  return (
    <div
      className={cn(
        "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
        gridClassName
      )}
    >
      {items.map((item, index) => (
        <React.Fragment key={keyExtractor(item, index)}>
          {renderItem(item, index)}
        </React.Fragment>
      ))}
    </div>
  );
}
