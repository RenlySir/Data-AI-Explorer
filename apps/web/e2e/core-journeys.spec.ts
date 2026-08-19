import { expect, test } from "@playwright/test";

import { AppShell } from "./pages/app-shell";
import { LoginPage } from "./pages/login-page";

test("首次登录进入模型接入引导，并可转到数据源管理", async ({ page }) => {
  const login = new LoginPage(page);
  const app = new AppShell(page);

  await login.open();
  await login.login();

  await expect(page.getByRole("heading", { name: "先连接一个大模型", level: 1 })).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("aegis_session_id")))
    .toMatch(/^sess-/);

  await app.openDataSources();
  await expect(page.getByRole("button", { name: "添加数据源" })).toBeVisible();
  await expect(page.getByPlaceholder("搜索名称、数据库或主机")).toBeVisible();
});

test("用户可按侧栏层级进入 ChatBI，并看到数据源选择和只读执行门禁", async ({ page }) => {
  const login = new LoginPage(page);
  const app = new AppShell(page);

  await login.open();
  await login.login();
  await app.openChatBI();

  await expect(page.getByText("智能问数 · ChatBI", { exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: /^数据源/ })).toBeVisible();
  await expect(page.getByPlaceholder("输入你的业务问题，例如：本月各区域 GMV 占比")).toBeVisible();
  await expect(page.getByRole("button", { name: "发送问题" })).toBeDisabled();
  await expect(page.getByText("只读执行 · 可追溯", { exact: true })).toBeVisible();
});
