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
  await expect(page.locator("#overview h2")).toHaveText("1. Overview");
  await expect(page.locator(".site-contents-tree a", { hasText: "Math Examples" })).toBeVisible();
  await expect(page.locator(".site-contents-tree a", { hasText: "3.1. Inline Math" })).toBeVisible();
  await expect(page.locator(".site-contents-tree a", { hasText: "Mermaid Diagrams" })).toBeVisible();
  await expect(page.locator(".chapter-nav-link.next")).toContainText("Chapter 2: Minimal Page");

  await expect(page.locator(".code-block-wrap .copy-code-button").first()).toBeVisible();
  await expect(page.locator("[data-python-runner-panel]")).toHaveCount(1);
  await expect(page.locator("[data-python-code]")).toHaveCount(1);
  await expect(page.locator("[data-python-run-button]")).toBeDisabled();
  await expect(page.locator(".CodeMirror")).toBeVisible();

  await expect.poll(() => page.evaluate(() => Boolean(window.Prism?.languages?.java))).toBe(true);
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

test("first and last generated chapters expose the correct edge navigation", async ({ page }) => {
  await page.goto("/chapters/01-introduction.html");

  await expect(page.locator(".chapter-nav-link.previous")).toHaveCount(0);
  await expect(page.locator(".chapter-nav-link.next")).toContainText("Chapter 2: Minimal Page");

  await page.goto("/chapters/03-reference.html");

  await expect(page.locator(".chapter-nav-link.previous")).toContainText("Chapter 2: Minimal Page");
  await expect(page.locator(".chapter-nav-link.next")).toHaveCount(0);
});

test("chapter-specific external links are appended to shared links", async ({ page }) => {
  await page.goto("/chapters/01-introduction.html");

  await expect(page.locator(".nav-section", { hasText: "External Links" })).toContainText("Prism.js");
  await expect(page.locator(".nav-section", { hasText: "External Links" })).not.toContainText("MDN HTML");

  await page.goto("/chapters/02-examples.html");

  const externalLinks = page.locator(".nav-section", { hasText: "External Links" });
  await expect(externalLinks).toContainText("Prism.js");
  await expect(externalLinks).toContainText("Chapter-specific links");
  await expect(externalLinks).toContainText("MDN HTML");
  await expect(externalLinks.locator('a[href="https://developer.mozilla.org/en-US/docs/Web/HTML"]')).toHaveAttribute(
    "target",
    "_blank"
  );
});

test("mobile layout remains readable without page-level horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/chapters/01-introduction.html");

  await expect(page.locator(".sidebar")).toBeVisible();
  await expect(page.locator(".content")).toBeVisible();

  const chapterNavColumns = await page.locator(".chapter-nav").evaluate((element) =>
    getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean)
  );
  expect(chapterNavColumns).toHaveLength(1);

  const overflow = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
});

test("print layout fits wide content to the printable page width", async ({ page }) => {
  await page.setViewportSize({ width: 794, height: 1123 });
  await page.emulateMedia({ media: "print" });
  await page.goto("/chapters/01-introduction.html");

  await expect(page.locator(".sidebar")).toBeHidden();
  await expect(page.locator(".copy-code-button").first()).toBeHidden();
  await expect(page.locator("[data-python-code]")).toBeHidden();
  await expect(page.locator("[data-python-print-code]")).toBeVisible();

  await expect(page.locator(".code-block").first()).toHaveCSS("white-space", "pre-wrap");
  await expect(page.locator(".code-block > code").first()).toHaveCSS("min-width", "0px");
  await expect(page.locator(".mermaid").first()).toHaveCSS("min-width", "0px");

  const overflow = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
});

test("static code copy button writes the code text", async ({ page }) => {
  await page.addInitScript(() => {
    window.__copiedText = "";
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (text) => {
          window.__copiedText = text;
        }
      }
    });
  });

  await page.goto("/chapters/01-introduction.html");

  const copyButton = page.locator(".code-block-wrap .copy-code-button").first();
  await copyButton.click();

  await expect(copyButton).toHaveText("Copied");
  await expect.poll(() => page.evaluate(() => window.__copiedText)).toContain("def summarize");
});

test("python runner reset and print snapshots stay in sync without loading Pyodide", async ({ page }) => {
  await page.goto("/chapters/01-introduction.html");

  const runner = page.locator("[data-python-runner-panel]");
  const editor = runner.locator(".CodeMirror");
  const textarea = runner.locator("[data-python-code]");
  const printCode = runner.locator("[data-python-print-code]");
  const printOutput = runner.locator("[data-python-print-output]");

  await expect(printCode).toContainText("linear_search_with_count");
  await expect(printOutput).toContainText('Press "Load Python Runtime" first');

  await editor.click();
  await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
  await page.keyboard.type('print("changed by smoke test")');

  await expect(textarea).toHaveValue('print("changed by smoke test")');
  await expect(printCode).toContainText('print("changed by smoke test")');

  await runner.locator("[data-python-reset-button]").click();

  await expect(textarea).toHaveValue(/linear_search_with_count/);
  await expect(printCode).toContainText("linear_search_with_count");
  await expect(runner.locator("[data-python-output]")).toContainText("Code text reset");
  await expect(printOutput).toContainText("Code text reset");
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
