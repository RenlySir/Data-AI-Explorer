import { expect, type Page } from "@playwright/test";

export class LoginPage {
  constructor(private readonly page: Page) {}

  async open() {
    await this.page.goto("/");
    await expect(this.page.getByRole("heading", { name: "登录工作台" })).toBeVisible();
  }

  async login(email = "admin@acme.com", password = "12345678") {
    await this.page.getByLabel("企业账号").fill(email);
    await this.page.getByLabel("密码").fill(password);
    await this.page.getByRole("button", { name: "登录工作台" }).click();
    await expect(this.page.getByRole("navigation", { name: "产品导航" })).toBeVisible();
  }
}
