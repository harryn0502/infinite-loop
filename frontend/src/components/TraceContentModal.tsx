import styled from "styled-components";
import React from "react";

interface TraceContentModalProps {
  title: string;
  content: string;
  onClose: () => void;
}

export const TraceContentModal: React.FC<TraceContentModalProps> = ({
  title,
  content,
  onClose,
}) => {
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <Backdrop onClick={handleBackdropClick}>
      <ModalBody>
        <Header>
          <Title>{title}</Title>
          <CloseButton onClick={onClose}>&times;</CloseButton>
        </Header>
        <Content>
          <ContentPre>{content}</ContentPre>
        </Content>
      </ModalBody>
    </Backdrop>
  );
};

// --- Styled Components ---

const Backdrop = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
`;

const ModalBody = styled.div`
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #e0e0e0;
`;

const Title = styled.h2`
  margin: 0;
  font-size: 16px;
  font-weight: 600;
`;

const CloseButton = styled.button`
  border: none;
  background: transparent;
  font-size: 28px;
  font-weight: 300;
  color: #777;
  cursor: pointer;
  padding: 0;
  line-height: 1;

  &:hover {
    color: #000;
  }
`;

const Content = styled.div`
  padding: 16px 24px;
  overflow-y: auto;
`;

const ContentPre = styled.pre`
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 12px;
  font-size: 13px;
  font-family: "Menlo", "Courier New", monospace;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
`;
