import { expect, type Page } from "@playwright/test";

export class AppShell {
  constructor(private readonly page: Page) {}

  async openDataSources() {
    await this.page.getByRole("button", { name: "数据源管理", exact: true }).click();
    await expect(
      this.page.getByRole("heading", { name: "数据源管理", exact: true, level: 1 }),
    ).toBeVisible();
  }

  async openChatBI() {
    await this.page.getByRole("button", { name: "智能问数", exact: true }).click();
    await this.page.getByRole("button", { name: "ChatBI", exact: true }).click();
    await expect(
      this.page.getByRole("heading", { name: "从问题到可复用报表", level: 1 }),
    ).toBeVisible();
  }
}
