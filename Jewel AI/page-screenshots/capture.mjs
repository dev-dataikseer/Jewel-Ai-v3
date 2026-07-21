/**
 * Jewel AI — full-page screenshot crawler
 *
 * Usage:
 *   node capture.mjs --headless --base-url=http://127.0.0.1:5173
 *   node capture.mjs --headed --email=admin@jewelai.com --password=changeme
 */

import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function arg(name, fallback = undefined) {
  const hit = process.argv.find((a) => a === `--${name}` || a.startsWith(`--${name}=`));
  if (!hit) return fallback;
  if (hit === `--${name}`) return true;
  return hit.slice(name.length + 3);
}

function parseArgs() {
  const headedFlag = process.argv.includes("--headed");
  const headlessFlag = process.argv.includes("--headless");
  const headless = headedFlag ? false : headlessFlag ? true : true;
  const viewportRaw = String(arg("viewport", "1440x900"));
  const [vw, vh] = viewportRaw.split(/[xX]/).map((n) => Number(n) || 0);

  return {
    baseUrl: String(arg("base-url", process.env.BASE_URL || "http://127.0.0.1:5173")).replace(
      /\/$/,
      "",
    ),
    headless,
    email: String(arg("email", process.env.EMAIL || "admin@jewelai.com")),
    password: String(arg("password", process.env.PASSWORD || "changeme")),
    shareToken: arg("share-token", process.env.SHARE_TOKEN || "") || "",
    outRoot: path.resolve(
      __dirname,
      String(arg("out", process.env.OUT_DIR || path.join(__dirname, "output"))),
    ),
    delayMs: Number(arg("delay", process.env.DELAY_MS || "1200")) || 1200,
    viewport: { width: vw || 1440, height: vh || 900 },
  };
}

function buildPages(shareToken) {
  const pages = [
    { name: "01-login", path: "/login", auth: false },
    { name: "02-studio", path: "/", auth: true },
    { name: "03-history", path: "/history", auth: true },
    { name: "04-admin", path: "/admin", auth: true },
  ];
  if (shareToken) {
    pages.push({ name: "05-share", path: `/share/${shareToken}`, auth: false });
  }
  return pages;
}

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

async function waitSettle(page, delayMs) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 20_000 });
  } catch {
    /* ignore */
  }
  await page.waitForTimeout(delayMs);
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
  });
}

async function isAuthenticatedUi(page) {
  // Header brand / logout / Studio nav — any means session is live
  const markers = [
    page.getByRole("link", { name: /Jewel AI Studio/i }),
    page.getByRole("button", { name: /log ?out|sign out/i }),
    page.getByRole("navigation").getByText(/Studio/i),
    page.locator("text=Workflows"),
    page.locator("text=Generate"),
  ];
  for (const loc of markers) {
    if (await loc.first().isVisible().catch(() => false)) return true;
  }
  return !page.url().includes("/login");
}

/**
 * Reliable login for cookie + in-memory access token SPA:
 * 1) POST /api/auth/login (via Vite proxy) → cookies + access_token
 * 2) addInitScript so EVERY navigation re-seeds localStorage before app JS runs
 *    (the SPA migrates localStorage → memory then clears it; without re-seed,
 *    the next full page load is logged out again)
 * 3) Open Studio and wait for authenticated chrome
 */
async function establishSession(page, context, baseUrl, email, password, delayMs) {
  const candidates = [
    { email, password },
    { email: "admin@jewelai.com", password: "changeme" },
    { email: "studio@jewelai.com", password: "studio123" },
  ];
  const seen = new Set();
  const tries = candidates.filter((c) => {
    const k = `${c.email}|${c.password}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  let lastErr = "";
  for (const cred of tries) {
    console.log(`  … trying API login as ${cred.email}`);
    try {
      const res = await context.request.post(`${baseUrl}/api/auth/login`, {
        data: { email: cred.email, password: cred.password },
        headers: { "Content-Type": "application/json" },
        timeout: 30_000,
      });
      const status = res.status();
      const body = await res.json().catch(() => ({}));
      if (status === 401 && String(body.detail || "").toLowerCase().includes("mfa")) {
        console.warn(
          "  ! MFA required for this account — use a non-MFA user or disable MFA.",
        );
        lastErr = "MFA required";
        continue;
      }
      if (!res.ok()) {
        lastErr = `HTTP ${status}: ${JSON.stringify(body).slice(0, 200)}`;
        console.warn(`  ! ${lastErr}`);
        continue;
      }
      const access = body.access_token;
      if (!access) {
        lastErr = "No access_token in login response";
        continue;
      }

      // Re-seed before every document load (SPA clears localStorage after migrate)
      await context.addInitScript((token) => {
        try {
          localStorage.setItem("jewel_access_token", token);
        } catch {
          /* ignore */
        }
      }, access);

      await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
      await waitSettle(page, delayMs);

      const deadline = Date.now() + 25_000;
      while (Date.now() < deadline) {
        if (await isAuthenticatedUi(page)) {
          console.log(`  ✓ Session ready (${cred.email})`);
          return access;
        }
        await page.waitForTimeout(500);
      }
      lastErr = "UI never showed authenticated chrome";
    } catch (err) {
      lastErr = err instanceof Error ? err.message : String(err);
      console.warn(`  ! ${lastErr}`);
    }
  }
  console.error(`  ✗ Login failed — ${lastErr}`);
  console.error("    Tip: edit EMAIL/PASSWORD in Capture-Screenshots.bat");
  return null;
}

async function fullPageShot(page, filePath) {
  await page.screenshot({
    path: filePath,
    fullPage: true,
    animations: "disabled",
  });
}

async function captureRoute(page, baseUrl, route, runDir, outRoot, delayMs) {
  const url = `${baseUrl}${route.path}`;
  console.log(`→ ${route.name}  ${url}`);
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await waitSettle(page, delayMs);

  if (route.auth && page.url().includes("/login")) {
    throw new Error("Session lost — redirected to /login");
  }

  const file = path.join(runDir, `${route.name}.png`);
  await fullPageShot(page, file);
  const rel = path.relative(outRoot, file);
  console.log(`  ✓ ${rel}`);
  return { name: route.name, path: route.path, file: rel, ok: true };
}

async function main() {
  const cfg = parseArgs();
  const runDir = path.join(cfg.outRoot, stamp());
  fs.mkdirSync(runDir, { recursive: true });

  const manifest = {
    startedAt: new Date().toISOString(),
    baseUrl: cfg.baseUrl,
    headless: cfg.headless,
    viewport: cfg.viewport,
    shots: [],
  };

  console.log(`Jewel page screenshots`);
  console.log(`  base:     ${cfg.baseUrl}`);
  console.log(`  mode:     ${cfg.headless ? "headless (background)" : "headed (visible)"}`);
  console.log(`  output:   ${runDir}`);
  console.log("");

  const browser = await chromium.launch({
    headless: cfg.headless,
    args: ["--disable-dev-shm-usage"],
  });
  const context = await browser.newContext({
    viewport: cfg.viewport,
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(45_000);

  const pages = buildPages(cfg.shareToken);
  let accessToken = null;

  try {
    // 1) Login page (logged-out)
    const loginPage = pages.find((p) => p.path === "/login");
    if (loginPage) {
      try {
        const shot = await captureRoute(page, cfg.baseUrl, loginPage, runDir, cfg.outRoot, cfg.delayMs);
        manifest.shots.push(shot);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        manifest.shots.push({ name: loginPage.name, path: loginPage.path, ok: false, error: msg });
        console.error(`  ✗ ${loginPage.name}: ${msg}`);
      }
    }

    // 2) Establish session once
    console.log("→ Establishing session…");
    accessToken = await establishSession(
      page,
      context,
      cfg.baseUrl,
      cfg.email,
      cfg.password,
      cfg.delayMs,
    );
    if (!accessToken) {
      console.error("Stopping — authenticated pages cannot be captured.");
    }

    // 3) Auth pages
    if (accessToken) {
      for (const route of pages.filter((p) => p.auth)) {
        try {
          const shot = await captureRoute(page, cfg.baseUrl, route, runDir, cfg.outRoot, cfg.delayMs);
          manifest.shots.push(shot);
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          manifest.shots.push({ name: route.name, path: route.path, ok: false, error: msg });
          console.error(`  ✗ ${route.name}: ${msg}`);
          console.log("  … re-establishing session");
          accessToken = await establishSession(
            page,
            context,
            cfg.baseUrl,
            cfg.email,
            cfg.password,
            cfg.delayMs,
          );
          if (!accessToken) break;
          try {
            manifest.shots.pop();
            const shot = await captureRoute(page, cfg.baseUrl, route, runDir, cfg.outRoot, cfg.delayMs);
            manifest.shots.push(shot);
          } catch (err2) {
            const msg2 = err2 instanceof Error ? err2.message : String(err2);
            console.error(`  ✗ ${route.name} retry: ${msg2}`);
          }
        }
      }
    }

    // 4) Optional public share
    const share = pages.find((p) => p.path.startsWith("/share/"));
    if (share) {
      try {
        const shot = await captureRoute(page, cfg.baseUrl, share, runDir, cfg.outRoot, cfg.delayMs);
        manifest.shots.push(shot);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        manifest.shots.push({ name: share.name, path: share.path, ok: false, error: msg });
        console.error(`  ✗ ${share.name}: ${msg}`);
      }
    }

    // 5) Admin tabs
    if (accessToken && (await isAuthenticatedUi(page))) {
      await page.goto(`${cfg.baseUrl}/admin`, { waitUntil: "domcontentloaded" });
      await waitSettle(page, cfg.delayMs);
      if (!page.url().includes("/login")) {
        const adminTabs = [
          "Overview",
          "Monitoring",
          "Providers",
          "Prompts",
          "Users",
        ];
        for (const tab of adminTabs) {
          const slug = tab.toLowerCase().replace(/\s+/g, "-");
          const name = `04-admin-${slug}`;
          console.log(`→ ${name}`);
          try {
            const btn = page.getByRole("button", { name: tab }).first();
            if (await btn.isVisible().catch(() => false)) {
              await btn.click();
              await waitSettle(page, cfg.delayMs);
            }
            const file = path.join(runDir, `${name}.png`);
            await fullPageShot(page, file);
            const rel = path.relative(cfg.outRoot, file);
            manifest.shots.push({ name, path: `/admin#${slug}`, file: rel, ok: true });
            console.log(`  ✓ ${rel}`);
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            manifest.shots.push({ name, ok: false, error: msg });
            console.error(`  ✗ ${name}: ${msg}`);
          }
        }
      }
    }
  } finally {
    await browser.close();
  }

  manifest.finishedAt = new Date().toISOString();
  const manifestPath = path.join(runDir, "manifest.json");
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  const ok = manifest.shots.filter((s) => s.ok).length;
  console.log("");
  console.log(`Done. ${ok}/${manifest.shots.length} shots`);
  console.log(`Manifest: ${manifestPath}`);
  process.exit(ok > 0 && ok === manifest.shots.length ? 0 : ok > 0 ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
