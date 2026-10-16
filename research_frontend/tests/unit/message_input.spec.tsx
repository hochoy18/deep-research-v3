/**
 * research_frontend/tests/unit/message_input.spec.tsx
 *
 * T086 — Vitest unit tests for the MessageInput component
 * (US-4 contract: 输入框 + 提交 + Enter 触发).
 *
 * Critical-path coverage (宪法 III):
 *   - @critical on every test in this file — counted toward ≥80% gate.
 *
 * What this file locks down:
 *   1. textarea renders empty by default
 *   2. typing updates the value (controlled component)
 *   3. clicking 发送 fires onSend ONCE with trimmed value
 *   4. pressing Enter without Shift submits (one onSend, value cleared)
 *   5. pressing Shift+Enter inserts a newline and does NOT submit
 *   6. submitting an empty/whitespace value is a no-op
 *   7. disabled prevents submission
 *
 * Notes:
 *   - Uses @testing-library/user-event to model real keyboard / pointer
 *     interactions rather than synthetic dispatchEvent.
 *   - onSend is observed via vi.fn() so spies can assert against calls.
 *   - Component is imported from @/components/message-input (path alias
 *     resolved by both tsconfig.json + vitest.config.ts).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { MessageInput } from "@/components/message-input";

describe("MessageInput (US-4 critical path)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("@critical renders an empty textarea and a submit button", () => {
    render(<MessageInput />);
    const textarea = screen.getByTestId("message-input-textarea");
    const submit = screen.getByTestId("message-input-submit");
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveValue("");
    expect(submit).toBeInTheDocument();
    expect(submit).toBeDisabled();
  });

  it("@critical updates the textarea value when the user types", async () => {
    const user = userEvent.setup();
    render(<MessageInput />);
    const textarea = screen.getByTestId(
      "message-input-textarea",
    ) as HTMLTextAreaElement;

    await user.type(textarea, "hello");

    expect(textarea).toHaveValue("hello");
  });

  it("@critical clicking 发送 fires onSend with trimmed value and clears input", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByTestId(
      "message-input-textarea",
    ) as HTMLTextAreaElement;

    await user.type(textarea, "  query  ");
    await user.click(screen.getByTestId("message-input-submit"));

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith("query");
    expect(textarea).toHaveValue("");
  });

  it("@critical Enter without Shift submits the trimmed value", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByTestId(
      "message-input-textarea",
    ) as HTMLTextAreaElement;

    await user.type(textarea, "ping");
    await user.keyboard("{Enter}");

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith("ping");
    expect(textarea).toHaveValue("");
  });

  it("@critical Shift+Enter inserts a newline and does not submit", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByTestId(
      "message-input-textarea",
    ) as HTMLTextAreaElement;

    await user.type(textarea, "first");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    await user.type(textarea, "second");

    expect(onSend).not.toHaveBeenCalled();
    expect(textarea.value).toContain("first");
    expect(textarea.value).toContain("second");
  });

  it("@critical submitting an empty/whitespace value is a no-op", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    await user.type(
      screen.getByTestId("message-input-textarea") as HTMLTextAreaElement,
      "   ",
    );
    await user.click(screen.getByTestId("message-input-submit"));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("@critical the disabled prop prevents submission", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} disabled />);
    const textarea = screen.getByTestId("message-input-textarea");
    const submit = screen.getByTestId("message-input-submit");

    expect(textarea).toBeDisabled();
    expect(submit).toBeDisabled();

    await user.click(submit);

    expect(onSend).not.toHaveBeenCalled();
  });
});
