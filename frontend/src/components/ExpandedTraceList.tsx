import React, { useMemo, useState } from "react";
import styled from "styled-components";
import { type TraceHeader } from "../hooks/useTraces";
import { ExpandedTraceRow } from "./ExpandedTraceRow";

// --- 1. TYPES ---
type SortKey = "start_time" | "total_cost" | "latency" | "status" | "name";
type SortDirection = "asc" | "desc";
type StatusFilter = "all" | "success" | "error";

interface SortConfig {
  key: SortKey;
  direction: SortDirection;
}

interface ExpandedTraceListProps {
  traces: TraceHeader[];
  selectedRunId: string | null;
  onSelectTrace: (run: TraceHeader) => void;
}

// Helper functions (omitted for brevity)
const getLatency = (start: string, end: string | null): number => {
  if (!end) return -1;
  return new Date(end).getTime() - new Date(start).getTime();
};

const getSortableValue = (trace: TraceHeader, key: SortKey) => {
  switch (key) {
    case "total_cost":
      return trace.total_cost ?? 0;
    case "latency":
      return getLatency(trace.start_time, trace.end_time);
    case "status":
      return trace.status;
    case "name":
      return trace.name;
    case "start_time":
    default:
      return new Date(trace.start_time).getTime();
  }
};

export const ExpandedTraceList = ({
  traces,
  selectedRunId,
  onSelectTrace,
}: ExpandedTraceListProps) => {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortConfigs, setSortConfigs] = useState<SortConfig[]>([
    { key: "start_time", direction: "desc" },
  ]);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredAndSortedTraces = useMemo(() => {
    const statusFiltered = traces.filter((trace) => {
      if (statusFilter === "all") return true;
      return trace.status === statusFilter;
    });

    const searchFiltered = statusFiltered.filter((trace) => {
      if (!searchTerm) return true;
      return trace.run_id.toLowerCase().includes(searchTerm.toLowerCase());
    });

    return searchFiltered.sort((a, b) => {
      for (const config of sortConfigs) {
        const valA = getSortableValue(a, config.key);
        const valB = getSortableValue(b, config.key);

        const direction = config.direction === "asc" ? 1 : -1;

        if (valA < valB) return -1 * direction;
        if (valA > valB) return 1 * direction;
      }
      return 0;
    });
  }, [traces, statusFilter, sortConfigs, searchTerm]);

  const handleSort = (key: SortKey, event: React.MouseEvent) => {
    const isShiftClick = event.shiftKey;
    const newConfigs = [...sortConfigs];
    const existingIndex = newConfigs.findIndex((c) => c.key === key);

    if (isShiftClick) {
      // MULTI-SORT LOGIC
      if (existingIndex > -1) {
        newConfigs[existingIndex].direction =
          newConfigs[existingIndex].direction === "asc" ? "desc" : "asc";
      } else {
        newConfigs.push({ key, direction: "asc" });
      }
      setSortConfigs(newConfigs);
    } else {
      // SINGLE-SORT LOGIC
      if (existingIndex > -1 && sortConfigs.length === 1) {
        const newDirection = sortConfigs[0].direction === "asc" ? "desc" : "asc";
        setSortConfigs([{ key, direction: newDirection }]);
      } else {
        const defaultDirection = key === "start_time" ? "desc" : "asc";
        setSortConfigs([{ key, direction: defaultDirection }]);
      }
    }
  };

  const getSortIndicator = (key: SortKey) => {
    const configIndex = sortConfigs.findIndex((c) => c.key === key);

    if (configIndex === -1) {
      return <SortIcon>▲▼</SortIcon>;
    }

    const config = sortConfigs[configIndex];
    const indicator = config.direction === "asc" ? "▲" : "▼";

    if (sortConfigs.length > 1) {
      return (
        <SortIcon $active>
          {indicator} {configIndex + 1}
        </SortIcon>
      );
    }

    return <SortIcon $active>{indicator}</SortIcon>;
  };

  return (
    <Wrapper>
      <FilterBar>
        <SearchInput
          type="text"
          placeholder="Search Run ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <FilterButton $active={statusFilter === "all"} onClick={() => setStatusFilter("all")}>
          All
        </FilterButton>
        <FilterButton
          $active={statusFilter === "success"}
          onClick={() => setStatusFilter("success")}
        >
          Success
        </FilterButton>
        <FilterButton $active={statusFilter === "error"} onClick={() => setStatusFilter("error")}>
          Error
        </FilterButton>
      </FilterBar>

      <HeaderRow>
        {/* 👇 --- MODIFIED FLEX LAYOUT FOR 9 COLUMNS --- 👇 */}
        {/* Total Flex: 3+2+1+1+1 + 2+2 = 12 */}
        <HeaderCell $flex={3} onClick={(e) => handleSort("name", e)}>
          Name / Run ID {getSortIndicator("name")}
        </HeaderCell>
        <HeaderCell $flex={2} onClick={(e) => handleSort("start_time", e)}>
          Date {getSortIndicator("start_time")}
        </HeaderCell>
        <HeaderCell $flex={1} onClick={(e) => handleSort("status", e)}>
          Status {getSortIndicator("status")}
        </HeaderCell>
        <HeaderCell $flex={1} $align="right" onClick={(e) => handleSort("total_cost", e)}>
          Cost {getSortIndicator("total_cost")}
        </HeaderCell>
        <HeaderCell $flex={1} $align="right" onClick={(e) => handleSort("latency", e)}>
          Latency {getSortIndicator("latency")}
        </HeaderCell>
        <HeaderCell $flex={2}>First Input</HeaderCell> {/* NEW */}
        <HeaderCell $flex={2}>Final Output</HeaderCell> {/* NEW */}
        {/* 👆 --- END MODIFIED FLEX LAYOUT --- 👆 */}
      </HeaderRow>
      <ListBody>
        {filteredAndSortedTraces.length > 0 ? (
          filteredAndSortedTraces.map((trace) => (
            <ExpandedTraceRow
              key={trace.run_id}
              trace={trace}
              onSelect={onSelectTrace}
              isSelected={trace.run_id === selectedRunId}
            />
          ))
        ) : (
          <EmptyResult>No traces found matching the current filters.</EmptyResult>
        )}
      </ListBody>
    </Wrapper>
  );
};

// --- STYLED COMPONENTS (Unchanged) ---

const SortIcon = styled.span<{ $active?: boolean }>`
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  min-width: 1.5em;
  color: ${(props) => (props.$active ? "#0d47a1" : "#aaa")};
  font-weight: ${(props) => (props.$active ? "bold" : "normal")};
`;

const SearchInput = styled.input`
  padding: 4px 10px;
  margin-right: 16px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  flex-grow: 1;
  min-width: 150px;
`;

const EmptyResult = styled.div`
  padding: 20px 16px;
  color: #757575;
  font-style: italic;
  font-size: 14px;
`;

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
`;

const FilterBar = styled.div`
  display: flex;
  padding: 8px 16px;
  border-bottom: 1px solid #e0e0e0;
  gap: 8px;
  flex-shrink: 0;
  align-items: center;
`;

const FilterButton = styled.button<{ $active: boolean }>`
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid ${(props) => (props.$active ? "#0d47a1" : "#ccc")};
  background-color: ${(props) => (props.$active ? "#e3f2fd" : "#fff")};
  color: ${(props) => (props.$active ? "#0d47a1" : "#333")};
  cursor: pointer;

  &:hover {
    background-color: ${(props) => (props.$active ? "#e3f2fd" : "#f5f5f5")};
  }
`;

const HeaderRow = styled.div`
  display: flex;
  align-items: center;
  padding: 10px 10px;
  border-bottom: 2px solid #ddd;
  background-color: #f9f9f9;
  flex-shrink: 0;
`;

const HeaderCell = styled.div<{ $flex: number; $align?: string }>`
  flex: ${(props) => props.$flex};
  font-size: 12px;
  font-weight: 600;
  color: #555;
  padding: 0 6px;
  cursor: pointer;
  text-align: ${(props) => props.$align || "left"};
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: ${(props) => (props.$align === "right" ? "flex-end" : "flex-start")};

  &:hover {
    color: #000;
  }
`;

const ListBody = styled.div`
  overflow-y: auto;
  flex-grow: 1;
`;
