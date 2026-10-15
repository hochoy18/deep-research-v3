# ADR 0007: Tailwind v4 CSS-first 配置

- Status: Accepted
- Date: 2026-10-15
- Deciders: @cai.he, @hochoy

## Context

deep-research v3 的前端使用 Next.js 16 (App Router) 构建，UI 层需要原子化 CSS 方案。
早期团队习惯使用 Tailwind v3，并通过 `tailwind.config.ts` 的 JS 配置方式扩展
theme、注册 plugin、配置 content 路径。但 Tailwind v4 已于 2026 年进入稳定版，引入了
全新的 CSS-first 配置范式：

- 通过 `@import "tailwindcss"` 替代旧版 `@tailwind base/components/utilities` 三段指令；
- 通过 `@theme` 在 CSS 文件内直接声明 design token（如颜色、字号、间距）；
- 通过 `@source` 显式声明需扫描的文件路径，不再依赖配置文件；
- 内置 `lightningcss` 引擎，构建速度相比 v3 提升 3-10 倍；
- 自动支持 `@variant dark`、`@layer` 等现代特性。

我们需要决定采用哪一代 Tailwind，并明确配置方式的取舍。

### 方案 A1: 沿用 Tailwind v3 + `tailwind.config.ts`

延续团队熟悉模式：JS 配置、PostCSS plugin、content glob 扫描。

### 方案 A2: 升级到 Tailwind v4 + CSS-first（`@import` + `@theme`）

放弃 JS 配置文件，把 theme、plugin 注册全部内联到 CSS。

## Decision

**采用 Tailwind v4 CSS-first 配置。** 项目根目录不再创建 `tailwind.config.ts`，
仅保留 `app/globals.css` 一个入口样式文件，结构为 `@import "tailwindcss"` →
`@theme { ... }` → `@layer components { ... }`。

所有 design token（颜色、字号、间距、断点）直接在 `@theme` 块中以 CSS custom
property 形式声明，例如 `--color-brand: oklch(...)`。需要在 TypeScript 中读取
token 时，通过 `getComputedStyle(document.documentElement).getPropertyValue('--color-brand')`
获取，避免引入额外构建步骤。

PostCSS pipeline 简化为仅使用 `@tailwindcss/postcss`（v4 官方包），不再引入
`autoprefixer`、`postcss-nested` 等 v3 时代必需的 plugin。

## Consequences

正面：

- 配置文件数量从 2 个（`tailwind.config.ts` + `postcss.config.js`）减少到 1 个
  CSS 文件，认知负担显著降低；
- `lightningcss` 构建速度快，冷启动在本地从 v3 的 ~800ms 降至 ~120ms；
- 与 Next.js 16 的 Turbopack 兼容路径更短，避免 v3 + Turbopack 的已知警告；
- CSS-first 让设计 token 可在 Figma、Storybook、Markdown 中以同一份 source of truth 引用。

负面 / 约束：

- 部分老 plugin（如 `@tailwindcss/typography`、`@tailwindcss/forms`）需升级到 v4
  兼容版本，否则在 `@theme` 中无法生效；
- IDE IntelliSense 在 `@theme` 块内的 CSS custom property 自动补全依赖编辑器版本，
  当前确认 VS Code 1.95+ + Tailwind IntelliSense 插件 0.10.4+ 可用；
- 升级不可逆：v4 与 v3 配置互不兼容，未来若需回退需重构整个 token 系统。

## Alternatives

- **保持 v3**：风险最低但放弃性能与生态红利；预计 2027 年后社区主版本升级压力变大。
- **CSS-in-JS（vanilla-extract / styled-components）**：与 RSC、Server Components 的
  兼容性弱于 Tailwind v4 的 utility-first + static extraction，pass。
- **纯手写 CSS modules**：维护成本随组件数快速上升，不适合快速迭代，pass。