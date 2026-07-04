import { test, expect } from '@playwright/test'

/**
 * FinSight — E2E Happy-Path Test
 *
 * Full user journey:
 *   Login → Dashboard → MSME Health Card → Data Source Explorer → Ecosystem
 *
 * Requires:
 *   - Frontend: npm run dev (http://localhost:5173)
 *   - Backend:  uvicorn app.main:app --reload (http://localhost:8000)
 */

const DEMO_USERNAME = 'bank_officer_sharma'
const DEMO_ROLE = 'bank_officer'

test.describe('FinSight happy path', () => {
  test.beforeEach(async ({ page }) => {
    // Start from a clean state
    await page.context().clearCookies()
    await page.evaluate(() => localStorage.clear())
  })

  test('full user journey: login → dashboard → health card → data explorer → ecosystem', async ({
    page,
  }) => {
    // ── 1. Visit app root — should redirect to /login ────────────────────────
    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByText('FinSight')).toBeVisible()
    await expect(page.getByText('MSME Credit Intelligence Platform')).toBeVisible()

    // ── 2. Login with demo preset ────────────────────────────────────────────
    await page.locator(`#preset-${DEMO_ROLE}`).click()
    await expect(page.locator('#login-username')).toHaveValue(DEMO_USERNAME)
    await page.locator('#btn-login').click()

    // Should redirect to /dashboard after login
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })
    await expect(page.getByText('Portfolio Dashboard')).toBeVisible()

    // ── 3. Dashboard — verify KPI strip and MSME table ───────────────────────
    await expect(page.locator('.kpi-strip')).toBeVisible()
    await expect(page.locator('#msme-table')).toBeVisible()

    // Wait for at least one MSME row to appear
    const msmeRows = page.locator('.msme-row')
    await expect(msmeRows.first()).toBeVisible({ timeout: 15_000 })

    // ── 4. Click first MSME row → Health Card ────────────────────────────────
    const firstRow = msmeRows.first()
    const msmeName = await firstRow.locator('.msme-row__name').textContent()
    await firstRow.click()

    await expect(page).toHaveURL(/\/msme\/[^/]+$/, { timeout: 15_000 })

    // Profile header should show the business name
    await expect(page.locator('.profile-header__name')).toContainText(
      msmeName ?? '',
      { timeout: 15_000 },
    )

    // ── 5. Health Card — verify charts and score ─────────────────────────────
    // Consent may or may not be present; if consent gate, grant it
    const consentGate = page.locator('.consent-gate')
    if (await consentGate.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await page.locator('#btn-grant-consent').click()
      await expect(consentGate).not.toBeVisible({ timeout: 10_000 })
    }

    // Wait for score to appear or check for score band
    await expect(page.locator('.score-band')).toBeVisible({ timeout: 15_000 })

    // Chart tabs should be visible
    await expect(page.locator('#tab-radar')).toBeVisible()
    await expect(page.locator('#tab-gauge')).toBeVisible()
    await expect(page.locator('#tab-shap')).toBeVisible()

    // Switch to gauge tab
    await page.locator('#tab-gauge').click()
    await expect(page.locator('.chart-wrap--gauge')).toBeVisible()

    // Switch to SHAP tab
    await page.locator('#tab-shap').click()
    await expect(page.getByText("Why This Score?")).toBeVisible()

    // ── 6. Navigate to Data Source Explorer ─────────────────────────────────
    await page.locator('#btn-data-sources').click()
    await expect(page).toHaveURL(/\/msme\/[^/]+\/data/)
    await expect(page.getByText('Data Source Explorer')).toBeVisible()

    // Verify source cards are visible
    await expect(page.locator('.source-grid')).toBeVisible()
    const sourceCards = page.locator('.source-card')
    await expect(sourceCards).toHaveCount(6, { timeout: 10_000 })

    // ── 7. Navigate to Ecosystem page via top nav ────────────────────────────
    await page.locator('#nav-ecosystem').click()
    await expect(page).toHaveURL(/\/ecosystem/)
    await expect(page.getByText('Ecosystem Status')).toBeVisible()

    // Connector cards should be visible
    await expect(
      page.locator('#connector-uli-unified-lending-interface'),
    ).toBeVisible({ timeout: 10_000 })
    await expect(
      page.locator('#connector-ocen-open-credit-enablement-network'),
    ).toBeVisible({ timeout: 10_000 })

    // ── 8. Logout ────────────────────────────────────────────────────────────
    await page.locator('#btn-logout').click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByText('Sign in to FinSight')).toBeVisible()
  })

  test('search filter on dashboard narrows MSME rows', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.locator(`#preset-${DEMO_ROLE}`).click()
    await page.locator('#btn-login').click()
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })

    // Wait for rows
    await expect(page.locator('.msme-row').first()).toBeVisible({ timeout: 15_000 })
    const totalRows = await page.locator('.msme-row').count()

    // Type a partial name that should narrow results
    await page.locator('#search-msme').fill('ZXQWERTY_NONEXISTENT_9999')
    await expect(page.locator('.table-empty')).toBeVisible()

    // Clear search — rows should restore
    await page.locator('#search-msme').clear()
    await expect(page.locator('.msme-row')).toHaveCount(totalRows)
  })
})
