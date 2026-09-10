"""Framework-specific frontend project generators."""

from __future__ import annotations

import html
import json


class FrontendFrameworkProjectsMixin:
    def generate_react_vite_project(self, ui_contract: dict) -> dict[str, str]:
        """生成 React + Vite + TypeScript 实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-react"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        primary = palette.get("primary", "#0f7cfa")
        accent = palette.get("accent", "#f65f22")
        background = palette.get("background", "#f5f8ff")
        text = palette.get("text", "#172133")
        border = palette.get("border", "#dfe7f3")
        heading_font = typography.get("heading", "Manrope")
        body_font = typography.get("body", "Inter")
        anti_cliches = json.dumps(direction.get("anti_cliches", []), ensure_ascii=False, indent=2)
        tweak_axes = json.dumps(direction.get("tweak_axes", []), ensure_ascii=False, indent=2)

        pkg = output_dir / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-frontend",
                    "private": True,
                    "version": "0.1.0",
                    "type": "module",
                    "scripts": {
                        "dev": "vite",
                        "build": "tsc -b && vite build",
                        "preview": "vite preview",
                    },
                    "dependencies": {
                        "react": "^19.0.0",
                        "react-dom": "^19.0.0",
                    },
                    "devDependencies": {
                        "@types/react": "^19.0.0",
                        "@types/react-dom": "^19.0.0",
                        "@vitejs/plugin-react": "^5.0.0",
                        "typescript": "^5.7.0",
                        "vite": "^6.0.0",
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(pkg)

        vite_config = output_dir / "vite.config.ts"
        vite_config.write_text(
            (
                'import { defineConfig } from "vite";\n'
                'import react from "@vitejs/plugin-react";\n\n'
                "export default defineConfig({\n"
                "  plugins: [react()],\n"
                "  server: {\n"
                "    port: 3000,\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vite.config.ts"] = str(vite_config)

        tsconfig = output_dir / "tsconfig.json"
        tsconfig.write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2020",
                        "useDefineForClassFields": True,
                        "lib": ["ES2020", "DOM", "DOM.Iterable"],
                        "module": "ESNext",
                        "skipLibCheck": True,
                        "moduleResolution": "Bundler",
                        "allowImportingTsExtensions": True,
                        "resolveJsonModule": True,
                        "isolatedModules": True,
                        "noEmit": True,
                        "jsx": "react-jsx",
                        "strict": True,
                    },
                    "include": ["src"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["tsconfig.json"] = str(tsconfig)

        index_html = output_dir / "index.html"
        index_html.write_text(
            (
                "<!doctype html>\n"
                '<html lang="zh-CN">\n'
                "  <head>\n"
                '    <meta charset="UTF-8" />\n'
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
                f"    <title>{html.escape(self.name)} · React Blueprint</title>\n"
                '    <link rel="preconnect" href="https://fonts.googleapis.com" />\n'
                '    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
                f'    <link href="{self._build_google_fonts_url(typography)}" rel="stylesheet" />\n'
                "  </head>\n"
                "  <body>\n"
                '    <div id="root"></div>\n'
                '    <script type="module" src="/src/main.tsx"></script>\n'
                "  </body>\n"
                "</html>\n"
            ),
            encoding="utf-8",
        )
        files["index.html"] = str(index_html)

        main_tsx = src_dir / "main.tsx"
        main_tsx.write_text(
            (
                'import { StrictMode } from "react";\n'
                'import { createRoot } from "react-dom/client";\n'
                'import "./styles.css";\n'
                'import { App } from "./App";\n\n'
                'createRoot(document.getElementById("root")!).render(\n'
                "  <StrictMode>\n"
                "    <App />\n"
                "  </StrictMode>,\n"
                ");\n"
            ),
            encoding="utf-8",
        )
        files["src/main.tsx"] = str(main_tsx)

        app_tsx = src_dir / "App.tsx"
        app_tsx.write_text(
            (
                "const antiCliches = "
                + anti_cliches
                + " as const;\n"
                + "const tweakAxes = "
                + tweak_axes
                + " as const;\n\n"
                + "export function App() {\n"
                + "  return (\n"
                + f'    <main className="app-shell" data-direction={json.dumps(direction["direction_id"], ensure_ascii=False)}>\n'
                + '      <section className="hero-card">\n'
                + f'        <p className="eyebrow">{html.escape(str(direction["name"]))}</p>\n'
                + f"        <h1>{html.escape(self.name)}</h1>\n"
                + f'        <p className="summary">{html.escape(self.description)}</p>\n'
                + f'        <p className="philosophy">{html.escape(str(direction["philosophy"]))}</p>\n'
                + '        <div className="meta-row">\n'
                + f'          <span>Hero: {html.escape(str(direction["hero_treatment"]))}</span>\n'
                + f'          <span>Proof: {html.escape(str(direction["proof_strategy"]))}</span>\n'
                + "        </div>\n"
                + "      </section>\n"
                + '      <section className="direction-grid">\n'
                + '        <article className="direction-card">\n'
                + "          <h2>Anti-Cliche Guardrails</h2>\n"
                + "          <ul>{antiCliches.map((item) => <li key={item}>{item}</li>)}</ul>\n"
                + "        </article>\n"
                + '        <article className="direction-card">\n'
                + "          <h2>Tweak Axes</h2>\n"
                + "          <ul>{tweakAxes.map((item) => <li key={item}>{item}</li>)}</ul>\n"
                + "        </article>\n"
                + "      </section>\n"
                + "    </main>\n"
                + "  );\n"
                + "}\n"
            ),
            encoding="utf-8",
        )
        files["src/App.tsx"] = str(app_tsx)

        styles = src_dir / "styles.css"
        styles.write_text(
            (
                ":root {\n"
                f"  --bg: {background};\n"
                f"  --surface: {self._alpha('#FFFFFF', 0.96)};\n"
                f"  --text: {text};\n"
                f"  --muted: {self._darken(text, 0.62)};\n"
                f"  --primary: {primary};\n"
                f"  --accent: {accent};\n"
                f"  --border: {self._alpha(border, 0.78)};\n"
                f'  --font-heading: "{heading_font}", sans-serif;\n'
                f'  --font-body: "{body_font}", system-ui, sans-serif;\n'
                "}\n\n"
                "* { box-sizing: border-box; }\n"
                "body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-body); }\n"
                ".app-shell { max-width: 1120px; margin: 0 auto; padding: 40px 20px 64px; }\n"
                ".hero-card, .direction-card { background: var(--surface); border: 1px solid var(--border); border-radius: 24px; box-shadow: 0 18px 40px rgba(13, 33, 57, 0.09); }\n"
                ".hero-card { padding: 32px; }\n"
                ".eyebrow { margin: 0 0 12px; color: var(--primary); text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; font-weight: 800; }\n"
                "h1, h2 { font-family: var(--font-heading); letter-spacing: -0.03em; }\n"
                "h1 { margin: 0 0 12px; font-size: clamp(34px, 5vw, 64px); }\n"
                ".summary, .philosophy { margin: 0 0 14px; max-width: 64ch; color: var(--muted); }\n"
                ".meta-row { display: flex; flex-wrap: wrap; gap: 10px; }\n"
                ".meta-row span { padding: 8px 12px; border-radius: 999px; background: rgba(15,124,250,0.08); font-size: 13px; font-weight: 700; }\n"
                ".direction-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 18px; }\n"
                ".direction-card { padding: 22px; }\n"
                ".direction-card ul { margin: 0; padding-left: 18px; display: grid; gap: 8px; }\n"
                '.app-shell[data-direction="cinematic-product"] .hero-card { background: linear-gradient(145deg, rgba(9, 18, 30, 0.96), rgba(12, 28, 43, 0.82)); color: #eef4fb; }\n'
                '.app-shell[data-direction="editorial-swiss"] h1 { text-transform: uppercase; max-width: 10ch; }\n'
                "@media (max-width: 860px) { .direction-grid { grid-template-columns: 1fr; } }\n"
            ),
            encoding="utf-8",
        )
        files["src/styles.css"] = str(styles)

        return files

    def generate_expo_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成 Expo 托管的 React Native 实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-expo"
        app_dir = output_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        direction = self._resolve_direction_profile(ui_contract)

        package_path = output_dir / "package.json"
        package_path.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-mobile",
                    "private": True,
                    "version": "0.1.0",
                    "main": "expo-router/entry",
                    "scripts": {
                        "start": "expo start",
                        "android": "expo run:android",
                        "ios": "expo run:ios",
                        "web": "expo start --web",
                    },
                    "dependencies": {
                        "expo": "^54.0.0",
                        "expo-router": "^5.0.0",
                        "react": "^19.0.0",
                        "react-native": "0.81.0",
                    },
                    "devDependencies": {"typescript": "^5.7.0"},
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(package_path)

        app_json = output_dir / "app.json"
        app_json.write_text(
            json.dumps(
                {
                    "expo": {
                        "name": self.name,
                        "slug": self.name.lower().replace(" ", "-"),
                        "scheme": self.name.lower().replace(" ", "-"),
                        "orientation": "portrait",
                        "plugins": ["expo-router"],
                    }
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["app.json"] = str(app_json)

        index_tsx = app_dir / "index.tsx"
        index_tsx.write_text(
            (
                'import { SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";\n\n'
                f"const antiCliches = {json.dumps(direction.get('anti_cliches', []), ensure_ascii=False)};\n\n"
                "export default function HomeScreen() {\n"
                "  return (\n"
                "    <SafeAreaView style={styles.safeArea}>\n"
                "      <ScrollView contentContainerStyle={styles.container}>\n"
                f'        <Text style={{{{styles.eyebrow}}}}>{html.escape(str(direction["name"]))}</Text>\n'
                f"        <Text style={{{{styles.title}}}}>{html.escape(self.name)}</Text>\n"
                f"        <Text style={{{{styles.summary}}}}>{html.escape(self.description)}</Text>\n"
                f'        <Text style={{{{styles.philosophy}}}}>{html.escape(str(direction["philosophy"]))}</Text>\n'
                "        <View style={styles.card}>\n"
                "          <Text style={styles.cardTitle}>Native Flow Checklist</Text>\n"
                "          <Text style={styles.cardBody}>Navigation, deep link, permission, offline cache, share and notification paths should be validated on device.</Text>\n"
                "        </View>\n"
                "        <View style={styles.card}>\n"
                "          <Text style={styles.cardTitle}>Anti-Cliche Guardrails</Text>\n"
                "          {antiCliches.map((item) => (\n"
                "            <Text key={item} style={styles.listItem}>• {item}</Text>\n"
                "          ))}\n"
                "        </View>\n"
                "      </ScrollView>\n"
                "    </SafeAreaView>\n"
                "  );\n"
                "}\n\n"
                "const styles = StyleSheet.create({\n"
                f"  safeArea: {{ flex: 1, backgroundColor: {json.dumps(palette.get('background', '#F5F8FF'))} }},\n"
                "  container: { padding: 24, gap: 18 },\n"
                f"  eyebrow: {{ color: {json.dumps(palette.get('primary', '#0F7CFA'))}, fontSize: 12, fontWeight: '800', letterSpacing: 1.2, textTransform: 'uppercase' }},\n"
                f"  title: {{ color: {json.dumps(palette.get('text', '#172133'))}, fontSize: 34, lineHeight: 40, fontWeight: '800', fontFamily: {json.dumps(typography.get('heading', 'System'))} }},\n"
                f"  summary: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.62))}, fontSize: 17, lineHeight: 26, fontFamily: {json.dumps(typography.get('body', 'System'))} }},\n"
                f"  philosophy: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.72))}, fontSize: 15, lineHeight: 24 }},\n"
                f"  card: {{ backgroundColor: '#FFFFFF', borderRadius: 24, padding: 18, borderWidth: 1, borderColor: {json.dumps(self._alpha(palette.get('border', '#DFE7F3'), 0.85))} }},\n"
                f"  cardTitle: {{ color: {json.dumps(palette.get('text', '#172133'))}, fontSize: 18, fontWeight: '700', marginBottom: 8 }},\n"
                f"  cardBody: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.66))}, fontSize: 14, lineHeight: 21 }},\n"
                f"  listItem: {{ color: {json.dumps(self._darken(palette.get('text', '#172133'), 0.7))}, fontSize: 14, lineHeight: 22, marginTop: 6 }},\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["app/index.tsx"] = str(index_tsx)

        return files

    def generate_flutter_project(self, ui_contract: dict) -> dict[str, str]:
        """生成 Flutter 实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-flutter"
        lib_dir = output_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        palette = ui_contract.get("color_palette", {})
        direction = self._resolve_direction_profile(ui_contract)

        pubspec = output_dir / "pubspec.yaml"
        pubspec.write_text(
            (
                f"name: {self.name.lower().replace(' ', '_')}_app\n"
                "description: Super Dev Flutter scaffold\n"
                "publish_to: 'none'\n"
                "environment:\n"
                "  sdk: '>=3.4.0 <4.0.0'\n"
                "dependencies:\n"
                "  flutter:\n"
                "    sdk: flutter\n"
                "  go_router: ^14.0.0\n"
                "  flutter_riverpod: ^2.5.0\n"
            ),
            encoding="utf-8",
        )
        files["pubspec.yaml"] = str(pubspec)

        main_dart = lib_dir / "main.dart"
        main_dart.write_text(
            (
                "import 'package:flutter/material.dart';\n\n"
                "void main() {\n"
                "  runApp(const SuperDevApp());\n"
                "}\n\n"
                "class SuperDevApp extends StatelessWidget {\n"
                "  const SuperDevApp({super.key});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    return MaterialApp(\n"
                f"      title: {json.dumps(self.name)},\n"
                "      theme: ThemeData(\n"
                f"        colorScheme: ColorScheme.fromSeed(seedColor: const Color({self._dart_color(palette.get('primary', '#0F7CFA'))})),\n"
                "        useMaterial3: true,\n"
                "      ),\n"
                "      home: const HomePage(),\n"
                "    );\n"
                "  }\n"
                "}\n\n"
                "class HomePage extends StatelessWidget {\n"
                "  const HomePage({super.key});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    return Scaffold(\n"
                "      body: SafeArea(\n"
                "        child: Padding(\n"
                "          padding: const EdgeInsets.all(24),\n"
                "          child: Column(\n"
                "            crossAxisAlignment: CrossAxisAlignment.start,\n"
                "            children: [\n"
                f"              Text({json.dumps(direction['name'])}, style: Theme.of(context).textTheme.labelSmall?.copyWith(letterSpacing: 1.2, fontWeight: FontWeight.w800)),\n"
                "              SizedBox(height: 12),\n"
                f"              Text({json.dumps(self.name)}, style: Theme.of(context).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800)),\n"
                "              SizedBox(height: 12),\n"
                f"              Text({json.dumps(self.description)}),\n"
                "              SizedBox(height: 16),\n"
                f"              Text({json.dumps(direction['philosophy'])}),\n"
                "            ],\n"
                "          ),\n"
                "        ),\n"
                "      ),\n"
                "    );\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["lib/main.dart"] = str(main_dart)
        return files

    def generate_miniapp_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成 uni-app / Taro 家族的小程序实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-miniapp"
        src_dir = output_dir / "src"
        pages_dir = src_dir / "pages" / "index"
        pages_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)
        is_taro = flavor == "taro"

        package_json = output_dir / "package.json"
        if is_taro:
            package_json.write_text(
                json.dumps(
                    {
                        "name": f"{self.name}-miniapp",
                        "private": True,
                        "version": "0.1.0",
                        "scripts": {"dev:weapp": "taro build --type weapp --watch"},
                        "dependencies": {"react": "^19.0.0", "@tarojs/taro": "^4.0.0"},
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files["package.json"] = str(package_json)

            app_tsx = src_dir / "app.tsx"
            app_tsx.parent.mkdir(parents=True, exist_ok=True)
            app_tsx.write_text(
                "import { PropsWithChildren } from 'react';\n\n"
                "function App({ children }: PropsWithChildren) {\n"
                "  return children;\n"
                "}\n\n"
                "export default App;\n",
                encoding="utf-8",
            )
            files["src/app.tsx"] = str(app_tsx)

            page_tsx = pages_dir / "index.tsx"
            page_tsx.write_text(
                (
                    "import { View, Text } from '@tarojs/components';\n\n"
                    "export default function IndexPage() {\n"
                    "  return (\n"
                    "    <View className='page'>\n"
                    f"      <Text className='eyebrow'>{html.escape(str(direction['name']))}</Text>\n"
                    f"      <Text className='title'>{html.escape(self.name)}</Text>\n"
                    f"      <Text className='summary'>{html.escape(self.description)}</Text>\n"
                    "    </View>\n"
                    "  );\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            files["src/pages/index/index.tsx"] = str(page_tsx)
        else:
            package_json.write_text(
                json.dumps(
                    {
                        "name": f"{self.name}-miniapp",
                        "private": True,
                        "version": "0.1.0",
                        "scripts": {"dev:h5": "uni", "dev:mp-weixin": "uni"},
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files["package.json"] = str(package_json)

            app_vue = src_dir / "App.vue"
            app_vue.parent.mkdir(parents=True, exist_ok=True)
            app_vue.write_text(
                '<script setup lang="ts"></script>\n\n'
                "<template>\n"
                "  <slot />\n"
                "</template>\n",
                encoding="utf-8",
            )
            files["src/App.vue"] = str(app_vue)

            page_vue = pages_dir / "index.vue"
            page_vue.write_text(
                (
                    "<template>\n"
                    '  <view class="page">\n'
                    f"    <text class=\"eyebrow\">{html.escape(str(direction['name']))}</text>\n"
                    f'    <text class="title">{html.escape(self.name)}</text>\n'
                    f'    <text class="summary">{html.escape(self.description)}</text>\n'
                    "  </view>\n"
                    "</template>\n\n"
                    "<style scoped>\n"
                    ".page { padding: 32rpx; display: flex; flex-direction: column; gap: 20rpx; }\n"
                    ".eyebrow { font-size: 24rpx; letter-spacing: 2rpx; text-transform: uppercase; color: #0F7CFA; }\n"
                    ".title { font-size: 64rpx; font-weight: 800; color: #172133; }\n"
                    ".summary { font-size: 30rpx; color: #4A5970; line-height: 1.6; }\n"
                    "</style>\n"
                ),
                encoding="utf-8",
            )
            files["src/pages/index/index.vue"] = str(page_vue)

            pages_json = output_dir / "pages.json"
            pages_json.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "path": "pages/index/index",
                                "style": {"navigationBarTitleText": self.name},
                            }
                        ]
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files["pages.json"] = str(pages_json)

        return files

    def generate_desktop_shell_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成桌面壳实施参考模板（Tauri / Electron / Wails）。"""
        output_dir = self.project_dir / "output" / "frontend-desktop-shell"
        src_dir = output_dir / "src"
        shell_dir = output_dir / flavor
        src_dir.mkdir(parents=True, exist_ok=True)
        shell_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)

        package_json = output_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-desktop",
                    "private": True,
                    "version": "0.1.0",
                    "scripts": {"dev": "vite", "build": "vite build"},
                    "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
                    "devDependencies": {"vite": "^6.0.0", "@vitejs/plugin-react": "^5.0.0"},
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(package_json)

        app_tsx = src_dir / "App.tsx"
        app_tsx.write_text(
            (
                "export function App() {\n"
                "  return (\n"
                "    <main style={{padding: 24, fontFamily: 'Inter, system-ui'}}> \n"
                f"      <p style={{textTransform: 'uppercase', color: '#0F7CFA', fontWeight: 800}}>{html.escape(str(direction['name']))}</p>\n"
                f"      <h1>{html.escape(self.name)}</h1>\n"
                f"      <p>{html.escape(self.description)}</p>\n"
                "      <ul>\n"
                "        <li>Window layout and restore</li>\n"
                "        <li>Native file system and import/export</li>\n"
                "        <li>Shortcut, IPC and offline recovery checks</li>\n"
                "      </ul>\n"
                "    </main>\n"
                "  );\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["src/App.tsx"] = str(app_tsx)

        if flavor == "tauri":
            tauri_conf = shell_dir / "tauri.conf.json"
            tauri_conf.write_text(
                json.dumps(
                    {"productName": self.name, "build": {"beforeDevCommand": "npm run dev"}},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files[f"{flavor}/tauri.conf.json"] = str(tauri_conf)
        elif flavor == "electron":
            electron_main = shell_dir / "main.ts"
            electron_main.write_text(
                "import { app, BrowserWindow } from 'electron';\n\n"
                "function createWindow() {\n"
                "  const win = new BrowserWindow({ width: 1440, height: 960 });\n"
                "  void win.loadURL('http://localhost:3000');\n"
                "}\n\n"
                "app.whenReady().then(createWindow);\n",
                encoding="utf-8",
            )
            files[f"{flavor}/main.ts"] = str(electron_main)
        else:
            wails_json = shell_dir / "wails.json"
            wails_json.write_text(
                json.dumps(
                    {"name": self.name, "frontend:install": "npm install"},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            files[f"{flavor}/wails.json"] = str(wails_json)
        return files

    def generate_hybrid_shell_project(self, ui_contract: dict, *, flavor: str) -> dict[str, str]:
        """生成 Ionic / Capacitor 混合壳实施参考模板。"""
        output_dir = self.project_dir / "output" / "frontend-hybrid-shell"
        src_dir = output_dir / "src"
        native_dir = output_dir / flavor
        src_dir.mkdir(parents=True, exist_ok=True)
        native_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        direction = self._resolve_direction_profile(ui_contract)

        package_json = output_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-hybrid",
                    "private": True,
                    "version": "0.1.0",
                    "scripts": {"dev": "vite", "build": "vite build"},
                    "dependencies": {
                        "@capacitor/core": "^7.0.0",
                        "react": "^19.0.0",
                        "react-dom": "^19.0.0",
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(package_json)

        app_tsx = src_dir / "App.tsx"
        app_tsx.write_text(
            (
                "export function App() {\n"
                "  return (\n"
                "    <main style={{padding: 24, fontFamily: 'Inter, system-ui'}}> \n"
                f"      <p style={{textTransform: 'uppercase', color: '#0F7CFA', fontWeight: 800}}>{html.escape(str(direction['name']))}</p>\n"
                f"      <h1>{html.escape(self.name)}</h1>\n"
                "      <p>Hybrid shell scaffold for camera, share, push and offline validation.</p>\n"
                "    </main>\n"
                "  );\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["src/App.tsx"] = str(app_tsx)

        capacitor_config = native_dir / "capacitor.config.ts"
        capacitor_config.write_text(
            (
                'import type { CapacitorConfig } from "@capacitor/cli";\n\n'
                "const config: CapacitorConfig = {\n"
                f"  appId: 'dev.super.{self.name.lower().replace(' ', '')}',\n"
                f"  appName: {json.dumps(self.name)},\n"
                '  webDir: "dist",\n'
                "};\n\n"
                "export default config;\n"
            ),
            encoding="utf-8",
        )
        files[f"{flavor}/capacitor.config.ts"] = str(capacitor_config)
        return files

    def _dart_color(self, hex_color: str) -> str:
        token = str(hex_color or "").lstrip("#")
        if len(token) != 6:
            token = "0F7CFA"
        return f"0xFF{token.upper()}"

    def generate_vue3_project(self) -> dict[str, str]:
        """生成完整的 Vue 3 + Vite 项目模板"""
        output_dir = self.project_dir / "output" / "frontend-vue3"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, str] = {}

        # package.json
        pkg = output_dir / "package.json"
        pkg_content = json.dumps(
            {
                "name": f"{self.name}-frontend",
                "version": "0.1.0",
                "private": True,
                "type": "module",
                "scripts": {
                    "dev": "vite",
                    "build": "vue-tsc && vite build",
                    "preview": "vite preview",
                    "test": "vitest",
                    "test:e2e": "playwright test",
                    "storybook": "storybook dev -p 6006",
                    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts",
                },
                "dependencies": {
                    "vue": "^3.4.0",
                    "vue-router": "^4.3.0",
                    "pinia": "^2.1.0",
                    "@vueuse/core": "^10.7.0",
                },
                "devDependencies": {
                    "@vitejs/plugin-vue": "^5.0.0",
                    "vite": "^5.0.0",
                    "vue-tsc": "^2.0.0",
                    "typescript": "^5.3.0",
                    "vitest": "^1.2.0",
                    "@vue/test-utils": "^2.4.0",
                    "tailwindcss": "^3.4.0",
                    "postcss": "^8.4.0",
                    "autoprefixer": "^10.4.0",
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        pkg.write_text(pkg_content, encoding="utf-8")
        files["package.json"] = str(pkg)

        # vite.config.ts
        vite_config = output_dir / "vite.config.ts"
        vite_config.write_text(
            (
                "import { defineConfig } from 'vite';\n"
                "import vue from '@vitejs/plugin-vue';\n"
                "import { resolve } from 'path';\n\n"
                "export default defineConfig({\n"
                "  plugins: [vue()],\n"
                "  resolve: {\n"
                "    alias: {\n"
                "      '@': resolve(__dirname, 'src'),\n"
                "    },\n"
                "  },\n"
                "  server: {\n"
                "    port: 3000,\n"
                "    proxy: {\n"
                "      '/api': { target: 'http://localhost:3001', changeOrigin: true },\n"
                "    },\n"
                "  },\n"
                "  build: {\n"
                "    rollupOptions: {\n"
                "      output: {\n"
                "        manualChunks: {\n"
                "          vendor: ['vue', 'vue-router', 'pinia'],\n"
                "        },\n"
                "      },\n"
                "    },\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vite.config.ts"] = str(vite_config)

        # tailwind.config.js
        tw = output_dir / "tailwind.config.js"
        tw.write_text(
            (
                "/** @type {import('tailwindcss').Config} */\n"
                "export default {\n"
                "  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],\n"
                "  theme: {\n"
                "    extend: {\n"
                "      colors: {\n"
                "        primary: 'var(--color-primary)',\n"
                "        secondary: 'var(--color-secondary)',\n"
                "        accent: 'var(--color-accent)',\n"
                "      },\n"
                "      fontFamily: {\n"
                "        heading: 'var(--font-heading)',\n"
                "        body: 'var(--font-body)',\n"
                "      },\n"
                "    },\n"
                "  },\n"
                "  plugins: [],\n"
                "};\n"
            ),
            encoding="utf-8",
        )
        files["tailwind.config.js"] = str(tw)

        # App.vue
        app_vue = src_dir / "App.vue"
        app_vue.write_text(
            (
                '<script setup lang="ts">\n'
                "import { RouterView } from 'vue-router';\n"
                "</script>\n\n"
                "<template>\n"
                "  <RouterView />\n"
                "</template>\n"
            ),
            encoding="utf-8",
        )
        files["src/App.vue"] = str(app_vue)

        # main.ts
        main_ts = src_dir / "main.ts"
        main_ts.write_text(
            (
                "import { createApp } from 'vue';\n"
                "import { createPinia } from 'pinia';\n"
                "import App from './App.vue';\n"
                "import router from './router';\n"
                "import './assets/main.css';\n\n"
                "const app = createApp(App);\n"
                "app.use(createPinia());\n"
                "app.use(router);\n"
                "app.mount('#app');\n"
            ),
            encoding="utf-8",
        )
        files["src/main.ts"] = str(main_ts)

        # Router
        router_dir = src_dir / "router"
        router_dir.mkdir(parents=True, exist_ok=True)
        (router_dir / "index.ts").write_text(
            (
                "import { createRouter, createWebHistory } from 'vue-router';\n\n"
                "const router = createRouter({\n"
                "  history: createWebHistory(),\n"
                "  routes: [\n"
                "    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },\n"
                "  ],\n"
                "});\n\n"
                "export default router;\n"
            ),
            encoding="utf-8",
        )
        files["src/router/index.ts"] = str(router_dir / "index.ts")

        # Views
        views_dir = src_dir / "views"
        views_dir.mkdir(parents=True, exist_ok=True)
        (views_dir / "HomeView.vue").write_text(
            (
                '<script setup lang="ts">\n'
                "</script>\n\n"
                "<template>\n"
                '  <main class="max-w-5xl mx-auto px-4 py-12">\n'
                f'    <h1 class="text-3xl font-heading font-bold">{html.escape(self.name)}</h1>\n'
                f'    <p class="mt-2 text-gray-600">{html.escape(self.description)}</p>\n'
                "  </main>\n"
                "</template>\n"
            ),
            encoding="utf-8",
        )
        files["src/views/HomeView.vue"] = str(views_dir / "HomeView.vue")

        return files

    def generate_angular_project(self) -> dict[str, str]:
        """生成 Angular 实施参考模板"""
        output_dir = self.project_dir / "output" / "frontend-angular"
        src_dir = output_dir / "src" / "app"
        src_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        # package.json
        pkg = output_dir / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-frontend",
                    "version": "0.1.0",
                    "scripts": {
                        "start": "ng serve",
                        "build": "ng build",
                        "test": "ng test",
                        "lint": "ng lint",
                    },
                    "dependencies": {
                        "@angular/animations": "^18.0.0",
                        "@angular/common": "^18.0.0",
                        "@angular/compiler": "^18.0.0",
                        "@angular/core": "^18.0.0",
                        "@angular/forms": "^18.0.0",
                        "@angular/platform-browser": "^18.0.0",
                        "@angular/router": "^18.0.0",
                        "rxjs": "^7.8.0",
                        "zone.js": "^0.14.0",
                    },
                    "devDependencies": {
                        "@angular/cli": "^18.0.0",
                        "@angular/compiler-cli": "^18.0.0",
                        "typescript": "^5.4.0",
                        "karma": "^6.4.0",
                        "jasmine-core": "^5.1.0",
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(pkg)

        # app.component.ts
        comp = src_dir / "app.component.ts"
        comp.write_text(
            (
                "import { Component } from '@angular/core';\n"
                "import { RouterOutlet } from '@angular/router';\n\n"
                "@Component({\n"
                "  selector: 'app-root',\n"
                "  standalone: true,\n"
                "  imports: [RouterOutlet],\n"
                f"  template: `<h1>{html.escape(self.name)}</h1><router-outlet />`,\n"
                "})\n"
                "export class AppComponent {}\n"
            ),
            encoding="utf-8",
        )
        files["src/app/app.component.ts"] = str(comp)

        # app.routes.ts
        routes = src_dir / "app.routes.ts"
        routes.write_text(
            (
                "import { Routes } from '@angular/router';\n\n"
                "export const routes: Routes = [\n"
                "  { path: '', loadComponent: () => import('./home/home.component').then(m => m.HomeComponent) },\n"
                "];\n"
            ),
            encoding="utf-8",
        )
        files["src/app/app.routes.ts"] = str(routes)

        # home component
        home_dir = src_dir / "home"
        home_dir.mkdir(parents=True, exist_ok=True)
        (home_dir / "home.component.ts").write_text(
            (
                "import { Component } from '@angular/core';\n\n"
                "@Component({\n"
                "  selector: 'app-home',\n"
                "  standalone: true,\n"
                f"  template: `<main><h2>Welcome to {html.escape(self.name)}</h2>"
                f"<p>{html.escape(self.description)}</p></main>`,\n"
                "})\n"
                "export class HomeComponent {}\n"
            ),
            encoding="utf-8",
        )
        files["src/app/home/home.component.ts"] = str(home_dir / "home.component.ts")

        return files

    def generate_svelte_project(self) -> dict[str, str]:
        """生成 SvelteKit 实施参考模板"""
        output_dir = self.project_dir / "output" / "frontend-svelte"
        src_dir = output_dir / "src"
        routes_dir = src_dir / "routes"
        routes_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        pkg = output_dir / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": f"{self.name}-frontend",
                    "version": "0.1.0",
                    "type": "module",
                    "scripts": {
                        "dev": "vite dev",
                        "build": "vite build",
                        "preview": "vite preview",
                        "test": "vitest",
                    },
                    "dependencies": {
                        "@sveltejs/kit": "^2.0.0",
                        "svelte": "^4.2.0",
                    },
                    "devDependencies": {
                        "@sveltejs/adapter-auto": "^3.0.0",
                        "@sveltejs/vite-plugin-svelte": "^3.0.0",
                        "vite": "^5.0.0",
                        "vitest": "^1.2.0",
                        "tailwindcss": "^3.4.0",
                        "postcss": "^8.4.0",
                        "autoprefixer": "^10.4.0",
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files["package.json"] = str(pkg)

        # +page.svelte
        page = routes_dir / "+page.svelte"
        page.write_text(
            (
                "<script>\n"
                "</script>\n\n"
                f"<h1>{html.escape(self.name)}</h1>\n"
                f"<p>{html.escape(self.description)}</p>\n"
            ),
            encoding="utf-8",
        )
        files["src/routes/+page.svelte"] = str(page)

        # +layout.svelte
        layout = routes_dir / "+layout.svelte"
        layout.write_text(
            ("<script>\n" "  import '../app.css';\n" "</script>\n\n" "<slot />\n"),
            encoding="utf-8",
        )
        files["src/routes/+layout.svelte"] = str(layout)

        # app.css
        app_css = src_dir / "app.css"
        app_css.write_text(
            "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
            encoding="utf-8",
        )
        files["src/app.css"] = str(app_css)

        return files
