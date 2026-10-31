import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { once } from "node:events";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import net from "node:net";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(frontendDir, "..");
const backendDir = path.join(repoRoot, "backend");
const pythonExe = path.join(backendDir, ".venv", "Scripts", "python.exe");
const nextCli = path.join(frontendDir, "node_modules", "next", "dist", "bin", "next");
const outputDir = path.join(frontendDir, "test-results", "launch-gate");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "resumind-launch-gate-"));
const dbPath = path.join(tempRoot, "isolated.sqlite3");
const storageRoot = path.join(tempRoot, "storage");
const nextDistDirName = `.next-launch-gate-${process.pid}`;
const nextDistDir = path.join(frontendDir, nextDistDirName);
const nextTsconfigName = `.tsconfig-launch-gate-${process.pid}.json`;
const nextTsconfigPath = path.join(frontendDir, nextTsconfigName);
fs.mkdirSync(storageRoot, { recursive: true });
fs.mkdirSync(outputDir, { recursive: true });

const results = [];
const processes = [];
let browser;
let backend;
let devFrontend;
let frontend;
let activePage;

function record(name, detail = "passed") {
  results.push({ name, detail });
  console.log(`PASS ${name}${detail === "passed" ? "" : `: ${detail}`}`);
}

function assertIncludes(haystack, needle, message) {
  assert.ok(String(haystack).includes(needle), message ?? `Expected text to include ${JSON.stringify(needle)}`);
}

function launch(command, args, options) {
  const child = spawn(command, args, {
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });
  child.outputTail = "";
  const append = (chunk) => {
    child.outputTail = `${child.outputTail}${chunk.toString()}`.slice(-12000);
  };
  child.stdout.on("data", append);
  child.stderr.on("data", append);
  processes.push(child);
  return child;
}

async function freePort() {
  const server = net.createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const { port } = server.address();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  return port;
}

async function waitFor(check, label, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      if (await check()) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  const tails = processes.map((child) => child.outputTail).filter(Boolean).join("\n--- process ---\n");
  throw new Error(`${label} did not become ready.${lastError ? ` Last error: ${lastError}` : ""}\n${tails}`);
}

function runPython(code, args = [], env = process.env) {
  const result = spawnSync(pythonExe, ["-c", code, ...args], {
    cwd: backendDir,
    env,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 10 * 1024 * 1024,
  });
  if (result.status !== 0) {
    throw new Error(`Python helper failed (${result.status}):\n${result.stdout}\n${result.stderr}`);
  }
  return result.stdout.trim();
}

async function stopProcess(child) {
  if (!child || child.exitCode !== null) return;
  child.kill("SIGTERM");
  await Promise.race([
    once(child, "exit").catch(() => {}),
    new Promise((resolve) => setTimeout(resolve, 5000)),
  ]);
}

async function makeDownload(page, button, filename) {
  const downloadPromise = page.waitForEvent("download", { timeout: 30000 });
  await button.click();
  const download = await downloadPromise;
  assert.equal(await download.failure(), null, `${filename} download failed`);
  const target = path.join(outputDir, filename);
  await download.saveAs(target);
  assert.ok(fs.statSync(target).size > 100, `${filename} is unexpectedly empty`);
  return target;
}

async function main() {
  assert.ok(fs.existsSync(pythonExe), `Backend virtualenv Python not found: ${pythonExe}`);
  assert.ok(fs.existsSync(nextCli), `Next.js CLI not found: ${nextCli}`);
  assert.ok(!fs.existsSync(nextTsconfigPath), `Temporary TypeScript config already exists: ${nextTsconfigPath}`);
  assert.ok(!fs.existsSync(nextDistDir), `Temporary Next.js output directory already exists: ${nextDistDir}`);
  fs.copyFileSync(path.join(frontendDir, "tsconfig.json"), nextTsconfigPath);

  const browserExe = process.env.RESUMIND_CHROMIUM_PATH || path.join(
    process.env.LOCALAPPDATA || "",
    "ms-playwright",
    "chromium_headless_shell-1228",
    "chrome-headless-shell-win64",
    "chrome-headless-shell.exe",
  );
  assert.ok(fs.existsSync(browserExe), `Chromium headless shell not found: ${browserExe}; set RESUMIND_CHROMIUM_PATH to an installed browser executable.`);

  const apiPort = await freePort();
  const devPort = await freePort();
  const webPort = await freePort();
  const apiOrigin = `http://127.0.0.1:${apiPort}`;
  const devOrigin = `http://127.0.0.1:${devPort}`;
  const webOrigin = `http://127.0.0.1:${webPort}`;
  const databaseUrl = `sqlite+aiosqlite:///${dbPath.replaceAll("\\", "/")}`;
  const backendEnv = {
    ...process.env,
    APP_ENV: "development",
    DEBUG: "false",
    HOST: "127.0.0.1",
    PORT: String(apiPort),
    DATABASE_URL: databaseUrl,
    STORAGE_ROOT: storageRoot,
    CORS_ORIGINS: `${devOrigin},${webOrigin}`,
    SESSION_COOKIE_SECURE: "false",
    RATE_LIMIT_ENABLED: "true",
    RATE_LIMIT_API_PER_MINUTE: "600",
    RATE_LIMIT_UPLOAD_COUNT: "20",
    RATE_LIMIT_AI_COUNT: "40",
  };
  const frontendEnv = {
    ...process.env,
    NEXT_PUBLIC_API_BASE_URL: apiOrigin,
    RESUMIND_NEXT_DIST_DIR: nextDistDirName,
    RESUMIND_NEXT_TSCONFIG_PATH: nextTsconfigName,
    NEXT_TELEMETRY_DISABLED: "1",
    CI: "true",
  };

  const fixtureCode = String.raw`
import importlib.util, pathlib, sys
fixture_path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("synthetic_generator", fixture_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
(out / "synthetic_resume.pdf").write_bytes(module.create_synthetic_pdf(
    name="Samantha Reed", email="samantha.reed@synthetic-domain.com",
    phone="+1 (555) 849-2041", linkedin="linkedin.com/in/samanthareed-synthetic", pages=2))
(out / "synthetic_resume.docx").write_bytes(module.create_synthetic_docx(
    name="Elena Rostova", email="elena.rostova@synthetic-domain.com"))
(out / "invalid_resume.txt").write_text("Synthetic invalid upload fixture", encoding="utf-8")
`;
  const fixtureDir = path.join(tempRoot, "fixtures");
  runPython(fixtureCode, [path.join(backendDir, "tests", "fixtures", "synthetic_generator.py"), fixtureDir]);
  record("synthetic PDF, DOCX, and invalid upload fixtures generated");

  const migration = spawnSync(pythonExe, ["-m", "alembic", "upgrade", "head"], {
    cwd: backendDir,
    env: backendEnv,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 10 * 1024 * 1024,
  });
  assert.equal(migration.status, 0, `Isolated Alembic upgrade failed:\n${migration.stdout}\n${migration.stderr}`);
  record("isolated Alembic upgrade head", `${migration.stdout.trim()} ${migration.stderr.trim()}`.trim());

  backend = launch(pythonExe, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)], {
    cwd: backendDir,
    env: backendEnv,
  });
  await waitFor(async () => {
    const response = await fetch(`${apiOrigin}/api/health`);
    return response.ok;
  }, "FastAPI health endpoint");
  record("FastAPI running against isolated SQLite and storage roots");

  devFrontend = launch(process.execPath, [nextCli, "dev", "--hostname", "127.0.0.1", "--port", String(devPort)], {
    cwd: frontendDir,
    env: frontendEnv,
  });
  await waitFor(async () => {
    const response = await fetch(devOrigin);
    return response.ok && response.headers.has("content-security-policy");
  }, "Next.js development frontend");
  const devResponse = await fetch(devOrigin);
  const devCsp = devResponse.headers.get("content-security-policy") || "";
  assert.match(devCsp, /script-src[^;]*'unsafe-eval'/, "Development CSP must permit React's eval-based debugging tools");
  record("development CSP includes unsafe-eval for React development tools");

  browser = await chromium.launch({
    headless: true,
    executablePath: browserExe,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--disable-background-networking"],
  });
  const devContext = await browser.newContext();
  const devPage = await devContext.newPage();
  activePage = devPage;
  const blockedEvalErrors = [];
  devPage.on("pageerror", (error) => {
    if (/eval\(\)|unsafe-eval|Refused to evaluate/i.test(error.message)) blockedEvalErrors.push(error.message);
  });
  devPage.on("console", (message) => {
    if (message.type() === "error" && /eval\(\) is not supported|unsafe-eval|Refused to evaluate/i.test(message.text())) {
      blockedEvalErrors.push(message.text());
    }
  });
  await devPage.goto(devOrigin, { waitUntil: "networkidle", timeout: 90000 });
  await devPage.getByRole("heading", { name: /Your experience\./ }).waitFor();
  await devPage.waitForTimeout(500);
  assert.deepEqual(blockedEvalErrors, [], `Development browser reported a CSP/eval error: ${blockedEvalErrors.join(" | ")}`);
  assert.equal(await devPage.getByText(/eval\(\) is not supported in this environment/i).count(), 0, "Next.js development overlay still reports the CSP eval error");
  record("development homepage renders in Chromium without the CSP eval error");
  await devContext.close();
  await stopProcess(devFrontend);

  const frontendBuild = spawnSync(process.execPath, [nextCli, "build"], {
    cwd: frontendDir,
    env: frontendEnv,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 20 * 1024 * 1024,
  });
  assert.equal(frontendBuild.status, 0, `Next.js production build for E2E failed:\n${frontendBuild.stdout}\n${frontendBuild.stderr}`);
  record("Next.js production build for browser E2E", `${frontendBuild.stdout.trim()} ${frontendBuild.stderr.trim()}`.trim());

  frontend = launch(process.execPath, [nextCli, "start", "--hostname", "127.0.0.1", "--port", String(webPort)], {
    cwd: frontendDir,
    env: frontendEnv,
  });
  await waitFor(async () => {
    const response = await fetch(webOrigin);
    return response.ok;
  }, "Next.js frontend");
  const productionResponse = await fetch(webOrigin);
  const productionCsp = productionResponse.headers.get("content-security-policy") || "";
  assert.ok(productionCsp, "Production frontend did not return a CSP header");
  assert.doesNotMatch(productionCsp, /script-src[^;]*'unsafe-eval'/, "Production CSP must not permit unsafe-eval");
  record("production CSP retains its policy without unsafe-eval");

  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  activePage = page;
  const consoleErrors = [];
  const browserDialogs = [];
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  page.on("dialog", async (dialog) => {
    browserDialogs.push(dialog.message());
    await dialog.dismiss();
  });
  const sessionResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith("/api/session") && response.request().method() === "POST",
  { timeout: 30000 });
  await page.goto(webOrigin, { waitUntil: "networkidle", timeout: 90000 });
  await page.getByRole("heading", { name: /Your experience\./ }).waitFor();
  record("homepage renders in Chromium");

  const sessionResponse = await sessionResponsePromise;
  assert.equal(sessionResponse.status(), 200, "Anonymous session creation did not return HTTP 200");
  const firstSession = await sessionResponse.json();
  const cookies = await context.cookies(apiOrigin);
  assert.ok(cookies.some((cookie) => cookie.name === "resumind_session" && cookie.httpOnly), "HttpOnly anonymous session cookie was not set");
  record("anonymous session created with HttpOnly cookie", firstSession.id);

  await page.getByRole("radio", { name: "Job Match" }).click();
  const jobDescription = "Lead Distributed Systems Engineer. Requirements include 6+ years building scalable microservices with Python and FastAPI, asynchronous event driven pipelines, PostgreSQL, CI/CD, zero trust authentication, and cloud service operations.";
  await page.locator("#jobDescriptionInput").fill(jobDescription);
  await page.locator("#resumeFileInput").setInputFiles(path.join(fixtureDir, "invalid_resume.txt"));
  await page.getByText(/Invalid file type/i).waitFor();
  record("unsupported file extension rejected with a clear validation message");

  await page.locator("#resumeFileInput").setInputFiles(path.join(fixtureDir, "synthetic_resume.pdf"));
  const uploadResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/resume/upload"));
  await page.locator("#analyzeResumeBtn").click();
  const uploadResponse = await uploadResponsePromise;
  assert.equal(uploadResponse.status(), 201, `PDF upload failed: ${await uploadResponse.text()}`);
  const parsedPdf = await uploadResponse.json();
  await page.getByRole("heading", { name: "Review & Correct Extracted Details" }).waitFor();
  const profile = parsedPdf.structured_data;
  assert.equal(profile.contact.name, "Samantha Reed", "PDF contact name extraction is incorrect");
  assert.equal(profile.contact.email, "samantha.reed@synthetic-domain.com", "PDF email extraction is incorrect");
  assert.equal(profile.contact.phone, "+1 (555) 849-2041", "PDF phone extraction is incorrect");
  assert.ok(profile.contact.urls.some((url) => url === "linkedin.com/in/samanthareed-synthetic"), "PDF LinkedIn extraction is incorrect");
  assert.ok(profile.experience.some((entry) => /Lead Backend Engineer.*Nexus Systems.*Jan 2021.*Present/i.test(entry)), "PDF lead role or date range extraction is incorrect");
  assert.ok(profile.experience.some((entry) => /Software Engineer.*CoreLogic Inc.*Jun 2018.*Dec 2020/i.test(entry)), "PDF prior role or date range extraction is incorrect");
  assert.ok(profile.experience.some((entry) => /Architected async microservices reducing API latency by 35%/i.test(entry)), "PDF first experience bullet is missing");
  assert.ok(profile.experience.some((entry) => /Designed automated ETL pipelines processing 2M\+ synthetic records daily/i.test(entry)), "PDF second experience bullet is missing");
  assert.ok(profile.projects.some((entry) => /Project Horizon.*Open source telemetry tooling.*2022/i.test(entry)), "PDF project title or description extraction is incorrect");
  assert.ok(profile.projects.some((entry) => /high-performance parser for structured document formats/i.test(entry)), "PDF project bullet is missing");
  const expectedSkills = ["Python", "FastAPI", "PostgreSQL", "SQLite", "Next.js", "TypeScript", "Docker", "PyMuPDF", "CI/CD"];
  assert.ok(expectedSkills.every((skill) => profile.skills.includes(skill)), "PDF skills extraction is incomplete or incorrect");
  assert.ok(profile.education.some((entry) => /B\.S\. in Computer Science.*Pacific Crest University.*2014.*2018/i.test(entry)), "PDF degree, institution, or date range extraction is incorrect");
  record("PDF upload parsed contact, experience, project, skills, and education", JSON.stringify({
    contact: profile.contact,
    experience: profile.experience,
    projects: profile.projects,
    skills: profile.skills,
    education: profile.education,
  }));

  await page.locator("[placeholder='Your name as it appears on the resume']").fill("Samantha Reed Verified");
  await page.locator("[placeholder='your@email.com']").fill("samantha.reed@synthetic-domain.com");
  await page.locator("#saveCorrectionsBtn").click();
  await page.getByText("Saved", { exact: true }).waitFor();
  // Confirm the value through the page's configured API origin without exposing the cookie to Node.
  const savedProfile = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/resume`, { credentials: "include" });
    return response.ok ? response.json() : null;
  }, apiOrigin);
  assert.ok(savedProfile && savedProfile.structured_data.contact.name === "Samantha Reed Verified", "Corrected resume was not saved to the active session");
  record("review correction saved and read back from backend");

  const lockedBeforeAssessment = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/reanalysis`, { credentials: "include" });
    return { status: response.status, payload: await response.json() };
  }, apiOrigin);
  assert.equal(lockedBeforeAssessment.status, 200);
  assert.equal(lockedBeforeAssessment.payload.available, false, "Differential comparison unlocked without a baseline");
  record("differential comparison remains locked without an ATS baseline", lockedBeforeAssessment.payload.reason);

  await page.locator("#proceedToAnalysisBtn").click();
  const matchResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/job-match"));
  const matchResponse = await matchResponsePromise;
  assert.equal(matchResponse.status(), 200, `Job Match failed: ${await matchResponse.text()}`);
  const matchData = await matchResponse.json();
  await page.locator("#switchToAtsBtn").waitFor();
  assert.ok(matchData.overall_score > 0 || matchData.score_withheld, "Job Match returned neither a real score nor an evidence-based withheld result");
  assert.ok(matchData.category_scores && Object.keys(matchData.category_scores).length > 0, "Job Match returned no category assessment data");
  record("Job Match generated role-specific results", `score=${matchData.overall_score ?? "withheld"}; categories=${Object.keys(matchData.category_scores).length}`);

  await page.locator("#switchToAtsBtn").click();
  const atsResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/assessment"));
  const atsResponse = await atsResponsePromise;
  assert.equal(atsResponse.status(), 200, `ATS Readiness failed: ${await atsResponse.text()}`);
  const atsData = await atsResponse.json();
  await page.getByText("ATS Readiness Assessment", { exact: true }).waitFor();
  assert.ok(atsData.overall_score > 0 && atsData.dimension_scores, "ATS Readiness did not return scored dimensions");
  assert.ok(!matchData.dimension_scores && Object.keys(matchData.category_scores).length > 0, "Job Match response incorrectly uses ATS readiness dimensions");
  record("ATS Readiness returned separate format/readability assessment", `score=${atsData.overall_score}; distinct Job Match score=${matchData.overall_score ?? "withheld"}`);

  await page.locator("#launchImprovementStudioBtn").click();
  await page.getByRole("heading", { name: "Targeted Bullet Rewriting" }).waitFor({ timeout: 30000 });
  const ollamaStatus = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/improvement/provider/status`, { credentials: "include" });
    return { status: response.status, ...(await response.json()) };
  }, apiOrigin);
  assert.equal(ollamaStatus.status, 200, "Local AI provider status could not be checked");
  assert.equal(ollamaStatus.provider, "ollama");
  if (ollamaStatus.available) {
    const rewriteResponsePromise = page.waitForResponse((response) =>
      /\/api\/improvement\/[^/]+\/rewrite$/.test(new URL(response.url()).pathname),
      { timeout: 180000 },
    );
    await page.getByRole("button", { name: "Rewrite with Local AI" }).first().click();
    const rewriteResponse = await rewriteResponsePromise;
    assert.equal(rewriteResponse.status(), 200, `Local Ollama rewrite failed: ${await rewriteResponse.text()}`);
    const aiProposal = await rewriteResponse.json();
    assert.equal(aiProposal.is_ai_generated, true, "Rewrite response was not identified as AI generated");
    assert.equal(aiProposal.status, "identified", "AI proposal was accepted without candidate confirmation");
    await page.getByRole("button", { name: "Accept Suggestion", exact: true }).first().click();
    await page.getByRole("button", { name: "Restore Original Statement" }).first().waitFor();
    await page.getByRole("button", { name: "Restore Original Statement" }).first().click();
    record("local Ollama rewrite returned a pending proposal and required explicit candidate acceptance", `model=${aiProposal.ai_model || ollamaStatus.model}`);
  } else {
    await page.getByText(/Local Ollama Offline/).waitFor();
    await page.getByText(/Start Ollama with/).waitFor();
    const firstSuggestion = page.locator("textarea").first();
    const unchangedDraft = await firstSuggestion.inputValue();
    const rewriteResponsePromise = page.waitForResponse((response) =>
      /\/api\/improvement\/[^/]+\/rewrite$/.test(new URL(response.url()).pathname),
    );
    await page.getByRole("button", { name: "Rewrite with Local AI" }).first().click();
    const rewriteResponse = await rewriteResponsePromise;
    assert.equal(rewriteResponse.status(), 503, `Offline local AI should return HTTP 503: ${await rewriteResponse.text()}`);
    const rewriteError = await rewriteResponse.json();
    assert.match(rewriteError.detail, /Local AI provider unavailable/i);
    const inlineRewriteError = page.getByRole("alert").filter({ hasText: /Local AI rewrite unavailable/ });
    await inlineRewriteError.waitFor();
    const inlineErrorText = await inlineRewriteError.innerText();
    assert.match(inlineErrorText, /suggestion is unchanged/i);
    assert.equal(await firstSuggestion.inputValue(), unchangedDraft, "Failed AI rewrite changed the user's draft");
    assert.deepEqual(browserDialogs, [], "Offline rewrite opened a blocking browser dialog");
    record("offline Ollama rewrite failure stays inline, preserves the draft, and leaves heuristic editing available", rewriteError.detail);
  }
  await page.locator("textarea").first().waitFor({ timeout: 30000 });
  const suggestionTextareas = page.locator("textarea");
  const suggestionCount = await suggestionTextareas.count();
  assert.ok(suggestionCount >= 1, "Improvement Studio returned no editable suggestions");
  await suggestionTextareas.first().fill("Architected asynchronous microservices using verified Python and FastAPI experience, reducing API latency by 35%.");
  await page.getByRole("button", { name: "Accept Custom Revision" }).first().click();
  await page.getByRole("button", { name: "Restore Original Statement" }).first().waitFor();
  await page.getByRole("button", { name: "Restore Original Statement" }).first().click();
  await page.getByRole("button", { name: /Accept (Custom Revision|Suggestion)/ }).first().waitFor();
  await page.getByRole("button", { name: "Reject", exact: true }).first().click();
  await page.getByRole("button", { name: "Rejected", exact: true }).first().waitFor();
  record("suggestion edited, explicitly accepted, restored, and rejected", `editable suggestions=${suggestionCount}`);

  await page.locator("#backToAtsButton").click();
  await page.getByText("ATS Readiness Assessment", { exact: true }).waitFor();
  await page.locator("#launchResumeBuilderBtn").click();
  await page.getByText(/Real-time ATS Builder/).waitFor({ timeout: 30000 });
  await page.getByText(/ATS Professional/).first().waitFor();
  const initialBuilder = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/builder`, { credentials: "include" });
    return response.ok ? response.json() : null;
  }, apiOrigin);
  assert.ok(initialBuilder && initialBuilder.template_id === "ats_professional", "Builder did not use the canonical ATS Professional template");
  record("builder initializes the single ATS Professional template", `version=${initialBuilder.version}`);

  await page.locator("#proceedToExportHubBtn").click();
  await page.getByText("Differential Reanalysis", { exact: true }).waitFor();
  await page.getByText("Comparison unavailable", { exact: true }).waitFor();
  const lockedBeforeRevision = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/reanalysis`, { credentials: "include" });
    return response.json();
  }, apiOrigin);
  assert.equal(lockedBeforeRevision.available, false, "Comparison unlocked before a content revision was saved");
  record("differential comparison remains locked until a content revision is saved", lockedBeforeRevision.reason);

  await page.getByRole("button", { name: "Resume Builder" }).click();
  await page.getByText(/Real-time ATS Builder/).waitFor();
  await page.locator("input[placeholder='e.g. Senior Software Architect']").fill("Verified Systems Engineer");
  const saveResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/builder") && response.request().method() === "PUT");
  await page.getByRole("button", { name: "Save Now" }).click();
  const saveResponse = await saveResponsePromise;
  assert.equal(saveResponse.status(), 200, `Builder save failed: ${await saveResponse.text()}`);
  const savedBuilder = await saveResponse.json();
  assert.equal(savedBuilder.template_id, "ats_professional");
  assert.ok(savedBuilder.version > initialBuilder.version, "Builder version did not advance after save");
  record("builder content saved with monotonic version and canonical template", `version=${savedBuilder.version}`);

  await page.reload({ waitUntil: "networkidle", timeout: 90000 });
  await page.getByText(/Real-time ATS Builder/).waitFor({ timeout: 15000 });
  assert.equal(await page.locator("input[placeholder='e.g. Senior Software Architect']").inputValue(), "Verified Systems Engineer", "Builder changes did not restore after browser refresh");
  record("builder changes persist and restore in the browser after refresh");

  // Open a second tab at the same saved version; the backend must reject its stale write clearly.
  const stalePage = await context.newPage();
  await stalePage.goto(webOrigin, { waitUntil: "networkidle", timeout: 90000 });
  await stalePage.getByText(/Real-time ATS Builder/).waitFor({ timeout: 15000 });
  const revisedSavePromise = page.waitForResponse((response) =>
    response.url().endsWith("/api/builder") && response.request().method() === "PUT" && response.status() === 200,
  );
  await page.locator("input[placeholder='e.g. Senior Software Architect']").fill("Verified Systems Engineer Revised");
  const revisedSaveResponse = await revisedSavePromise;
  const revisedBuilder = await revisedSaveResponse.json();
  await page.getByText(`Saved v${revisedBuilder.version}`, { exact: true }).waitFor();
  const staleSavePromise = stalePage.waitForResponse((response) =>
    response.url().endsWith("/api/builder") && response.request().method() === "PUT" && response.status() === 409,
  );
  await stalePage.locator("input[placeholder='e.g. Senior Software Architect']").fill("Stale Tab Candidate");
  await staleSavePromise;
  await stalePage.getByText(/Version mismatch: The document was updated in another session/).waitFor();
  record("stale builder auto-save is rejected with a clear conflict message", `server version=${revisedBuilder.version}`);
  await stalePage.close();

  const revisedComparison = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/reanalysis`, { credentials: "include" });
    return response.json();
  }, apiOrigin);
  assert.equal(revisedComparison.available, true, `Differential comparison did not unlock after saved revision: ${revisedComparison.reason}`);
  assert.ok(revisedComparison.ats && Number.isFinite(revisedComparison.ats.baseline_score) && Number.isFinite(revisedComparison.ats.revised_score), "Differential comparison has no actual score values");
  record("differential comparison reports actual baseline and revision scores", `baseline=${revisedComparison.ats.baseline_score}; revised=${revisedComparison.ats.revised_score}; delta=${revisedComparison.ats.delta}`);

  await page.locator("#proceedToExportHubBtn").click();
  await page.getByRole("heading", { name: /Multi-Format Export/ }).waitFor({ timeout: 30000 });
  await page.getByText("Differential Reanalysis", { exact: true }).waitFor();
  await page.getByText("Saved baseline", { exact: true }).waitFor();
  const pdfFile = await makeDownload(page, page.locator("#downloadPdfResumeBtn"), "resume.pdf");
  const docxFile = await makeDownload(page, page.locator("#downloadDocxResumeBtn"), "resume.docx");
  const diagnosticFile = await makeDownload(page, page.locator("#downloadAuditReportBtn"), "diagnostic-report.pdf");
  record("PDF, DOCX, and diagnostic report download from the browser");

  const inspectCode = String.raw`
import json, pathlib, sys
import pymupdf as fitz
import docx
out = pathlib.Path(sys.argv[1])
expected_builder_version = int(sys.argv[2])
expected_ats_score = float(sys.argv[3])
expected_job_match_score = float(sys.argv[4])
pdf = fitz.open(out / "resume.pdf")
pdf_text = "\n".join(page.get_text() for page in pdf)
png = out / "resume-page-1.png"
pdf[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(png)
word = docx.Document(out / "resume.docx")
docx_text = "\n".join(p.text for p in word.paragraphs)
report = fitz.open(out / "diagnostic-report.pdf")
report_text = "\n".join(page.get_text() for page in report)
assert pdf.page_count >= 1 and "Samantha Reed Verified" in pdf_text and "Verified Systems Engineer Revised" in pdf_text
assert "Lead Backend Engineer" in pdf_text and "Nexus Systems" in pdf_text and "Architected async microservices" in pdf_text
assert "samantha.reed@synthetic-domain.com" in pdf_text and "Pacific Crest University" in pdf_text
assert "2014" in pdf_text and "2018" in pdf_text and "Pacific Crest University (2014" not in pdf_text
assert "Samantha Reed Verified" in docx_text and "Verified Systems Engineer Revised" in docx_text
assert "Lead Backend Engineer" in docx_text and "Nexus Systems" in docx_text and "Architected async microservices" in docx_text
assert "Pacific Crest University (2014" not in docx_text
assert "ATS Professional" in pdf_text or "Verified Systems Engineer Revised" in pdf_text
assert "Diagnostic Resume Improvement Report" in report_text
assert "Samantha Reed Verified" in report_text
assert f"Document Version: v{expected_builder_version}" in report_text
assert "Assessment evaluated an earlier resume snapshot" in report_text
assert "ATS Readiness" in report_text or "MECHANICAL & STRUCTURAL ATS READINESS" in report_text.upper()
assert f"{expected_ats_score:.1f}" in report_text, "Diagnostic report does not include the actual ATS score returned in this browser session"
assert f"Semantic Qualification Match: {round(expected_job_match_score)}/100" in report_text, "Diagnostic report does not include the actual Job Match score returned in this browser session"
print(json.dumps({"pdf_pages": pdf.page_count, "pdf_text": pdf_text, "docx_paragraph_count": len(word.paragraphs), "docx_text": docx_text, "report_pages": report.page_count, "document_version": expected_builder_version, "ats_score": expected_ats_score, "job_match_score": expected_job_match_score, "historical_assessment_warning": "Assessment evaluated an earlier resume snapshot" in report_text, "report_text": report_text, "rendered_page": str(png)}))
`;
  const inspection = JSON.parse(runPython(inspectCode, [outputDir, String(revisedBuilder.version), String(atsData.overall_score), String(matchData.overall_score)]));
  record("exported PDF opens, has selectable expected text, and renders for visual review", `pages=${inspection.pdf_pages}; preview=${inspection.rendered_page}`);
  record("exported DOCX opens and preserves corrected resume content", `paragraphs=${inspection.docx_paragraph_count}`);
  record("diagnostic report includes actual ATS and Job Match scores, current version, and historical assessment warning", `ATS=${inspection.ats_score}; Job Match=${inspection.job_match_score}; report version=v${inspection.document_version}; historical=${inspection.historical_assessment_warning}; pages=${inspection.report_pages}`);
  fs.writeFileSync(path.join(outputDir, "document-inspection.json"), JSON.stringify(inspection, null, 2));

  const secondContext = await browser.newContext({ acceptDownloads: true });
  const secondPage = await secondContext.newPage();
  const secondSessionPromise = secondPage.waitForResponse((response) =>
    response.url().endsWith("/api/session") && response.request().method() === "POST",
  { timeout: 30000 });
  await secondPage.goto(webOrigin, { waitUntil: "networkidle", timeout: 90000 });
  await secondPage.getByRole("heading", { name: /Your experience\./ }).waitFor();
  const secondSessionResponse = await secondSessionPromise;
  const secondSession = await secondSessionResponse.json();
  assert.notEqual(secondSession.id, firstSession.id, "A new browser context reused the first anonymous session");
  const isolatedResume = await secondPage.evaluate(async (api) => {
    const response = await fetch(`${api}/api/resume`, { credentials: "include" });
    return { status: response.status, body: await response.json().catch(() => ({})) };
  }, apiOrigin);
  assert.ok([401, 404].includes(isolatedResume.status), `Second session accessed the first resume (HTTP ${isolatedResume.status})`);
  await secondPage.locator("#resumeFileInput").setInputFiles(path.join(fixtureDir, "synthetic_resume.docx"));
  const docxUploadPromise = secondPage.waitForResponse((response) => response.url().endsWith("/api/resume/upload"));
  await secondPage.locator("#analyzeResumeBtn").click();
  const docxUploadResponse = await docxUploadPromise;
  assert.equal(docxUploadResponse.status(), 201, `DOCX upload failed: ${await docxUploadResponse.text()}`);
  const docxParsed = await docxUploadResponse.json();
  assert.equal(docxParsed.structured_data.contact.name, "Elena Rostova");
  assert.equal(docxParsed.structured_data.contact.email, "elena.rostova@synthetic-domain.com");
  assert.ok(docxParsed.structured_data.experience.some((entry) => /Stratum Cloud Labs/i.test(entry)), "DOCX experience extraction is missing Stratum Cloud Labs");
  assert.ok(docxParsed.structured_data.skills.some((entry) => /Python/i.test(entry)), "DOCX skill extraction is missing Python");
  assert.ok(docxParsed.structured_data.education.some((entry) => /Horizon Institute/i.test(entry)), "DOCX education extraction is missing Horizon Institute");
  record("second anonymous session is isolated and DOCX upload parses synthetic profile", `session=${secondSession.id}; experience/skills/education verified`);
  await secondContext.close();

  const expireCode = String.raw`
import sqlite3, sys
connection = sqlite3.connect(sys.argv[1])
connection.execute("UPDATE anonymous_sessions SET expires_at = datetime('now', '-1 hour')")
connection.commit()
assert connection.execute("SELECT COUNT(*) FROM anonymous_sessions WHERE expires_at < CURRENT_TIMESTAMP").fetchone()[0] > 0
connection.close()
`;
  runPython(expireCode, [dbPath]);
  const expiredCheck = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/export/status`, { credentials: "include" });
    return { status: response.status, body: await response.json().catch(() => ({})) };
  }, apiOrigin);
  assert.equal(expiredCheck.status, 401, `Expired session was not rejected (HTTP ${expiredCheck.status})`);
  assertIncludes(JSON.stringify(expiredCheck.body), "expired", "Expired session error was not clear");
  await page.getByRole("button", { name: "Refresh comparison" }).click();
  await page.getByRole("alert").filter({ hasText: /expired/i }).waitFor({ timeout: 10000 });
  record("expired session returns HTTP 401 and a visible clear error");

  await stopProcess(backend);
  const failureResponse = await page.evaluate(async (api) => {
    const response = await fetch(`${api}/api/reanalysis`, { credentials: "include" }).catch(() => null);
    return response ? response.status : 0;
  }, apiOrigin);
  assert.equal(failureResponse, 0, "Backend did not stop for outage UX check");
  await page.getByRole("button", { name: "Refresh comparison" }).click();
  await page.getByRole("alert").filter({ hasText: /Backend connection failed.*Differential comparison is unavailable/i }).waitFor({ timeout: 10000 });
  record("backend outage produces a visible retryable comparison error");

  assert.deepEqual(consoleErrors, [], `Browser reported uncaught page errors: ${consoleErrors.join(" | ")}`);
  record("no uncaught browser page errors");
  const evidence = {
    generated_at: new Date().toISOString(),
    browser: path.basename(browserExe),
    frontend_origin: webOrigin,
    api_origin: apiOrigin,
    isolated_database: dbPath,
    results,
    exported_files: [pdfFile, docxFile, diagnosticFile, inspection.rendered_page],
    ollama_status: ollamaStatus,
    console_errors: consoleErrors,
  };
  fs.writeFileSync(path.join(outputDir, "browser-evidence.json"), JSON.stringify(evidence, null, 2));
  const priorFailurePath = path.join(outputDir, "browser-evidence-failure.json");
  if (fs.existsSync(priorFailurePath)) fs.rmSync(priorFailurePath, { force: true });
  console.log(`EVIDENCE ${path.join(outputDir, "browser-evidence.json")}`);

  await context.close();
  await browser.close();
}

try {
  await main();
  console.log(`\nLaunch gate browser E2E: ${results.length} checks passed.`);
} catch (error) {
  if (activePage && !activePage.isClosed()) {
    await activePage.screenshot({ path: path.join(outputDir, "browser-evidence-failure.png"), fullPage: true }).catch(() => {});
  }
  const failure = {
    generated_at: new Date().toISOString(),
    results,
    error: error instanceof Error ? `${error.stack}\n${error.message}` : String(error),
    process_output: processes.map((child) => ({ pid: child.pid, tail: child.outputTail })),
  };
  fs.writeFileSync(path.join(outputDir, "browser-evidence-failure.json"), JSON.stringify(failure, null, 2));
  console.error(error);
  process.exitCode = 1;
} finally {
  await Promise.all([stopProcess(frontend), stopProcess(devFrontend), stopProcess(backend)]);
  if (browser) await browser.close().catch(() => {});
  const tempParent = path.resolve(os.tmpdir());
  const resolvedTempRoot = path.resolve(tempRoot);
  if (resolvedTempRoot.startsWith(`${tempParent}${path.sep}`) && path.basename(resolvedTempRoot).startsWith("resumind-launch-gate-")) {
    try {
      fs.rmSync(resolvedTempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 500 });
    } catch (error) {
      console.error(`Temporary test directory cleanup failed for ${resolvedTempRoot}: ${error}`);
      process.exitCode = 1;
    }
  }
  const resolvedFrontend = path.resolve(frontendDir);
  const resolvedNextDistDir = path.resolve(nextDistDir);
  if (resolvedNextDistDir.startsWith(`${resolvedFrontend}${path.sep}`) && path.basename(resolvedNextDistDir).startsWith(".next-launch-gate-")) {
    try {
      fs.rmSync(resolvedNextDistDir, { recursive: true, force: true, maxRetries: 10, retryDelay: 500 });
    } catch (error) {
      console.error(`Temporary Next.js test output cleanup failed for ${resolvedNextDistDir}: ${error}`);
      process.exitCode = 1;
    }
  }
  const resolvedNextTsconfig = path.resolve(nextTsconfigPath);
  if (resolvedNextTsconfig.startsWith(`${resolvedFrontend}${path.sep}`) && path.basename(resolvedNextTsconfig).startsWith(".tsconfig-launch-gate-") && fs.existsSync(resolvedNextTsconfig)) {
    try {
      fs.rmSync(resolvedNextTsconfig, { force: true });
    } catch (error) {
      console.error(`Temporary Next.js test TypeScript config cleanup failed for ${resolvedNextTsconfig}: ${error}`);
      process.exitCode = 1;
    }
  }
}
