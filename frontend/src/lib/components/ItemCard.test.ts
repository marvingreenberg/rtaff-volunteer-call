import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import ItemCard from "./ItemCard.svelte";

function textSnippet(text: string) {
  return createRawSnippet(() => ({
    render: () => `<span>${text}</span>`,
  }));
}

describe("ItemCard", () => {
  it("renders children content", () => {
    render(ItemCard, { props: { children: textSnippet("Hello") } });
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders as a link when href is provided", () => {
    render(ItemCard, {
      props: { href: "/test", children: textSnippet("Link card") },
    });
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/test");
  });

  it("renders as a div when no href", () => {
    const { container } = render(ItemCard, {
      props: { children: textSnippet("Div card") },
    });
    expect(container.querySelector("a")).toBeNull();
    expect(screen.getByText("Div card")).toBeInTheDocument();
  });

  it("applies checked class when checked", () => {
    const { container } = render(ItemCard, {
      props: { checked: true, children: textSnippet("Checked") },
    });
    expect(container.querySelector(".checked")).not.toBeNull();
  });

  it("applies accent border when accentColor provided", () => {
    const { container } = render(ItemCard, {
      props: { accentColor: "#ff0000", children: textSnippet("Accented") },
    });
    expect(container.querySelector(".accented")).not.toBeNull();
  });
});
