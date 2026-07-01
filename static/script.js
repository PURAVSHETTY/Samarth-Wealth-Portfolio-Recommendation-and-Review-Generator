document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const fileNameBadge = document.getElementById("uploaded-file-name");
    const loadSampleBtn = document.getElementById("load-sample-btn");
    const geminiKeyInput = document.getElementById("gemini-key-input");
    
    // Progress Bar
    const progressContainer = document.getElementById("upload-progress-container");
    const progressBar = document.getElementById("upload-progress-bar");
    const progressText = document.getElementById("upload-progress-text");
    
    // Containers
    const unloadedContainer = document.getElementById("unloaded-container");
    const loadingContainer = document.getElementById("loading-container");
    const parsedContainer = document.getElementById("parsed-container");
    const downloadContainer = document.getElementById("download-container");
    const missingFieldsContainer = document.getElementById("missing-fields-container");
    const missingFieldsInputs = document.getElementById("missing-fields-inputs");
    
    // Display elements
    const clientNameDisplay = document.getElementById("client-name-display");
    const detectedSheetsDisplay = document.getElementById("detected-sheets-display");
    const detectedAllocColsDisplay = document.getElementById("detected-alloc-cols-display");
    const detectedProdColsDisplay = document.getElementById("detected-prod-cols-display");
    const detectedFundsList = document.getElementById("detected-funds-list");
    
    // Action Buttons
    const generateAiBtn = document.getElementById("generate-ai-btn");
    const downloadPdfBtn = document.getElementById("download-pdf-btn");
    const resetPipelineBtn = document.getElementById("reset-pipeline-btn");
    const submitMissingFieldsBtn = document.getElementById("submit-missing-fields-btn");
    
    // Workflow Selector Elements
    const tabRec = document.getElementById("tab-recommendation");
    const tabRev = document.getElementById("tab-review");
    const uploadCardTitle = document.getElementById("upload-card-title");
    const uploadCardDesc = document.getElementById("upload-card-desc");
    
    // Review Specific Elements
    const reviewAnalyticsCard = document.getElementById("review-analytics-card");
    const reviewVarianceTableBody = document.getElementById("review-variance-table-body");
    const weightedExpenseDisplay = document.getElementById("weighted-expense-display");
    const weightedSharpeDisplay = document.getElementById("weighted-sharpe-display");

    const structureInfoCard = document.getElementById("structure-info-card");
    const listHeaderTitle = document.getElementById("list-header-title");
    const parsedActionFooter = document.getElementById("parsed-action-footer");
    
    // Toast Notification
    const toast = document.getElementById("toast-notification");
    const toastMessage = document.getElementById("toast-message");
    const toastIcon = document.getElementById("toast-icon");

    // State Variables
    let currentWorkflow = "recommendation";
    let currentFilepath = null;
    let currentProposalData = null;
    let autoTriggerTimeout = null;
    
    // Toggle Workflow Tabs
    function setWorkflow(wf) {
        currentWorkflow = wf;
        resetUI();
        fileInput.value = "";
        fileNameBadge.textContent = "No file selected";
        
        if (wf === "recommendation") {
            tabRec.classList.add("active");
            tabRev.classList.remove("active");
            uploadCardTitle.textContent = "Upload Portfolio Spreadsheet";
            uploadCardDesc.textContent = "Upload your completed client portfolio spreadsheet. Messy sheets and varying column header styles will be parsed dynamically by the AI system.";
            loadSampleBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Process Workspace Sample';
        } else {
            tabRec.classList.remove("active");
            tabRev.classList.add("active");
            uploadCardTitle.textContent = "Upload Review Holdings Sheet";
            uploadCardDesc.textContent = "Upload your client\'s existing holdings sheet with buy costs, asset classes, and target allocations to parse and analyze current balances.";
            loadSampleBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Process Review Sample';
        }
        showToast(`Switched to Portfolio ${wf === "recommendation" ? "Recommendation" : "Review"} workflow`, "info");
    }
    
    tabRec.addEventListener("click", () => setWorkflow("recommendation"));
    tabRev.addEventListener("click", () => setWorkflow("review"));
    


    // Toast Alert Helper
    function showToast(message, type = "info") {
        toastMessage.textContent = message;
        toast.className = "toast"; // Reset
        toast.classList.add(type);
        
        if (type === "success") {
            toastIcon.className = "fa-solid fa-circle-check toast-icon";
        } else if (type === "error") {
            toastIcon.className = "fa-solid fa-circle-xmark toast-icon";
        } else {
            toastIcon.className = "fa-solid fa-circle-info toast-icon";
        }
        
        toast.classList.remove("hidden");
        
        if (window.toastTimeout) clearTimeout(window.toastTimeout);
        window.toastTimeout = setTimeout(() => {
            toast.classList.add("hidden");
        }, 6000);
    }

    // Local Persistence of Gemini Key
    const apiKeyWarning = document.getElementById("api-key-warning");
    function updateApiKeyWarning() {
        const apiKey = geminiKeyInput.value.trim();
        console.log("[DEBUG] Checking Gemini API key status. Found key length:", apiKey.length);
        if (!apiKey) {
            apiKeyWarning.classList.remove("hidden");
            apiKeyWarning.classList.add("d-flex");
            console.log("[DEBUG] Gemini API key is missing. Frontend warning banner displayed.");
        } else {
            apiKeyWarning.classList.add("hidden");
            apiKeyWarning.classList.remove("d-flex");
            console.log("[DEBUG] Gemini API key is present. Warning banner hidden.");
        }
    }

    if (localStorage.getItem("gemini_key")) {
        geminiKeyInput.value = localStorage.getItem("gemini_key");
    }
    updateApiKeyWarning();

    geminiKeyInput.addEventListener("input", (e) => {
        localStorage.setItem("gemini_key", e.target.value);
        updateApiKeyWarning();
    });

    // ── Drag & Drop Event Handling ──────────────────────────────────────────
    
    dropZone.addEventListener("click", () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) {
            uploadFileXHR(files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length) {
            uploadFileXHR(e.target.files[0]);
        }
    });

    // ── Upload Handler using XMLHttpRequest (XHR) for Progress Tracking ──────

    function uploadFileXHR(file) {
        if (autoTriggerTimeout) clearTimeout(autoTriggerTimeout);

        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        if (ext !== ".xlsx" && ext !== ".xls") {
            showToast("Invalid file format. Please upload an Excel spreadsheet (.xlsx or .xls)", "error");
            fileNameBadge.textContent = "No file selected";
            resetUI();
            return;
        }

        fileNameBadge.textContent = file.name;
        showToast(`Uploading '${file.name}' to server...`, "info");
        
        // Reset and hide views
        unloadedContainer.classList.remove("hidden");
        parsedContainer.classList.add("hidden");
        loadingContainer.classList.add("hidden");
        downloadContainer.classList.add("hidden");
        missingFieldsContainer.classList.add("hidden");

        // Show progress bars
        progressContainer.classList.remove("hidden");
        progressText.classList.remove("hidden");
        progressBar.style.width = "0%";
        progressBar.textContent = "0%";
        progressText.textContent = "Uploading: 0%";

        const formData = new FormData();
        formData.append("file", file);

        const xhr = new XMLHttpRequest();

        // Track upload progress percentage
        xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = `${percent}%`;
                progressBar.textContent = `${percent}%`;
                progressText.textContent = `Uploading: ${percent}%`;
                
                if (percent === 100) {
                    progressText.textContent = "Upload successful. Parsing spreadsheet on server...";
                }
            }
        });

        // Response finish handler
        xhr.onload = function() {
            setTimeout(() => {
                progressContainer.classList.add("hidden");
                progressText.classList.add("hidden");
            }, 1000);

            let result = {};
            try {
                result = JSON.parse(xhr.responseText);
            } catch (err) {
                result = { error: "Failed to parse JSON response from server" };
            }

            if (xhr.status >= 200 && xhr.status < 300) {
                showToast(result.message || "Excel parsed successfully!", "success");
                currentFilepath = result.filepath;
                currentProposalData = result.proposal_data;
                
                // Check if some fields are missing (Requirement 19)
                // Check if some fields are missing (Requirement 19)
                if (result.missing_fields && result.missing_fields.length > 0) {
                    showToast("Some critical details could not be detected. Please fill them below.", "warning");
                    displayMissingFieldsState(result.missing_fields);
                } else {
                    displayParsedState(result);
                    
                    // Conditionally skip AI trigger for review workflow (Phase 1)
                    if (result.workflow !== "review") {
                        // AUTOMATICALLY trigger AI analysis after 2 seconds
                        showToast("Launching AI portfolio analysis in 2 seconds...", "info");
                        autoTriggerTimeout = setTimeout(() => {
                            triggerAiProposalGeneration();
                        }, 2000);
                    } else {
                        showToast("Portfolio Review context parsed and loaded for verification.", "success");
                    }
                }
            } else {
                // Show actual error message on screen instead of generic failed
                const errMsg = result.error || `Upload failed (Status: ${xhr.status})`;
                showToast(errMsg, "error");
                fileNameBadge.textContent = "Parsing failed";
                resetUI();
            }
        };

        xhr.onerror = function() {
            progressContainer.classList.add("hidden");
            progressText.classList.add("hidden");
            showToast("Network connection error. Failed to reach the server.", "error");
            fileNameBadge.textContent = "Connection error";
            resetUI();
        };

        const apiKey = geminiKeyInput.value.trim ? geminiKeyInput.value.trim() : geminiKeyInput.value;
        xhr.open("POST", "/upload");
        xhr.setRequestHeader("X-Workflow", currentWorkflow);
        if (apiKey) {
            xhr.setRequestHeader("X-Gemini-Key", apiKey);
        }
        xhr.send(formData);
    }

    // Process Workspace Demo sample
    loadSampleBtn.addEventListener("click", async () => {
        if (autoTriggerTimeout) clearTimeout(autoTriggerTimeout);
        
        if (currentWorkflow === "review") {
            fileNameBadge.textContent = "PORTFOLIO_REVIEW_TEMPLATE.xlsx (Workspace Demo)";
        } else {
            fileNameBadge.textContent = "CLIENT_TEMPLATE.xlsx (Workspace Demo)";
        }
        showToast("Processing demo template...", "info");
        
        resetUI();

        try {
            const response = await fetch(`/api/default_data?workflow=${currentWorkflow}`);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not parse default sample");
            }

            showToast("Demo loaded successfully!", "success");
            currentFilepath = result.filepath;
            currentProposalData = result.proposal_data;

            if (result.missing_fields && result.missing_fields.length > 0) {
                displayMissingFieldsState(result.missing_fields);
            } else {
                displayParsedState(result);
                
                // Conditionally skip AI trigger for review workflow (Phase 1)
                if (result.workflow !== "review") {
                    showToast("Launching AI portfolio analysis in 2 seconds...", "info");
                    autoTriggerTimeout = setTimeout(() => {
                        triggerAiProposalGeneration();
                    }, 2000);
                } else {
                    showToast("Portfolio Review context parsed and loaded for verification.", "success");
                }
            }

        } catch (err) {
            showToast(err.message, "error");
            resetUI();
        }
    });

    // Renders the missing fields inputs (Requirement 19)
    function displayMissingFieldsState(fields) {
        missingFieldsInputs.innerHTML = "";
        fields.forEach(field => {
            const div = document.createElement("div");
            div.className = "form-group d-flex flex-column gap-1";
            
            // Set label and input
            div.innerHTML = `
                <label class="small text-warning fw-semibold text-uppercase">${field}</label>
                <input type="text" class="form-control bg-dark border-secondary text-white small missing-field-val" data-field="${field}" placeholder="Enter ${field} value..." required>`;
            missingFieldsInputs.appendChild(div);
        });
        
        unloadedContainer.classList.add("hidden");
        parsedContainer.classList.add("hidden");
        loadingContainer.classList.add("hidden");
        downloadContainer.classList.add("hidden");
        missingFieldsContainer.classList.remove("hidden");
        missingFieldsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // Handles submit missing fields
    submitMissingFieldsBtn.addEventListener("click", () => {
        const inputs = missingFieldsInputs.querySelectorAll(".missing-field-val");
        let allValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.classList.add("border-danger");
                allValid = false;
            } else {
                input.classList.remove("border-danger");
                const fieldName = input.getAttribute("data-field");
                const val = input.value.trim();
                
                // Map to correct section inside currentProposalData
                if (fieldName === "Client Name" || fieldName === "Portfolio Corpus (INR)") {
                    currentProposalData.client[fieldName] = val;
                } else if (fieldName === "Firm Name" || fieldName === "Advisor Name") {
                    currentProposalData.firm[fieldName] = val;
                }
            }
        });
        
        if (!allValid) {
            showToast("Please fill in all requested fields.", "error");
            return;
        }
        
        // Hide missing fields card and trigger generation
        missingFieldsContainer.classList.add("hidden");
        
        // Update client display values in success card
        clientNameDisplay.textContent = currentProposalData.client["Client Name"] || "Valued Client";
        
        showToast("Details verified. Automatically launching AI analysis...", "success");
        triggerAiProposalGeneration();
    });

    // Update screen view to show parsed details
    function displayParsedState(result) {
        clientNameDisplay.textContent = result.client_name;
        
        if (result.workflow === "review") {
            // PORTFOLIO REVIEW WORKFLOW VIEW
            structureInfoCard.classList.add("hidden");
            reviewAnalyticsCard.classList.remove("hidden");
            parsedActionFooter.classList.remove("hidden");
            generateAiBtn.innerHTML = '<i class="fa-solid fa-file-pdf"></i> Generate Portfolio Review';
            
            listHeaderTitle.textContent = "Parsed Holdings & Returns";
            
            // Populate list of funds with custom details
            detectedFundsList.innerHTML = "";
            if (result.funds && result.funds.length > 0) {
                result.funds.forEach(fund => {
                    const item = document.createElement("div");
                    item.className = "list-group-item d-flex justify-content-between align-items-center py-2";
                    
                    const gainColor = fund.gain_loss_pct >= 0 ? "text-success" : "text-danger";
                    const gainSign = fund.gain_loss_pct >= 0 ? "+" : "";
                    
                    item.innerHTML = `
                        <div>
                            <strong class="d-block"><i class="fa-solid fa-file-invoice-dollar text-warning me-2"></i>${fund.name}</strong>
                            <span class="small text-muted">${fund.class} &nbsp;|&nbsp; Weight: ${fund.allocation_pct}%</span>
                        </div>
                        <span class="badge bg-secondary-subtle px-2 py-1 ${gainColor}">${gainSign}${fund.gain_loss_pct}% return</span>
                    `;
                    detectedFundsList.appendChild(item);
                });
            } else {
                detectedFundsList.innerHTML = `<div class="list-group-item text-muted">No holdings detected</div>`;
            }
            
            // Populate variance table
            reviewVarianceTableBody.innerHTML = "";
            const analytics = result.analytics || {};
            const varianceData = analytics.allocation_variance || {};
            
            for (const [assetClass, data] of Object.entries(varianceData)) {
                const tr = document.createElement("tr");
                const varColor = data.variance_pct > 0 ? "text-danger" : (data.variance_pct < 0 ? "text-warning" : "text-success");
                const varSign = data.variance_pct > 0 ? "+" : "";
                
                tr.innerHTML = `
                    <td class="fw-semibold">${assetClass}</td>
                    <td class="text-end">${data.current_pct}%</td>
                    <td class="text-end">${data.target_pct}%</td>
                    <td class="text-end ${varColor}">${varSign}${data.variance_pct}%</td>
                    <td class="text-end fw-bold">${data.rebalance_action}</td>
                `;
                reviewVarianceTableBody.appendChild(tr);
            }
            
            weightedExpenseDisplay.textContent = `${(analytics.weighted_average_expense_ratio * 100).toFixed(2)}%`;
            weightedSharpeDisplay.textContent = analytics.weighted_average_sharpe_ratio || "—";

            
        } else {
            // PORTFOLIO RECOMMENDATION WORKFLOW VIEW
            structureInfoCard.classList.remove("hidden");
            reviewAnalyticsCard.classList.add("hidden");
            parsedActionFooter.classList.remove("hidden");
            generateAiBtn.innerHTML = '<i class="fa-solid fa-robot"></i> Generate AI Proposal';
            
            listHeaderTitle.textContent = "Detected Products / Funds";
            
            detectedSheetsDisplay.textContent = result.sheets ? result.sheets.join(", ") : "None";
            detectedAllocColsDisplay.textContent = result.allocation_columns ? result.allocation_columns.join(", ") : "None";
            detectedProdColsDisplay.textContent = result.products_columns ? result.products_columns.join(", ") : "None";
            
            detectedFundsList.innerHTML = "";
            if (result.funds && result.funds.length > 0) {
                result.funds.forEach(fund => {
                    const item = document.createElement("div");
                    item.className = "list-group-item d-flex justify-content-between align-items-center";
                    item.innerHTML = `
                        <span><i class="fa-solid fa-file-invoice-dollar text-warning me-2"></i>${fund.name}</span>
                        <span class="badge bg-secondary-subtle text-muted small px-2 py-1">${fund.class}</span>
                    `;
                    detectedFundsList.appendChild(item);
                });
            } else {
                detectedFundsList.innerHTML = `<div class="list-group-item text-muted">No funds detected in Products sheet</div>`;
            }

        }

        unloadedContainer.classList.add("hidden");
        loadingContainer.classList.add("hidden");
        downloadContainer.classList.add("hidden");
        parsedContainer.classList.remove("hidden");
        parsedContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // ── Generate AI Portfolio (POST /generate-proposal) ───────────────────

    async function triggerAiProposalGeneration() {
        console.log("[DEBUG] Triggering AI proposal generation workflow.");
        if (!currentFilepath) {
            console.error("[DEBUG ERROR] Generation aborted: currentFilepath is empty.");
            showToast("Please upload an Excel spreadsheet first.", "error");
            return;
        }

        // Disable button, show loading text/spinner inside button temporarily (Requirement 4)
        generateAiBtn.disabled = true;
        const originalBtnText = generateAiBtn.innerHTML;
        generateAiBtn.innerHTML = currentWorkflow === "review" ? 
            '<i class="fa-solid fa-spinner fa-spin"></i> AI is generating review...' : 
            '<i class="fa-solid fa-spinner fa-spin"></i> AI is generating proposal...';
        loadSampleBtn.disabled = true;

        // Show Loading spinner panel screen
        parsedContainer.classList.add("hidden");
        missingFieldsContainer.classList.add("hidden");
        loadingContainer.classList.remove("hidden");
        loadingContainer.scrollIntoView({ behavior: 'smooth' });

        // Update loading screen title (Requirement 4)
        const loadingTitle = loadingContainer.querySelector("h3");
        if (loadingTitle) {
            loadingTitle.textContent = currentWorkflow === "review" ? 
                "AI is generating review report..." : 
                "AI is generating proposal...";
        }

        // Setup dynamic progress updates to prevent UI from appearing frozen (Requirement 17)
        const progressDesc = loadingContainer.querySelector("p");
        if (progressDesc) {
            progressDesc.textContent = currentWorkflow === "review" ? 
                "Initiating portfolio audit..." : 
                "Initiating portfolio allocation...";
        }
        
        let elapsedSeconds = 0;
        console.log("[DEBUG] Starting frontend dynamic progress logging timer.");
        const progressInterval = setInterval(() => {
            elapsedSeconds += 3;
            console.log(`[DEBUG] Generation in progress... elapsed: ${elapsedSeconds} seconds.`);
            if (progressDesc) {
                if (currentWorkflow === "review") {
                    if (elapsedSeconds === 3) {
                        progressDesc.textContent = "Analyzing asset class drift and gap metrics...";
                    } else if (elapsedSeconds === 6) {
                        progressDesc.textContent = "Engaging Gemini AI audit models...";
                    } else if (elapsedSeconds === 9) {
                        progressDesc.textContent = "Formulating rebalancing recommendations...";
                    } else if (elapsedSeconds === 12) {
                        progressDesc.textContent = "Writing fund audits and performance commentary...";
                    } else if (elapsedSeconds === 15) {
                        progressDesc.textContent = "Compiling ReportLab PDF report slides...";
                    } else if (elapsedSeconds >= 18) {
                        progressDesc.textContent = "Wrapping up PDF package compilation...";
                    }
                } else {
                    if (elapsedSeconds === 3) {
                        progressDesc.textContent = "Categorizing products and analyzing risk matrices...";
                    } else if (elapsedSeconds === 6) {
                        progressDesc.textContent = "Engaging Gemini AI optimization models...";
                    } else if (elapsedSeconds === 9) {
                        progressDesc.textContent = "Formulating customized investment rationales...";
                    } else if (elapsedSeconds === 12) {
                        progressDesc.textContent = "Compiling institutional ReportLab PDF slides...";
                    } else if (elapsedSeconds === 15) {
                        progressDesc.textContent = "Finalizing layout rhythm and formatting tables...";
                    } else if (elapsedSeconds >= 18) {
                        progressDesc.textContent = "Wrapping up PDF package compilation (takes a few more seconds)...";
                    }
                }
            }
        }, 3000);

        const apiKey = typeof geminiKeyInput.value.trim === "function" ? geminiKeyInput.value.trim() : geminiKeyInput.value;
        const headers = {
            "Content-Type": "application/json",
            "X-Workflow": currentWorkflow
        };
        if (apiKey) {
            headers["X-Gemini-Key"] = apiKey;
        }

        const payload = {
            filepath: currentFilepath,
            proposal_data: currentProposalData
        };

        // Abort Controller for timeout handling (Requirement 11)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.warn("[DEBUG WARNING] Proposal generation timed out after 60 seconds. Aborting request.");
            controller.abort();
        }, 60000); // 60 seconds timeout

        console.log("[DEBUG] Sending POST request to /generate-proposal with payload:", JSON.stringify(payload));
        
        try {
            const response = await fetch("/generate-proposal", {
                method: "POST",
                headers: headers,
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            // Clear progress timer and timeout
            clearInterval(progressInterval);
            clearTimeout(timeoutId);

            console.log(`[DEBUG] Received response from /generate-proposal. Status: ${response.status}`);
            const result = await response.json();

            if (!response.ok) {
                console.error("[DEBUG ERROR] Backend returned error status:", response.status, result);
                throw new Error(result.error || "Failed to generate AI proposal");
            }

            console.log("[DEBUG] Proposal generation succeeded! PDF URL path:", result.pdf_url);
            showToast(currentWorkflow === "review" ? 
                "AI portfolio review and PDF generated successfully!" : 
                "AI proposal and PDF generated successfully!", "success");
            
            // Set download URL link and show download screen (Requirement 10)
            const downloadTitle = downloadContainer.querySelector("h3");
            if (downloadTitle) {
                downloadTitle.textContent = currentWorkflow === "review" ? 
                    "Portfolio Review Compiled Successfully!" : 
                    "Proposal Compiled Successfully!";
                downloadTitle.className = "h5 fw-bold text-success";
            }
            const downloadDesc = downloadContainer.querySelector("p");
            if (downloadDesc) {
                downloadDesc.textContent = currentWorkflow === "review" ? 
                    "Gemini AI has completed the portfolio audit, rebalancing thesis, and scheme performance reviews. Click below to download the ReportLab PDF." : 
                    "Gemini AI has categorized the assets and completed client-friendly rationales. Click below to download the ReportLab PDF.";
            }
            downloadPdfBtn.innerHTML = currentWorkflow === "review" ? 
                '<i class="fa-solid fa-cloud-arrow-down"></i> Download Review PDF' : 
                '<i class="fa-solid fa-cloud-arrow-down"></i> Download Proposal PDF';
            downloadPdfBtn.setAttribute("href", result.pdf_url);
            
            loadingContainer.classList.add("hidden");
            downloadContainer.classList.remove("hidden");
            downloadContainer.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            // Clear progress timer and timeout
            clearInterval(progressInterval);
            clearTimeout(timeoutId);

            // Detailed logging (Requirement 15 & 16)
            if (err.name === 'AbortError') {
                console.error("[DEBUG ERROR] Request was aborted due to timeout (60 seconds exceeded).");
                showToast("Request timed out. Proposal generation took longer than 60 seconds.", "error");
            } else {
                console.error("[DEBUG ERROR] Failed proposal generation:", err);
                showToast(err.message || "Failed to generate proposal.", "error");
            }
            
            // Revert back to parsed screen so it doesn't freeze (Requirement 7)
            loadingContainer.classList.add("hidden");
            parsedContainer.classList.remove("hidden");
        } finally {
            // Re-enable buttons and restore original text (Requirement 4)
            generateAiBtn.disabled = false;
            generateAiBtn.innerHTML = originalBtnText;
            loadSampleBtn.disabled = false;
            console.log("[DEBUG] UI buttons re-enabled and state restored.");
        }
    }

    // Manual backup click trigger
    generateAiBtn.addEventListener("click", triggerAiProposalGeneration);

    // Reset Pipeline helper
    resetPipelineBtn.addEventListener("click", () => {
        if (autoTriggerTimeout) clearTimeout(autoTriggerTimeout);
        resetUI();
        fileNameBadge.textContent = "No file selected";
        fileInput.value = "";
    });

    function resetUI() {
        currentFilepath = null;
        currentProposalData = null;
        parsedContainer.classList.add("hidden");
        loadingContainer.classList.add("hidden");
        downloadContainer.classList.add("hidden");
        missingFieldsContainer.classList.add("hidden");
        unloadedContainer.classList.remove("hidden");
    }

    // Auto-test query parameter handling
    const testParams = new URLSearchParams(window.location.search);
    const autoTest = testParams.get("auto_test");
    if (autoTest === "review") {
        setWorkflow("review");
        setTimeout(() => {
            loadSampleBtn.click();
        }, 300);
    } else if (autoTest === "recommendation") {
        setWorkflow("recommendation");
        setTimeout(() => {
            loadSampleBtn.click();
        }, 300);
    }
});
