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

    function getTocTitle(element) {
      if (element.dataset.tocTitle) {
        return element.dataset.tocTitle;
      }

      const heading = element.matches("section")
        ? element.querySelector("h2, h3")
        : element;

      return heading ? heading.textContent.trim() : element.id;
    }

    function getTocHref(element) {
      return `#${element.id}`;
    }

    function getTocLevel(element) {
      if (element.dataset.tocLevel) {
        return Number.parseInt(element.dataset.tocLevel, 10);
      }

      if (element.matches("h3")) {
        return 3;
      }

      return 2;
    }

    function createTocItem(element) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      const level = getTocLevel(element);

      link.href = getTocHref(element);
      link.textContent = getTocTitle(element);

      if (level >= 3) {
        item.classList.add(`toc-level-${level}`);
      }

      item.appendChild(link);
      return item;
    }

    function getOrCreateChildList(item) {
      let childList = item.querySelector(":scope > ol");

      if (!childList) {
        childList = document.createElement("ol");
        item.appendChild(childList);
      }

      return childList;
    }

    function buildNestedToc(toc, tocTargets) {
      const stack = [
        {
          level: 1,
          list: toc,
          item: null
        }
      ];

      for (const target of tocTargets) {
        const level = getTocLevel(target);
        const item = createTocItem(target);

        while (stack.length > 1 && stack[stack.length - 1].level >= level) {
          stack.pop();
        }

        let parent = stack[stack.length - 1];

        if (level > parent.level + 1 && parent.item) {
          const childList = getOrCreateChildList(parent.item);
          parent = {
            level: level - 1,
            list: childList,
            item: parent.item
          };
          stack.push(parent);
        }

        parent.list.appendChild(item);

        stack.push({
          level,
          list: getOrCreateChildList(item),
          item
        });
      }

      for (const emptyList of toc.querySelectorAll("ol:empty")) {
        emptyList.remove();
      }
    }

    function buildToc() {
      const toc = document.getElementById("auto-toc");

      if (!toc) {
        return;
      }

      const tocTargets = Array.from(document.querySelectorAll("main [data-toc][id]"));
      toc.innerHTML = "";

      if (tocTargets.length === 0) {
        const item = document.createElement("li");
        item.textContent = "No TOC targets found. Add data-toc to structural sections or headings.";
        toc.appendChild(item);
        return;
      }

      buildNestedToc(toc, tocTargets);
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

        const workerSource = `
        const pyodideScriptUrl = "${PYODIDE_WORKER_CONFIG.scriptUrl}";
        const pyodideIndexUrl = "${PYODIDE_WORKER_CONFIG.indexUrl}";

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


    document.addEventListener("DOMContentLoaded", () => {
      buildToc();
      const runners = Array.from(document.querySelectorAll("[data-python-runner-panel]"));

      for (const runner of runners) {
        initializePythonRunner(runner);
      }

      initializePrintSnapshotSync(runners);

      if (window.Prism) {
        window.Prism.highlightAll();
      }
      initializeCodeCopyButtons();
      initializeMermaid();
    });
