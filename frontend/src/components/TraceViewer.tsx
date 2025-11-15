import { useState } from "react";
import styled from "styled-components";
import { useMockDatabase } from "../hooks/useMockDatabase";
import type { RawLangSmithRun } from "../types";

// --- Styled Components ---

const Wrapper = styled.div`
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100vw;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  border: 1px solid #e0e0e0;
  box-sizing: border-box;
`;

const Column = styled.div<{ $flex?: number }>`
  flex: ${(props) => props.$flex || 1};
  border-right: 1px solid #e0e0e0;
  overflow-y: auto;
  min-width: 200px;

  &:last-child {
    border-right: none;
  }
`;

const ColumnHeader = styled.div`
  padding: 12px 16px;
  font-weight: 600;
  font-size: 16px;
  border-bottom: 1px solid #e0e0e0;
  background-color: #f9f9f9;
  position: sticky;
  top: 0;
`;

const ListItem = styled.div<{ $active: boolean }>`
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  font-family: "Menlo", "Courier New", monospace;
  border-bottom: 1px solid #f0f0f0;
  background-color: ${(props) => (props.$active ? "#e3f2fd" : "transparent")};
  color: ${(props) => (props.$active ? "#0d47a1" : "inherit")};

  &:hover {
    background-color: ${(props) => (props.$active ? "#e3f2fd" : "#f5f5f5")};
  }
`;

const DetailView = styled.div`
  padding: 16px;
  font-size: 13px;
  font-family: "Menlo", "Courier New", monospace;
  line-height: 1.6;

  pre {
    white-space: pre-wrap;
    word-wrap: break-word;
  }
`;

const EmptyState = styled.div`
  padding: 16px;
  color: #757575;
  font-style: italic;
`;

// Type alias for our collection names
type CollectionName = keyof ReturnType<typeof useMockDatabase>;

export const TraceViewer = () => {
  const db = useMockDatabase();
  const collectionNames = Object.keys(db) as CollectionName[];

  // State to manage selections
  const [selectedCollection, setSelectedCollection] = useState<CollectionName | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<RawLangSmithRun | null>(null);

  // Get the list of documents for the currently selected collection
  const documents = selectedCollection ? db[selectedCollection] : [];

  const handleSelectCollection = (name: CollectionName) => {
    setSelectedCollection(name);
    setSelectedDocument(null); // Reset document when collection changes
  };

  const handleSelectDocument = (doc: RawLangSmithRun) => {
    setSelectedDocument(doc);
  };

  return (
    <Wrapper>
      {/* === COLUMN 1: COLLECTIONS === */}
      <Column>
        <ColumnHeader>Collections</ColumnHeader>
        {collectionNames.map((name) => (
          <ListItem
            key={name}
            $active={name === selectedCollection}
            onClick={() => handleSelectCollection(name)}
          >
            {name} ({db[name].length})
          </ListItem>
        ))}
      </Column>

      {/* === COLUMN 2: DOCUMENTS === */}
      <Column>
        <ColumnHeader>Documents (IDs)</ColumnHeader>
        {selectedCollection &&
          documents.map((doc) => (
            <ListItem
              key={doc.id}
              $active={doc.id === selectedDocument?.id}
              onClick={() => handleSelectDocument(doc)}
            >
              {/* Show the run name and fallback to ID */}
              {doc.name} ({doc.id.substring(0, 8)}...)
            </ListItem>
          ))}
      </Column>

      {/* === COLUMN 3: DOCUMENT DETAIL === */}
      <Column $flex={2}>
        <ColumnHeader>Fields</ColumnHeader>
        {selectedDocument ? (
          <DetailView>
            <pre>{JSON.stringify(selectedDocument, null, 2)}</pre>
          </DetailView>
        ) : (
          <EmptyState>Select a document to see its details</EmptyState>
        )}
      </Column>
    </Wrapper>
  );
};
