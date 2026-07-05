    const DEFAULT_CODE = `from time import perf_counter


def linear_search_with_count(values: list[int], target: int) -> tuple[int, int]:
    """Finds the target by scanning values and counts comparisons.

    Args:
        values: Sorted integer values.
        target: Value to find.

    Returns:
        A pair of the target index and the number of comparisons.
    """
    comparisons = 0

    for index, value in enumerate(values):
        comparisons += 1
        if value == target:
            return index, comparisons

    return -1, comparisons


def binary_search_with_count(values: list[int], target: int) -> tuple[int, int]:
    """Finds the target using binary search and counts comparisons.

    Args:
        values: Sorted integer values.
        target: Value to find.

    Returns:
        A pair of the target index and the number of comparisons.
    """
    left = 0
    right = len(values) - 1
    comparisons = 0

    while left <= right:
        middle = (left + right) // 2
        comparisons += 1

        if values[middle] == target:
            return middle, comparisons

        if values[middle] < target:
            left = middle + 1
        else:
            right = middle - 1

    return -1, comparisons


def measure_once(n: int, repeats: int) -> tuple[int, int, float, float]:
    """Measures comparison counts and average execution times.

    Args:
        n: Number of elements.
        repeats: Number of repeated searches.

    Returns:
        Linear-search comparisons, binary-search comparisons, average linear-search
        time, and average binary-search time.
    """
    values = list(range(n))
    target = n - 1

    _, linear_comparisons = linear_search_with_count(values, target)
    _, binary_comparisons = binary_search_with_count(values, target)

    start = perf_counter()
    for _ in range(repeats):
        linear_search_with_count(values, target)
    linear_ms = (perf_counter() - start) * 1000 / repeats

    start = perf_counter()
    for _ in range(repeats):
        binary_search_with_count(values, target)
    binary_ms = (perf_counter() - start) * 1000 / repeats

    return linear_comparisons, binary_comparisons, linear_ms, binary_ms


def main() -> None:
    """Runs a simple growth-rate experiment."""
    sizes = [1_000, 10_000, 100_000, 500_000, 1_000_000]
    repeats_by_size = {
        1_000: 200,
        10_000: 100,
        100_000: 20,
        500_000: 5,
        1_000_000: 3,
    }

    print("n          linear_cmp   binary_cmp   cmp_ratio   linear_ms   binary_ms")
    print("-" * 78)

    for n in sizes:
        linear_cmp, binary_cmp, linear_ms, binary_ms = measure_once(n, repeats_by_size[n])
        ratio = linear_cmp / binary_cmp if binary_cmp > 0 else float("inf")
        print(
            f"{n:>9}  "
            f"{linear_cmp:>10}  "
            f"{binary_cmp:>10}  "
            f"{ratio:>9.1f}x  "
            f"{linear_ms:>9.4f}  "
            f"{binary_ms:>9.4f}"
        )

    print()
    print("Interpretation:")
    print("- Comparison counts are the cleanest signal here.")
    print("- Linear search comparisons grow almost directly with n.")
    print("- Binary search comparisons grow slowly because the search range is halved.")
    print("- Timing numbers are useful but noisier than comparison counts.")


main()
`;

    /*
      Pyodide CDN security note:
      Pyodide is loaded inside a classic Web Worker only when the user presses
      Load Python Runtime. This keeps the page responsive and prevents Python
      code from directly manipulating the DOM. However, the Worker loads
      pyodide.js with importScripts(), and importScripts() does not support
      normal script-tag SRI. If the pinned CDN asset or its dependent Pyodide
      files were compromised upstream, the browser would not reject them via
      integrity="...". For documents that require strict supply-chain
      control, host a reviewed Pyodide build locally and change this config
      to point to those local assets.
    */
    const PYODIDE_WORKER_CONFIG = {
      scriptUrl: "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.js",
      indexUrl: "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/"
    };

    function normalizePyodideAssetUrl(value, label) {
      if (typeof value !== "string" || value.trim() === "") {
        throw new Error(`Invalid Pyodide ${label} URL.`);
      }

      const url = new URL(value, window.location.href);
      if (url.protocol !== "https:" && url.origin !== window.location.origin) {
        throw new Error(`Pyodide ${label} URL must be HTTPS or same-origin.`);
      }

      return url.href;
    }

    const LAYOUT_MODE_STORAGE_KEY = "technicalDocLayoutMode";

    function defaultLayoutMode() {
      return window.technicalDocDefaultLayoutMode === "wide" ? "wide" : "standard";
    }

    function storedLayoutMode() {
      try {
        const savedMode = window.localStorage.getItem(LAYOUT_MODE_STORAGE_KEY);
        return savedMode === "wide" || savedMode === "standard" ? savedMode : defaultLayoutMode();
      } catch (error) {
        return defaultLayoutMode();
      }
    }

    function setLayoutMode(mode) {
      const isWide = mode === "wide";
      document.documentElement.classList.toggle("layout-wide", isWide);
      document.body.classList.toggle("layout-wide", isWide);

      try {
        window.localStorage.setItem(LAYOUT_MODE_STORAGE_KEY, mode);
      } catch (error) {
        // Ignore storage errors so the control still works for the current page.
      }
    }

    function initializeLayoutModeControl() {
      const controls = Array.from(document.querySelectorAll('input[name="layout-mode"]'));
      if (controls.length === 0) {
        return;
      }

      const mode = storedLayoutMode();
      setLayoutMode(mode);

      for (const control of controls) {
        control.checked = control.value === mode;
        control.addEventListener("change", () => {
          if (control.checked) {
            setLayoutMode(control.value);
          }
        });
      }
    }

    function initializeMermaid() {
      if (window.mermaid) {
        window.mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "default",
          flowchart: {
            htmlLabels: false,
            curve: "basis"
          }
        });
        window.mermaid.run({ querySelector: ".mermaid" });
      }
    }

    function initializeVegaLite() {
      if (!window.vegaEmbed) {
        return;
      }

      for (const target of document.querySelectorAll("[data-vega-lite]")) {
        const specId = target.dataset.vegaLiteSpec;
        const specElement = specId ? document.getElementById(specId) : null;

        if (!specElement) {
          target.textContent = "Vega-Lite spec was not found.";
          continue;
        }

        let spec;

        try {
          const specText = specElement.content
            ? specElement.content.textContent
            : specElement.textContent;
          spec = JSON.parse(specText);
        } catch (error) {
          target.textContent = `Vega-Lite spec error: ${error.message}`;
          continue;
        }

        window.vegaEmbed(target, spec, {
          actions: false,
          renderer: "svg"
        }).catch((error) => {
          target.textContent = `Vega-Lite render error: ${error.message || error}`;
        });
      }
    }

    function initializePythonRunner(panel) {
      const codeArea = panel.querySelector("[data-python-code]");
      const output = panel.querySelector("[data-python-output]");
      const loadButton = panel.querySelector("[data-python-load-button]");
      const runButton = panel.querySelector("[data-python-run-button]");
      const resetButton = panel.querySelector("[data-python-reset-button]");
      const restartRuntimeButton = panel.querySelector("[data-python-restart-button]");
      const copyButton = panel.querySelector("[data-python-copy-button]");
      const printCode = panel.querySelector("[data-python-print-code]");
      const printOutput = panel.querySelector("[data-python-print-output]");

      if (!codeArea || !output || !loadButton || !runButton || !resetButton || !restartRuntimeButton) {
        return;
      }

      let pyodideWorker = null;
      let pyodideWorkerUrl = null;
      let pyodideReady = false;
      let pyodideRequestId = 0;
      let pythonEditor = null;
      const pyodidePendingRequests = new Map();
      const initialPythonCode = codeArea.dataset.initialCodeBase64
        ? decodeBase64Utf8(codeArea.dataset.initialCodeBase64)
        : codeArea.dataset.initialCode
          ? codeArea.dataset.initialCode
          : codeArea.value.trim()
            ? codeArea.value
            : DEFAULT_CODE;

      function getPythonCode() {
        if (pythonEditor) {
          return pythonEditor.getValue();
        }

        return codeArea.value;
      }

      function setPythonCode(value) {
        if (pythonEditor) {
          pythonEditor.setValue(value);
        }

        codeArea.value = value;
      }

      function syncPrintRunnerSnapshot() {
        if (printCode) {
          printCode.textContent = getPythonCode() || "(empty code)";
        }

        if (printOutput) {
          printOutput.textContent = output.textContent || "(no output)";
        }
      }

      function setOutput(text) {
        output.textContent = text;
        output.dataset.hasStreamOutput = text ? "true" : "false";
        syncPrintRunnerSnapshot();
      }

      function clearOutput() {
        output.textContent = "";
        output.dataset.hasStreamOutput = "false";
        syncPrintRunnerSnapshot();
      }

      function appendOutput(text) {
        output.textContent += text;
        output.dataset.hasStreamOutput = "true";
        output.scrollTop = output.scrollHeight;
        syncPrintRunnerSnapshot();
      }

      function hasOutputContent() {
        return output.dataset.hasStreamOutput === "true" && output.textContent.length > 0;
      }

      function setOutputBusy(isBusy) {
        output.setAttribute("aria-busy", String(isBusy));
      }

      function setStatus(text) {
        panel.dataset.pythonRuntimeStatus = text;
      }

      function createPyodideWorker() {
        if (pyodideWorker) {
          return pyodideWorker;
        }

        const pyodideScriptUrl = normalizePyodideAssetUrl(PYODIDE_WORKER_CONFIG.scriptUrl, "script");
        const pyodideIndexUrl = normalizePyodideAssetUrl(PYODIDE_WORKER_CONFIG.indexUrl, "index");

        const workerSource = `
        const pyodideScriptUrl = ${JSON.stringify(pyodideScriptUrl)};
        const pyodideIndexUrl = ${JSON.stringify(pyodideIndexUrl)};

        importScripts(pyodideScriptUrl);
        let pyodideReadyPromise = null;
        let streamsConfigured = false;
        let currentRunId = null;

        async function getPyodideRuntime() {
          if (!pyodideReadyPromise) {
            pyodideReadyPromise = loadPyodide({
              indexURL: pyodideIndexUrl
            });
          }

          const pyodide = await pyodideReadyPromise;

          if (!streamsConfigured) {
            // Pyodide's batched stdout/stderr callback may provide line text without a trailing newline.
            pyodide.setStdout({
              batched: (text) => {
                if (currentRunId !== null) {
                  self.postMessage({
                    id: currentRunId,
                    type: "stdout",
                    text: text.endsWith("\\n") ? text : text + "\\n"
                  });
                }
              }
            });

            pyodide.setStderr({
              batched: (text) => {
                if (currentRunId !== null) {
                  self.postMessage({
                    id: currentRunId,
                    type: "stderr",
                    text: text.endsWith("\\n") ? text : text + "\\n"
                  });
                }
              }
            });

            streamsConfigured = true;
          }

          return pyodide;
        }

        function wrapUserCode(code) {
          // Catch BaseException in the Python wrapper so SystemExit-like errors are printed.
          // stdout/stderr are streamed by Pyodide setStdout/setStderr, not captured in StringIO.
          const indentedCode = code
            .split("\\n")
            .map((line) => "    " + line)
            .join("\\n");

          return \`
import traceback

try:
\${indentedCode}
except BaseException:
    traceback.print_exc()
\`;
        }

        self.addEventListener("message", async (event) => {
          const { id, type, code } = event.data;

          try {
            const pyodide = await getPyodideRuntime();

            if (type === "load") {
              self.postMessage({
                id,
                type: "loaded",
                result: "Python runtime loaded in worker."
              });
              return;
            }

            if (type === "run") {
              const wrappedCode = wrapUserCode(code || "");
              currentRunId = id;

              try {
                const result = await pyodide.runPythonAsync(wrappedCode);
                const resultText = result === undefined || result === null ? "" : String(result);

                self.postMessage({
                  id,
                  type: "result",
                  result: resultText
                });
              } finally {
                currentRunId = null;
              }

              return;
            }

            self.postMessage({
              id,
              type: "error",
              error: "Unknown worker message type: " + type
            });
          } catch (error) {
            self.postMessage({
              id,
              type: "error",
              error: String(error && error.stack ? error.stack : error)
            });
          }
        });
        `;

        const blob = new Blob([workerSource], { type: "text/javascript" });
        pyodideWorkerUrl = URL.createObjectURL(blob);
        pyodideWorker = new Worker(pyodideWorkerUrl);

        pyodideWorker.addEventListener("message", (event) => {
          const { id, type, result, error, text } = event.data;
          const request = pyodidePendingRequests.get(id);

          if (!request) {
            return;
          }

          if (type === "stdout" || type === "stderr") {
            if (request.onStream) {
              request.onStream(text || "");
            }
            return;
          }

          pyodidePendingRequests.delete(id);

          if (type === "error") {
            request.reject(new Error(error || "Unknown worker error."));
            return;
          }

          request.resolve(result);
        });

        pyodideWorker.addEventListener("error", (event) => {
          const details = [
            event.message || "Worker error.",
            event.filename ? `file: ${event.filename}` : "",
            event.lineno ? `line: ${event.lineno}` : "",
            event.colno ? `column: ${event.colno}` : ""
          ]
            .filter(Boolean)
            .join(" ");

          for (const request of pyodidePendingRequests.values()) {
            request.reject(new Error(details));
          }
          pyodidePendingRequests.clear();
        });

        return pyodideWorker;
      }

      function sendPyodideWorkerMessage(type, payload = {}, handlers = {}) {
        const worker = createPyodideWorker();
        const id = ++pyodideRequestId;

        return new Promise((resolve, reject) => {
          pyodidePendingRequests.set(id, {
            resolve,
            reject,
            onStream: handlers.onStream || null
          });

          worker.postMessage({
            id,
            type,
            ...payload
          });
        });
      }

      async function loadPythonRuntime() {
        if (pyodideReady) {
          setStatus("Python runtime: already loaded in worker.");
          runButton.disabled = false;
          restartRuntimeButton.disabled = false;
          return;
        }

        loadButton.disabled = true;
        setOutputBusy(true);
        setStatus("Python runtime: loading in worker...");
        setOutput("Loading Pyodide in a classic Web Worker. The page should remain responsive.");

        try {
          await sendPyodideWorkerMessage("load");
          pyodideReady = true;
          setStatus("Python runtime: loaded in worker.");
          setOutput("Python runtime loaded in worker. Press Run Python.");
          setOutputBusy(false);
          runButton.disabled = false;
          restartRuntimeButton.disabled = false;
        } catch (error) {
          loadButton.disabled = false;
          setStatus("Python runtime: failed to load in worker.");
          setOutput(String(error));
          setOutputBusy(false);
        }
      }

      async function runPythonCode() {
        const code = getPythonCode();

        if (!pyodideReady) {
          setOutput("Python runtime is not loaded.");
          return;
        }

        runButton.disabled = true;
        setOutputBusy(true);
        clearOutput();
        setStatus("Python runtime: running code in worker.");

        try {
          const result = await sendPyodideWorkerMessage(
            "run",
            { code },
            {
              onStream: (text) => {
                appendOutput(text);
              }
            }
          );

          if (result) {
            appendOutput(result);
          }

          if (!hasOutputContent()) {
            setOutput("(no output)");
          }

          setStatus("Python runtime: run completed.");
        } catch (error) {
          appendOutput(String(error));
          setStatus("Python runtime: run failed.");
        } finally {
          runButton.disabled = false;
          setOutputBusy(false);
        }
      }

      function resetCode() {
        setPythonCode(initialPythonCode);
        syncPrintRunnerSnapshot();
        setOutputBusy(false);
        setOutput("Code text reset. Python runtime state was not changed.");
      }

      function restartPythonRuntime() {
        for (const request of pyodidePendingRequests.values()) {
          request.reject(new Error("Python runtime was restarted."));
        }
        pyodidePendingRequests.clear();

        if (pyodideWorker) {
          pyodideWorker.terminate();
          pyodideWorker = null;
        }

        if (pyodideWorkerUrl) {
          URL.revokeObjectURL(pyodideWorkerUrl);
          pyodideWorkerUrl = null;
        }

        pyodideReady = false;
        loadButton.disabled = false;
        runButton.disabled = true;
        restartRuntimeButton.disabled = true;

        setOutputBusy(false);
        setStatus("Python runtime: restarted. Load it again before running code.");
        setOutput("Python runtime was restarted. Press Load Python Runtime.");
      }

      function initializePythonEditor() {
        if (!window.CodeMirror) {
          return;
        }

        pythonEditor = window.CodeMirror.fromTextArea(codeArea, {
          mode: "python",
          lineNumbers: true,
          indentUnit: 4,
          tabSize: 4,
          indentWithTabs: false,
          lineWrapping: false,
          viewportMargin: Infinity,
          extraKeys: {
            Tab: (editor) => {
              if (editor.somethingSelected()) {
                editor.indentSelection("add");
                return;
              }

              editor.replaceSelection("    ", "end");
            }
          }
        });

        pythonEditor.on("change", () => {
          pythonEditor.save();
          syncPrintRunnerSnapshot();
        });
      }

      function initializePrintSnapshotSync() {
        syncPrintRunnerSnapshot();
        codeArea.addEventListener("input", syncPrintRunnerSnapshot);
      }

      function initializePythonCodeCopyButton() {
        if (!copyButton) {
          return;
        }

        copyButton.addEventListener("click", async () => {
          const originalText = copyButton.textContent;
          copyButton.disabled = true;

          try {
            await copyTextToClipboard(getPythonCode());
            copyButton.textContent = "Copied";
          } catch (error) {
            copyButton.textContent = "Error";
          } finally {
            window.setTimeout(() => {
              copyButton.textContent = originalText;
              copyButton.disabled = false;
            }, 1400);
          }
        });
      }

      setPythonCode(initialPythonCode);
      initializePythonEditor();
      setPythonCode(initialPythonCode);
      initializePrintSnapshotSync();
      initializePythonCodeCopyButton();

      loadButton.addEventListener("click", loadPythonRuntime);
      runButton.addEventListener("click", runPythonCode);
      resetButton.addEventListener("click", resetCode);
      restartRuntimeButton.addEventListener("click", restartPythonRuntime);
    }

    function initializePrintSnapshotSync(runners) {
      window.addEventListener("beforeprint", syncPrintRunnerSnapshot);

      if (window.matchMedia) {
        const printMediaQuery = window.matchMedia("print");
        printMediaQuery.addEventListener("change", (event) => {
          if (event.matches) {
            syncPrintRunnerSnapshot();
          }
        });
      }

      function syncPrintRunnerSnapshot() {
        for (const runner of runners) {
          const code = runner.querySelector("[data-python-code]");
          const output = runner.querySelector("[data-python-output]");
          const printCode = runner.querySelector("[data-python-print-code]");
          const printOutput = runner.querySelector("[data-python-print-output]");

          if (printCode && code) {
            printCode.textContent = code.value || "(empty code)";
          }

          if (printOutput && output) {
            printOutput.textContent = output.textContent || "(no output)";
          }
        }
      }
    }

    function decodeBase64Utf8(value) {
      const bytes = Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
      return new TextDecoder().decode(bytes);
    }

    async function copyTextToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
      }

      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.top = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();

      try {
        document.execCommand("copy");
      } finally {
        textarea.remove();
      }
    }

    function initializeCodeCopyButtons() {
      const codeBlocks = Array.from(document.querySelectorAll("pre.code-block"));

      for (const block of codeBlocks) {
        if (block.closest(".code-block-wrap")) {
          continue;
        }

        const wrapper = document.createElement("div");
        wrapper.className = "code-block-wrap";
        block.parentNode.insertBefore(wrapper, block);
        wrapper.appendChild(block);

        const button = document.createElement("button");
        button.className = "copy-code-button";
        button.type = "button";
        button.textContent = "Copy";
        button.setAttribute("aria-label", "Copy code block");

        button.addEventListener("click", async () => {
          const code = block.querySelector("code");
          const text = code ? code.textContent : block.textContent;
          const originalText = button.textContent;
          button.disabled = true;

          try {
            await copyTextToClipboard(text.endsWith("\n") ? text.slice(0, -1) : text);
            button.textContent = "Copied";
          } catch (error) {
            button.textContent = "Error";
          } finally {
            window.setTimeout(() => {
              button.textContent = originalText;
              button.disabled = false;
            }, 1400);
          }
        });

        wrapper.appendChild(button);
      }
    }

    function initializeTableCaptions() {
      const wrappers = Array.from(document.querySelectorAll(".table-wrap"));
      if (wrappers.length === 0) {
        return;
      }

      const updateCaptionOffset = (wrapper) => {
        const tableCaption = wrapper.querySelector(".table-caption");
        wrapper.style.setProperty("--table-caption-sticky-offset", tableCaption ? `${tableCaption.offsetHeight}px` : "0px");
        const tableHeader = wrapper.querySelector("thead");
        wrapper.style.setProperty("--table-header-sticky-offset", tableHeader ? `${tableHeader.offsetHeight}px` : "0px");
      };

      for (const wrapper of wrappers) {
        const table = wrapper.querySelector("table");
        const caption = table ? table.querySelector("caption") : null;
        if (!table || !caption) {
          updateCaptionOffset(wrapper);
          continue;
        }

        const tableCaption = document.createElement("div");
        tableCaption.className = "table-caption";
        tableCaption.innerHTML = caption.innerHTML;
        if (table.id) {
          tableCaption.id = `${table.id}-caption`;
          if (!table.hasAttribute("aria-labelledby")) {
            table.setAttribute("aria-labelledby", tableCaption.id);
          }
        }

        caption.remove();
        wrapper.insertBefore(tableCaption, table);
        updateCaptionOffset(wrapper);
      }

      window.addEventListener("resize", () => {
        for (const wrapper of wrappers) {
          updateCaptionOffset(wrapper);
        }
      });
    }

    function initializeTableScrollHints() {
      const wrappers = Array.from(document.querySelectorAll(".table-wrap.table-wide, .table-wrap.table-fixed-height"));
      if (wrappers.length === 0) {
        return;
      }

      const ensureFrame = (wrapper) => {
        if (wrapper.parentElement && wrapper.parentElement.classList.contains("table-scroll-frame")) {
          return wrapper.parentElement;
        }

        const frame = document.createElement("div");
        frame.className = "table-scroll-frame";
        wrapper.parentNode.insertBefore(frame, wrapper);
        frame.appendChild(wrapper);
        return frame;
      };

      const ensureShadow = (frame, className) => {
        let shadow = frame.querySelector(`:scope > .${className}`);
        if (!shadow) {
          shadow = document.createElement("span");
          shadow.className = `table-scroll-shadow ${className}`;
          shadow.setAttribute("aria-hidden", "true");
          frame.insertBefore(shadow, frame.firstChild);
        }
        return shadow;
      };

      const updateWrapper = (wrapper) => {
        const frame = wrapper.parentElement && wrapper.parentElement.classList.contains("table-scroll-frame")
          ? wrapper.parentElement
          : wrapper;
        const captionOffset = window.getComputedStyle(wrapper).getPropertyValue("--table-caption-sticky-offset") || "0px";
        const headerOffset = window.getComputedStyle(wrapper).getPropertyValue("--table-header-sticky-offset") || "0px";
        const table = wrapper.querySelector("table");
        const maxScrollTop = wrapper.scrollHeight - wrapper.clientHeight;
        const hasVerticalOverflow = maxScrollTop > 1;
        const verticalScrollbarWidth = hasVerticalOverflow ? Math.max(18, wrapper.offsetWidth - wrapper.clientWidth) : 0;
        frame.style.setProperty("--table-caption-sticky-offset", captionOffset.trim());
        frame.style.setProperty("--table-header-sticky-offset", headerOffset.trim());
        frame.style.setProperty("--table-body-scroll-height", table ? `${table.offsetHeight}px` : `${wrapper.clientHeight}px`);
        frame.style.setProperty("--table-vertical-scrollbar-width", `${verticalScrollbarWidth}px`);

        if (wrapper.classList.contains("table-wide")) {
          const maxScrollLeft = wrapper.scrollWidth - wrapper.clientWidth;
          const hasLess = maxScrollLeft > 1 && wrapper.scrollLeft > 1;
          const hasMore = maxScrollLeft > 1 && wrapper.scrollLeft < maxScrollLeft - 1;
          frame.classList.toggle("has-scroll-x-less", hasLess);
          frame.classList.toggle("has-scroll-x-more", hasMore);
        }

        if (wrapper.classList.contains("table-fixed-height")) {
          const hasLess = maxScrollTop > 1 && wrapper.scrollTop > 1;
          const hasMore = maxScrollTop > 1 && wrapper.scrollTop < maxScrollTop - 1;
          frame.classList.toggle("has-scroll-y-less", hasLess);
          frame.classList.toggle("has-scroll-y-more", hasMore);
        }
      };

      for (const wrapper of wrappers) {
        const frame = ensureFrame(wrapper);

        if (wrapper.classList.contains("table-wide")) {
          ensureShadow(frame, "table-scroll-shadow-x-left");
          ensureShadow(frame, "table-scroll-shadow-x-right");
        }

        if (wrapper.classList.contains("table-fixed-height")) {
          ensureShadow(frame, "table-scroll-shadow-y-top");
          ensureShadow(frame, "table-scroll-shadow-y-bottom");
        }

        updateWrapper(wrapper);
        wrapper.addEventListener("scroll", () => updateWrapper(wrapper), { passive: true });
      }

      window.addEventListener("resize", () => {
        for (const wrapper of wrappers) {
          updateWrapper(wrapper);
        }
      });
    }


    document.addEventListener("DOMContentLoaded", () => {
      const runners = Array.from(document.querySelectorAll("[data-python-runner-panel]"));

      for (const runner of runners) {
        initializePythonRunner(runner);
      }

      initializePrintSnapshotSync(runners);

      if (window.Prism) {
        window.Prism.highlightAll();
      }
      initializeCodeCopyButtons();
      initializeTableCaptions();
      initializeTableScrollHints();
      initializeLayoutModeControl();
      initializeMermaid();
      initializeVegaLite();
    });
