document.documentElement.dataset.chapterScriptExampleLoaded = "true";

document.querySelectorAll("[data-chapter-script-output]").forEach((element) => {
  element.textContent = "Chapter-specific JavaScript loaded for this page.";
});
