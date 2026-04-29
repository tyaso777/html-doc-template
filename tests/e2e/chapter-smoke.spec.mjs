import { expect, test } from "@playwright/test";

const consoleErrorsByPage = new WeakMap();

test.beforeEach(async ({ page }) => {
  const consoleErrors = [];
  consoleErrorsByPage.set(page, consoleErrors);
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(error.message);
  });
});

test.afterEach(async ({ page }) => {
  expect(consoleErrorsByPage.get(page) || []).toEqual([]);
});

test("chapter page initializes document enhancements", async ({ page }) => {
  await page.goto("/chapters/01-introduction.html");

  await expect(page).toHaveTitle("Chapter 1: Introduction");
  await expect(page.locator("h1")).toHaveText("Chapter 1: Introduction");
  await expect(page.locator(".site-contents-tree a", { hasText: "Math Examples" })).toBeVisible();
  await expect(page.locator(".site-contents-tree a", { hasText: "Mermaid Diagrams" })).toBeVisible();
  await expect(page.locator(".chapter-nav-link.next")).toContainText("Chapter 2: Minimal Page");

  await expect(page.locator(".code-block-wrap .copy-code-button").first()).toBeVisible();
  await expect(page.locator("[data-python-runner-panel]")).toHaveCount(1);
  await expect(page.locator("[data-python-code]")).toHaveCount(1);
  await expect(page.locator("[data-python-run-button]")).toBeDisabled();
  await expect(page.locator(".CodeMirror")).toBeVisible();

  await expect(page.locator("mjx-container").first()).toBeVisible();
  await expect(page.locator(".mermaid svg").first()).toBeVisible();
});

test("generated chapter navigation works", async ({ page }) => {
  await page.goto("/chapters/02-examples.html");

  await expect(page.locator("h1")).toHaveText("Chapter 2: Minimal Page");
  await expect(page.locator(".chapter-nav-link.previous")).toContainText("Chapter 1: Introduction");
  await expect(page.locator(".chapter-nav-link.next")).toContainText("Chapter 3: Reference Page");

  await page.locator(".chapter-nav-link.next").click();
  await expect(page).toHaveURL(/\/chapters\/03-reference\.html$/);
  await expect(page.locator("h1")).toHaveText("Chapter 3: Reference Page");
});

test("python runner can load Pyodide and execute code @pyodide", async ({ page }) => {
  test.skip(process.env.PYODIDE_SMOKE !== "1", "Set PYODIDE_SMOKE=1 to run the slow CDN-backed Pyodide smoke test.");
  test.setTimeout(180_000);

  await page.goto("/chapters/01-introduction.html");
  await page.locator("[data-python-load-button]").click();
  await expect(page.locator("[data-python-output]")).toContainText("Python runtime loaded", {
    timeout: 120_000
  });

  await page.locator("[data-python-run-button]").click();
  await expect(page.locator("[data-python-output]")).toContainText("Interpretation:", {
    timeout: 60_000
  });
});
