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

  it("renders without body snippet (header-only shape)", () => {
    const { container } = render(CallCard, { props: { title: "X" } });
    expect(container.querySelector(".call-head")).toBeInTheDocument();
    expect(container.querySelector(".call-body")).toBeNull();
  });

  it("renders the title as an <a> when titleHref is provided", () => {
    const { getByRole } = render(CallCard, {
      props: { title: "Cleanup", titleHref: "/volunteer-calls/abc" },
    });
    const link = getByRole("link", { name: "Cleanup" });
    expect(link.getAttribute("href")).toBe("/volunteer-calls/abc");
  });

  it("renders the title as a <span> when titleHref is omitted", () => {
    const { queryByRole, getByText } = render(CallCard, {
      props: { title: "Cleanup" },
    });
    expect(queryByRole("link", { name: "Cleanup" })).toBeNull();
    expect(getByText("Cleanup").tagName.toLowerCase()).toBe("span");
  });
});
