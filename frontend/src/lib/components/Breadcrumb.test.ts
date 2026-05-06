import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import Breadcrumb from "./Breadcrumb.svelte";

describe("Breadcrumb", () => {
  it("renders all crumb labels", () => {
    render(Breadcrumb, {
      props: {
        crumbs: [
          { label: "Home", href: "/" },
          { label: "Projects", href: "/projects" },
          { label: "Detail" },
        ],
      },
    });
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Projects")).toBeInTheDocument();
    expect(screen.getByText("Detail")).toBeInTheDocument();
  });

  it("renders links for non-last crumbs with href", () => {
    render(Breadcrumb, {
      props: {
        crumbs: [
          { label: "Home", href: "/" },
          { label: "Projects", href: "/projects" },
          { label: "Detail" },
        ],
      },
    });
    const homeLink = screen.getByText("Home").closest("a");
    expect(homeLink).toHaveAttribute("href", "/");
    const projLink = screen.getByText("Projects").closest("a");
    expect(projLink).toHaveAttribute("href", "/projects");
  });

  it("renders last crumb as span with aria-current", () => {
    render(Breadcrumb, {
      props: {
        crumbs: [{ label: "Home", href: "/" }, { label: "Current Page" }],
      },
    });
    const current = screen.getByText("Current Page");
    expect(current.tagName).toBe("SPAN");
    expect(current).toHaveAttribute("aria-current", "page");
  });

  it("has accessible navigation landmark", () => {
    render(Breadcrumb, {
      props: {
        crumbs: [{ label: "Home", href: "/" }, { label: "Page" }],
      },
    });
    expect(
      screen.getByRole("navigation", { name: "Breadcrumb" }),
    ).toBeInTheDocument();
  });

  it("renders single crumb as current page", () => {
    render(Breadcrumb, {
      props: { crumbs: [{ label: "Home" }] },
    });
    expect(screen.getByText("Home")).toHaveAttribute("aria-current", "page");
  });
});
