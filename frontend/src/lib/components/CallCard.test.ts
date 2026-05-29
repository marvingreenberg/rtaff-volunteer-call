import { describe, expect, it } from "vitest";
import { render } from "@testing-library/svelte";
import CallCard from "./CallCard.svelte";
import { createRawSnippet } from "svelte";

const snippet = (html: string) =>
  createRawSnippet(() => ({ render: () => html }));

describe("CallCard", () => {
  it("renders title and meta in the head", () => {
    const { getByText } = render(CallCard, {
      props: {
        title: "Coastal cleanup",
        meta: "5 tasks",
        body: snippet("<p>body</p>"),
      },
    });
    expect(getByText("Coastal cleanup")).toBeInTheDocument();
    expect(getByText("5 tasks")).toBeInTheDocument();
  });

  it("renders body snippet content", () => {
    const { container } = render(CallCard, {
      props: { title: "X", body: snippet('<p data-testid="body">hello</p>') },
    });
    expect(container.querySelector('[data-testid="body"]')).toHaveTextContent(
      "hello",
    );
  });
});
