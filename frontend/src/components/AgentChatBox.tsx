import React, { useState, useRef, useEffect } from "react";
import styled from "styled-components";
// Import the chart component
import { AgentChart } from "./AgentChart";

// --- 1. TYPES ---

// Represents a message in the chat UI
interface ChatMessage {
  type: "human" | "ai";
  content: string;
  reasoning?: string | null; // For the agent's "thoughts"
}

// Represents the raw serialized message from the backend (via messages_to_dict)
interface SerializedMessage {
  type: "human" | "ai" | "system" | "tool";
  data: {
    content: string;
    additional_kwargs?: {
      reasoning?: string;
      [key: string]: unknown; // Use Record<string, unknown> instead of any
    };
    [key: string]: unknown; // Use Record<string, unknown> instead of any
  };
}

// The state returned by the /query_agent endpoint
interface AgentState {
  messages: SerializedMessage[];
  [key: string]: unknown; // Other state keys
}

/**
 * Expected shape of the agent's chart JSON.
 */
interface AgentChartSpec {
  chartType: string;
  xField: string;
  yField: string;
  data: Record<string, unknown>[];
}

// --- 2. HELPER FUNCTION ---

/**
 * Tries to parse an Agent Chart Spec from a string.
 * It looks for a ```json ... ``` code block or raw JSON.
 * Returns the parsed spec object if valid, otherwise null.
 */
const extractChartSpec = (content: string): AgentChartSpec | null => {
  // Regex to find a JSON code block
  const jsonRegex = /```json\s*([\s\S]*?)\s*```/;
  const match = content.match(jsonRegex);

  let jsonString: string | null = null;

  if (match && match[1]) {
    // Case 1: Found a ```json code block
    jsonString = match[1];
  } else if (content.trim().startsWith("{") && content.trim().endsWith("}")) {
    // Case 2: The entire content is just the JSON object
    jsonString = content.trim();
  } else {
    // Not a chart spec
    return null;
  }

  try {
    const json = JSON.parse(jsonString);
    // Check for the specific keys we need to render a chart
    if (json && json.chartType && json.xField && json.yField && Array.isArray(json.data)) {
      return json as AgentChartSpec;
    }
    return null;
  } catch {
    return null; // Not valid JSON
  }
};

// --- 3. COMPONENT ---

export const AgentChatBox = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentInput, setCurrentInput] = useState("");
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentInput.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      type: "human",
      content: currentInput,
    };

    setMessages((prev) => [...prev, userMessage]);
    setCurrentInput("");
    setIsLoading(true);

    const payload = {
      user_message: currentInput,
      prev_state: agentState,
    };

    try {
      const response = await fetch("http://localhost:8000/query_agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || `API Error: ${response.statusText}`);
      }

      const finalState: AgentState = await response.json();
      setAgentState(finalState);
      const lastMessage = finalState.messages[finalState.messages.length - 1];

      if (lastMessage && lastMessage.type === "ai") {
        const aiMessage: ChatMessage = {
          type: "ai",
          content: lastMessage.data.content,
          reasoning: lastMessage.data.additional_kwargs?.reasoning,
        };
        setMessages((prev) => [...prev, aiMessage]);
      } else {
        console.warn("Last message was not from AI:", lastMessage);
      }
    } catch (error) {
      console.error("Failed to query agent:", error);

      // 💡 FIX: Safely assert/narrow the type of the error object
      let errorMessageContent = "An unknown error occurred.";

      if (error instanceof Error) {
        errorMessageContent = `Sorry, I encountered an error: ${error.message}`;
      } else if (typeof error === "string") {
        errorMessageContent = `Sorry, I encountered an error: ${error}`;
      }

      const errorMessage: ChatMessage = {
        type: "ai",
        content: errorMessageContent,
        reasoning: "The API call failed or returned an invalid response.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ChatWrapper>
      <ColumnHeader>Agent Chat</ColumnHeader>
      <MessageList ref={messageListRef}>
        {messages.map((msg, index) => {
          let chartSpec: AgentChartSpec | null = null;
          if (msg.type === "ai") {
            chartSpec = extractChartSpec(msg.content);
          }

          return (
            <MessageBubble key={index} $type={msg.type}>
              {chartSpec ? (
                <AgentChart spec={chartSpec} />
              ) : (
                <MessageContent>{msg.content}</MessageContent>
              )}

              {msg.type === "ai" && msg.reasoning && (
                <ReasoningBox>
                  <ReasoningHeader>🧠 Reasoning</ReasoningHeader>
                  <ReasoningContent>{msg.reasoning}</ReasoningContent>
                </ReasoningBox>
              )}
            </MessageBubble>
          );
        })}
        {isLoading && (
          <MessageBubble $type="ai">
            <TypingIndicator>
              <span></span>
              <span></span>
              <span></span>
            </TypingIndicator>
          </MessageBubble>
        )}
      </MessageList>
      <ChatInputForm onSubmit={handleSubmit}>
        <Input
          type="text"
          placeholder="Ask the agent a question..."
          value={currentInput}
          onChange={(e) => setCurrentInput(e.target.value)}
          disabled={isLoading}
        />
        <Button type="submit" disabled={isLoading}>
          Send
        </Button>
      </ChatInputForm>
    </ChatWrapper>
  );
};

// --- 4. STYLED COMPONENTS ---

const ColumnHeader = styled.div`
  padding: 12px 16px;
  font-weight: 600;
  font-size: 16px;
  border-bottom: 1px solid #e0e0e0;
  background-color: #f9f9f9;
  flex-shrink: 0;
`;

const ChatWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
`;

const MessageList = styled.div`
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const MessageBubble = styled.div<{ $type: "human" | "ai" }>`
  /* --- CRITICAL VISUAL FIX --- */
  padding: 10px 14px 15px; /* Increased bottom padding to prevent text leakage */
  position: relative;
  overflow: hidden;
  /* --- END CRITICAL FIX --- */

  border-radius: 18px;
  max-width: 80%;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.5;

  ${(props) =>
    props.$type === "human"
      ? `
        background-color: #0d47a1;
        color: white;
        align-self: flex-end;
        border-bottom-right-radius: 4px;
      `
      : `
        background-color: #f1f1f1;
        color: #222;
        align-self: flex-start;
        border-bottom-left-radius: 4px;
      `}
`;

const MessageContent = styled.div`
  white-space: pre-wrap;

  /* --- Secondary Visual Fix --- */
  overflow: hidden;
  padding-bottom: 2px;
  /* --- End Secondary Fix --- */
`;

const ReasoningBox = styled.div`
  border-top: 1px solid #d0d0d0;
  margin-top: 10px;
  padding-top: 10px;
  background: #f1f1f1;
`;

const ReasoningHeader = styled.div`
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 4px;
`;

const ReasoningContent = styled.pre`
  font-family: "Menlo", "Courier New", monospace;
  font-size: 13px;
  color: #444;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  padding: 0;
  background: transparent;
`;

const ChatInputForm = styled.form`
  display: flex;
  padding: 12px;
  border-top: 1px solid #e0e0e0;
  background-color: #f9f9f9;
`;

const Input = styled.input`
  flex-grow: 1;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 20px;
  margin-right: 8px;

  &:disabled {
    background-color: #f5f5f5;
  }
`;

const Button = styled.button`
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 20px;
  background-color: #0d47a1;
  color: white;
  cursor: pointer;

  &:hover {
    background-color: #1565c0;
  }

  &:disabled {
    background-color: #90a4ae;
    cursor: not-allowed;
  }
`;

const TypingIndicator = styled.div`
  display: flex;
  align-items: center;
  padding: 8px 0;
  span {
    height: 8px;
    width: 8px;
    border-radius: 50%;
    background-color: #999;
    margin: 0 2px;
    animation: bounce 1.4s infinite both;
  }
  span:nth-child(1) {
    animation-delay: -0.32s;
  }
  span:nth-child(2) {
    animation-delay: -0.16s;
  }
  @keyframes bounce {
    0%,
    80%,
    100% {
      transform: scale(0);
    }
    40% {
      transform: scale(1);
    }
  }
`;
