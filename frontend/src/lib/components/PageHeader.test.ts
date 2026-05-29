import { describe, expect, it } from "vitest";
import { render } from "@testing-library/svelte";
import PageHeader from "./PageHeader.svelte";

describe("PageHeader", () => {
  it("renders the title", () => {
    const { getByRole } = render(PageHeader, {
      props: { title: "Volunteering" },
    });
    expect(getByRole("heading", { level: 1 })).toHaveTextContent(
      "Volunteering",
    );
  });

  it("omits the meta region when no meta snippet is passed", () => {
    const { container } = render(PageHeader, { props: { title: "Hi" } });
    expect(container.querySelector(".page-header-meta")).toBeNull();
  });
});
