document.documentElement.dataset.chapterScriptExampleLoaded = "true";

document.querySelectorAll("[data-chapter-script-demo]").forEach((demo) => {
  const progress = demo.querySelector("[data-demo-progress]");
  const progressValue = demo.querySelector("[data-demo-progress-value]");
  const progressOutput = demo.querySelector("[data-demo-progress-output]");
  const filter = demo.querySelector("[data-demo-filter]");
  const rows = Array.from(demo.querySelectorAll("[data-demo-row]"));
  const filterCount = demo.querySelector("[data-demo-filter-count]");
  const viewButtons = Array.from(demo.querySelectorAll("[data-demo-view]"));
  const viewPanels = Array.from(demo.querySelectorAll("[data-demo-view-panel]"));

  const updateProgress = () => {
    if (!progress || !progressValue || !progressOutput) {
      return;
    }

    const value = Number(progress.value);
    const status = value < 35 ? "low" : value > 70 ? "high" : "middle";
    progressValue.value = String(value);
    progressOutput.textContent = `Progress is ${value}%, so the status is in the ${status} range.`;
  };

  const updateFilter = () => {
    if (!filter || !filterCount) {
      return;
    }

    const query = filter.value.trim().toLowerCase();
    let visibleCount = 0;

    rows.forEach((row) => {
      const text = `${row.textContent || ""} ${row.dataset.demoKeywords || ""}`.toLowerCase();
      const visible = query === "" || text.includes(query);
      row.hidden = !visible;
      if (visible) {
        visibleCount += 1;
      }
    });

    filterCount.textContent = `Showing ${visibleCount} ${visibleCount === 1 ? "row" : "rows"}.`;
  };

  const showView = (name) => {
    viewPanels.forEach((panel) => {
      panel.hidden = panel.dataset.demoViewPanel !== name;
    });
    viewButtons.forEach((button) => {
      const active = button.dataset.demoView === name;
      button.classList.toggle("secondary", !active);
      button.setAttribute("aria-pressed", String(active));
    });
  };

  progress?.addEventListener("input", updateProgress);
  filter?.addEventListener("input", updateFilter);
  viewButtons.forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.demoView || "overview"));
  });

  updateProgress();
  updateFilter();
  showView("overview");
});
