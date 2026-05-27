import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TruncatedText } from "@/components/util/TruncatedText";

describe("TruncatedText", () => {
  it("renders short text without truncation", () => {
    render(<TruncatedText text="Short text" />);
    expect(screen.getByText("Short text")).toBeInTheDocument();
  });

  it("truncates long text with default maxLength", () => {
    const longText = "This is a very long text that should be truncated";
    render(<TruncatedText text={longText} />);
    expect(screen.getByText("This is a very long text ...")).toBeInTheDocument();
  });

  it("truncates long text with custom maxLength", () => {
    const text = "Hello world";
    render(<TruncatedText text={text} maxLength={5} />);
    expect(screen.getByText("Hello...")).toBeInTheDocument();
  });

  it("sets title attribute for hover tooltip", () => {
    const text = "Full text for tooltip";
    render(<TruncatedText text={text} />);
    expect(screen.getByText(text)).toHaveAttribute("title", text);
  });

  it("applies custom className", () => {
    render(<TruncatedText text="Test" className="custom-class" />);
    expect(screen.getByText("Test")).toHaveClass("custom-class");
  });

  it("renders with default styling classes", () => {
    render(<TruncatedText text="Test" />);
    const element = screen.getByText("Test");
    expect(element).toHaveClass("whitespace-nowrap");
    expect(element).toHaveClass("overflow-hidden");
    expect(element).toHaveClass("text-ellipsis");
  });
});
