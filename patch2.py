import json
import re

def update_main():
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update UI Layout
    old_ui = '''        # Row 1: Base URL
        ctk.CTkLabel(self.api_frame, text="Base URL", font=self.FONT_UI).grid(
            row=1, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_base_url = ctk.CTkEntry(self.api_frame, placeholder_text="https://...", font=self.FONT_UI)
        self.entry_base_url.grid(row=1, column=1, columnspan=4, sticky="ew", padx=(4, 14), pady=8)
        self.entry_base_url.insert(0, self._api_config.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"))

        # Row 2: Fast Model (left) + Core Model (right)
        ctk.CTkLabel(self.api_frame, text="Fast Model", font=self.FONT_UI).grid(
            row=2, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_fast_model = ctk.CTkEntry(self.api_frame, placeholder_text="轻量级模型", font=self.FONT_UI)
        self.entry_fast_model.grid(row=2, column=1, sticky="ew", padx=(4, 20), pady=8)
        self.entry_fast_model.insert(0, self._api_config.get("fast_model", "doubao-lite-32k"))

        ctk.CTkLabel(self.api_frame, text="Core Model", font=self.FONT_UI).grid(
            row=2, column=2, sticky="e", padx=(20, 8), pady=8
        )
        self.entry_core_model = ctk.CTkEntry(self.api_frame, placeholder_text="强推理模型", font=self.FONT_UI)
        self.entry_core_model.grid(row=2, column=3, sticky="ew", padx=(4, 14), pady=8)
        self.entry_core_model.insert(0, self._api_config.get("core_model", "doubao-pro-32k"))

        # Row 3: API Key + Save button
        ctk.CTkLabel(self.api_frame, text="API Key", font=self.FONT_UI).grid(
            row=3, column=0, sticky="e", padx=(14, 8), pady=(8, 14)
        )
        self.entry_api_key = ctk.CTkEntry(
            self.api_frame, placeholder_text="sk-...", show="*", font=self.FONT_UI
        )
        self.entry_api_key.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(4, 10), pady=(8, 14))
        self.entry_api_key.insert(0, self._api_config.get("api_key", ""))

        ctk.CTkButton(
            self.api_frame, text="💾 保存配置", width=110, font=self.FONT_UI,
            command=self._on_save_config,
        ).grid(row=3, column=4, padx=(5, 14), pady=(8, 14), sticky="e")'''

    new_ui = '''        profiles = list(self._api_config.get("profiles", {}).keys())
        last_used = self._api_config.get("last_used", "默认配置")
        if not profiles:
            profiles = ["默认配置"]

        self._current_profile_data = self._api_config.get("profiles", {}).get(last_used, {})

        # Row 1: Profile Selector + Name Entry + Save Button
        ctk.CTkLabel(self.api_frame, text="配置预设", font=self.FONT_UI).grid(
            row=1, column=0, sticky="e", padx=(14, 8), pady=8
        )
        # Dropdown to load
        self.combo_profile = ctk.CTkComboBox(
            self.api_frame, values=profiles, command=self._on_profile_selected
        )
        self.combo_profile.set(last_used if last_used in profiles else profiles[0])
        self.combo_profile.grid(row=1, column=1, sticky="ew", padx=(4, 20), pady=8)

        ctk.CTkButton(
            self.api_frame, text="🗑️ 删除配置", width=100, font=self.FONT_UI,
            command=self._on_delete_profile, fg_color="#C82B2B", hover_color="#8f1b1b"
        ).grid(row=1, column=2, padx=(4, 14), pady=8, sticky="w")

        # Row 2: Base URL
        ctk.CTkLabel(self.api_frame, text="Base URL", font=self.FONT_UI).grid(
            row=2, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_base_url = ctk.CTkEntry(self.api_frame, placeholder_text="https://...", font=self.FONT_UI)
        self.entry_base_url.grid(row=2, column=1, columnspan=4, sticky="ew", padx=(4, 14), pady=8)
        self.entry_base_url.insert(0, self._current_profile_data.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"))

        # Row 3: Fast Model (left) + Core Model (right)
        ctk.CTkLabel(self.api_frame, text="Fast Model", font=self.FONT_UI).grid(
            row=3, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_fast_model = ctk.CTkEntry(self.api_frame, placeholder_text="轻量级模型", font=self.FONT_UI)
        self.entry_fast_model.grid(row=3, column=1, sticky="ew", padx=(4, 20), pady=8)
        self.entry_fast_model.insert(0, self._current_profile_data.get("fast_model", "doubao-lite-32k"))

        ctk.CTkLabel(self.api_frame, text="Core Model", font=self.FONT_UI).grid(
            row=3, column=2, sticky="e", padx=(20, 8), pady=8
        )
        self.entry_core_model = ctk.CTkEntry(self.api_frame, placeholder_text="强推理模型", font=self.FONT_UI)
        self.entry_core_model.grid(row=3, column=3, sticky="ew", padx=(4, 14), pady=8)
        self.entry_core_model.insert(0, self._current_profile_data.get("core_model", "doubao-pro-32k"))

        # Row 4: API Key + Save button
        ctk.CTkLabel(self.api_frame, text="API Key", font=self.FONT_UI).grid(
            row=4, column=0, sticky="e", padx=(14, 8), pady=(8, 14)
        )
        self.entry_api_key = ctk.CTkEntry(
            self.api_frame, placeholder_text="sk-...", show="*", font=self.FONT_UI
        )
        self.entry_api_key.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(4, 10), pady=(8, 14))
        self.entry_api_key.insert(0, self._current_profile_data.get("api_key", ""))

        ctk.CTkButton(
            self.api_frame, text="💾 保存/覆盖此配置", width=130, font=self.FONT_UI,
            command=self._on_save_profile,
        ).grid(row=4, column=4, padx=(5, 14), pady=(8, 14), sticky="e")'''
    
    content = content.replace(old_ui, new_ui)

    # 2. Update Handler
    old_handler = '''def _on_save_config(self) -> None:
        """保存 API 配置到本地文件。"""
        config = {
            "base_url": self.entry_base_url.get().strip(),
            "fast_model": self.entry_fast_model.get().strip(),
            "core_model": self.entry_core_model.get().strip(),
            "api_key": self.entry_api_key.get().strip(),
        }
        with open(".api_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        self._log("✅ API 配置已保存到 .api_config.json")'''

    new_handler = '''def _on_profile_selected(self, choice: str) -> None:
        profiles = self._api_config.get("profiles", {})
        if choice in profiles:
            data = profiles[choice]
            self.entry_base_url.delete(0, "end")
            self.entry_base_url.insert(0, data.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"))
            self.entry_fast_model.delete(0, "end")
            self.entry_fast_model.insert(0, data.get("fast_model", "doubao-lite-32k"))
            self.entry_core_model.delete(0, "end")
            self.entry_core_model.insert(0, data.get("core_model", "doubao-pro-32k"))
            self.entry_api_key.delete(0, "end")
            self.entry_api_key.insert(0, data.get("api_key", ""))
            
            self._api_config["last_used"] = choice
            self._save_api_config_file()
            self._log(f"✅ 已加载预设: {choice}")
            
    def _on_delete_profile(self) -> None:
        choice = self.combo_profile.get().strip()
        if choice in self._api_config.get("profiles", {}):
            del self._api_config["profiles"][choice]
            if len(self._api_config["profiles"]) == 0:
                self._api_config["profiles"]["默认配置"] = {}
                last = "默认配置"
            else:
                last = list(self._api_config["profiles"].keys())[0]
            self._api_config["last_used"] = last
            self._save_api_config_file()
            self.combo_profile.configure(values=list(self._api_config["profiles"].keys()))
            self.combo_profile.set(last)
            self._on_profile_selected(last)
            self._log(f"🗑️ 已删除预设: {choice}")

    def _on_save_profile(self) -> None:
        """保存或覆盖当前填写的配置，使用组合框中的名字。"""
        choice = self.combo_profile.get().strip()
        if not choice:
            self._log("⚠️ 请在配置下拉框中输入或选择一个预设名称！")
            return
            
        profiles = self._api_config.get("profiles", {})
        if choice not in profiles and len(profiles) >= 10:
            self._log("⚠️ 最多只能保存 10 组预设，请先删除不需要的预设！")
            return
            
        config = {
            "base_url": self.entry_base_url.get().strip(),
            "fast_model": self.entry_fast_model.get().strip(),
            "core_model": self.entry_core_model.get().strip(),
            "api_key": self.entry_api_key.get().strip(),
        }
        profiles[choice] = config
        self._api_config["profiles"] = profiles
        self._api_config["last_used"] = choice
        self._save_api_config_file()
        
        self.combo_profile.configure(values=list(profiles.keys()))
        self.combo_profile.set(choice)
        self._log(f"✅ 配置 `{choice}` 已保存并设为当前预设（最多存储10个）。")

    def _save_api_config_file(self) -> None:
        try:
            API_CONFIG_PATH.write_text(
                json.dumps(self._api_config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass'''

    # For replacing string correctly taking into account potentially slightly different characters, regular expressions are safer:
    # Actually just replacing directly is faster if exact
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The text we try to replace might contain Chinese characters encoded differently. Let's do partial replace.
    # UI part
    start_str = '# Row 1: Base URL'
    end_str = '# Row 3: API Key + Save button\\n'
    # Actually just run regex
    ui_pat = r'# Row 1: Base URL.*?(?=# 鈹€鈹€ 鐢熸垚鎺у埗鍖?)'
    
    # We will just write a custom simple python string replace line by line
    
def patch_smart(filepath):
    lines = open(filepath, 'r', encoding='utf-8').readlines()
    out = []
    in_ui = False
    in_handler = False

    for i, line in enumerate(lines):
        if "Row 1: Base URL" in line:
            in_ui = True
            # Write new UI
            out.append("""        profiles = list(self._api_config.get("profiles", {}).keys())
        last_used = self._api_config.get("last_used", "默认配置")
        if not profiles:
            profiles = ["默认配置"]

        self._current_profile_data = self._api_config.get("profiles", {}).get(last_used, {})

        # Row 1: Profile Selector + Name Entry + Save Button
        ctk.CTkLabel(self.api_frame, text="配置预设", font=self.FONT_UI).grid(
            row=1, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.combo_profile = ctk.CTkComboBox(
            self.api_frame, values=profiles, command=self._on_profile_selected
        )
        self.combo_profile.set(last_used if last_used in profiles else profiles[0])
        self.combo_profile.grid(row=1, column=1, sticky="ew", padx=(4, 20), pady=8)

        ctk.CTkButton(
            self.api_frame, text="🗑️ 删除", width=70, font=self.FONT_UI,
            command=self._on_delete_profile, fg_color="#C82B2B", hover_color="#8f1b1b"
        ).grid(row=1, column=2, padx=(4, 14), pady=8, sticky="w")

        # Row 2: Base URL
        ctk.CTkLabel(self.api_frame, text="Base URL", font=self.FONT_UI).grid(
            row=2, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_base_url = ctk.CTkEntry(self.api_frame, placeholder_text="https://...", font=self.FONT_UI)
        self.entry_base_url.grid(row=2, column=1, columnspan=4, sticky="ew", padx=(4, 14), pady=8)
        self.entry_base_url.insert(0, self._current_profile_data.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"))

        # Row 3: Fast Model (left) + Core Model (right)
        ctk.CTkLabel(self.api_frame, text="Fast Model", font=self.FONT_UI).grid(
            row=3, column=0, sticky="e", padx=(14, 8), pady=8
        )
        self.entry_fast_model = ctk.CTkEntry(self.api_frame, placeholder_text="轻量级模型", font=self.FONT_UI)
        self.entry_fast_model.grid(row=3, column=1, sticky="ew", padx=(4, 20), pady=8)
        self.entry_fast_model.insert(0, self._current_profile_data.get("fast_model", "doubao-lite-32k"))

        ctk.CTkLabel(self.api_frame, text="Core Model", font=self.FONT_UI).grid(
            row=3, column=2, sticky="e", padx=(20, 8), pady=8
        )
        self.entry_core_model = ctk.CTkEntry(self.api_frame, placeholder_text="强推理模型", font=self.FONT_UI)
        self.entry_core_model.grid(row=3, column=3, sticky="ew", padx=(4, 14), pady=8)
        self.entry_core_model.insert(0, self._current_profile_data.get("core_model", "doubao-pro-32k"))

        # Row 4: API Key + Save button
        ctk.CTkLabel(self.api_frame, text="API Key", font=self.FONT_UI).grid(
            row=4, column=0, sticky="e", padx=(14, 8), pady=(8, 14)
        )
        self.entry_api_key = ctk.CTkEntry(
            self.api_frame, placeholder_text="sk-...", show="*", font=self.FONT_UI
        )
        self.entry_api_key.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(4, 10), pady=(8, 14))
        self.entry_api_key.insert(0, self._current_profile_data.get("api_key", ""))

        ctk.CTkButton(
            self.api_frame, text="💾 保存/覆盖当前名称预设", width=150, font=self.FONT_UI,
            command=self._on_save_profile,
        ).grid(row=4, column=4, padx=(5, 14), pady=(8, 14), sticky="e")\n""")
            continue

        if in_ui:
            if "ctrl_frame = ctk.CTkFrame" in line:
                in_ui = False
                out.append("        # ── 生成控制区 ────────────────────────────────────────\n")
                out.append(line)
            continue

        if "def _on_save_config(self)" in line:
            in_handler = True
            out.append("""    def _on_profile_selected(self, choice: str) -> None:
        profiles = self._api_config.get("profiles", {})
        if choice in profiles:
            data = profiles[choice]
            self.entry_base_url.delete(0, "end")
            self.entry_base_url.insert(0, data.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"))
            self.entry_fast_model.delete(0, "end")
            self.entry_fast_model.insert(0, data.get("fast_model", "doubao-lite-32k"))
            self.entry_core_model.delete(0, "end")
            self.entry_core_model.insert(0, data.get("core_model", "doubao-pro-32k"))
            self.entry_api_key.delete(0, "end")
            self.entry_api_key.insert(0, data.get("api_key", ""))
            
            self._api_config["last_used"] = choice
            self._save_api_config_file()
            self._log(f"✅ 已加载预设: {choice}")
            
    def _on_delete_profile(self) -> None:
        choice = self.combo_profile.get().strip()
        if choice in self._api_config.get("profiles", {}):
            del self._api_config["profiles"][choice]
            if len(self._api_config["profiles"]) == 0:
                self._api_config["profiles"]["默认配置"] = {}
                last = "默认配置"
            else:
                last = list(self._api_config["profiles"].keys())[0]
            self._api_config["last_used"] = last
            self._save_api_config_file()
            self.combo_profile.configure(values=list(self._api_config["profiles"].keys()))
            self.combo_profile.set(last)
            self._on_profile_selected(last)
            self._log(f"🗑️ 已删除预设: {choice}")

    def _on_save_profile(self) -> None:
        \"\"\"保存或覆盖组合框上名称对应的配置。\"\"\"
        choice = self.combo_profile.get().strip()
        if not choice:
            self._log("⚠️ 请在预设下拉框中输入或选择一个名称（如: 通义千问配置）！")
            return
            
        profiles = self._api_config.get("profiles", {})
        if choice not in profiles and len(profiles) >= 10:
            self._log("⚠️ 最多只能保存 10 组预设，请先选择需要删除的预设点 [删除]。")
            return
            
        config = {
            "base_url": self.entry_base_url.get().strip(),
            "fast_model": self.entry_fast_model.get().strip(),
            "core_model": self.entry_core_model.get().strip(),
            "api_key": self.entry_api_key.get().strip(),
        }
        profiles[choice] = config
        self._api_config["profiles"] = profiles
        self._api_config["last_used"] = choice
        self._save_api_config_file()
        
        self.combo_profile.configure(values=list(profiles.keys()))
        self.combo_profile.set(choice)
        self._log(f"✅ 配置 `{choice}` 已保存（最多支持10组）。")

    def _save_api_config_file(self) -> None:
        try:
            API_CONFIG_PATH.write_text(
                json.dumps(self._api_config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass\n""")
            continue

        if in_handler:
            if "def _on_start_generate(self)" in line:
                in_handler = False
                out.append("    # ── 开始生成 ────────────────────────────────────────────────────────────\n")
                out.append(line)
            continue
            
        out.append(line)

    open('main.py', 'w', encoding='utf-8').writelines(out)

if __name__ == "__main__":
    patch_smart('main.py')