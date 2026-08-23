# ⚠️ 使用前風險警告

本工具並非遊戲官方程式。使用前請自行評估並承擔下列風險：

1. 本工具會修改遊戲的 Godot `PCK` 封包。此行為可能違反遊戲規範，並存在帳號遭停權或封鎖的風險。
2. 本程式與其原始碼皆由 AI 產生，無法保證品質、正確性、安全性、相容性或後續維護。
3. 若擔心 Release 內的打包執行檔含有惡意程式，請勿直接執行；可改為取得原始碼、檢查內容後自行執行 Python 版本或自行打包。
4. 基於上述風險，請務必自行閱讀並審查程式碼，再判斷是否使用本工具。作者與 AI 均無法代替你完成安全性判斷。

# Soul's Remnant Font Manager

Soul's Remnant 的跨平台字型管理器。使用者只需執行 Release 裡的單一檔案，不必安裝 Python、.NET、Java 或 Godot。

目前支援的功能：

- 自動尋找 Steam 收藏庫與 App `3451980`
- 匯入 `.ttf`／`.otf` 字型並做基本格式檢查
- 遊戲選項「字體＝點陣／傳統」可分別指定字型，遊戲內切換時同步套用
- 同時處理遊戲主題、FontVariation、匿名 Theme 子資源、`loc_fixed_font` HUD 與稍後才載入的 UI
- 六類獨立字體大小：一般 UI、說明長文、任務、HUD／世界標籤、聊天、彈出提示
- 每類以遊戲原始字號為 `1.00×`，不累乘且可個別恢復預設
- 可一次將六類字體大小設為相同倍率，或全部恢復 `1.00×`
- 任一模式留空時完整使用該模式的遊戲內建字型
- 傳統模式沿用遊戲內建的 `0.85` 版面補償，點陣模式不觸發
- 完整保留遊戲內建的 UI 與道具說明字型大小
- 可從選單開啟 [免費字型網站](https://font.emtech.cc/)
- 使用小型 rollback journal 安全修改 Godot PCK，不建立數百 MB 備份
- Steam 更新後在下次啟動前重新套用
- 保留原有 Steam Launch Options，解除安裝時只還原本工具管理的值
- Windows 設定模式顯示主控台；Steam prelaunch 模式不顯示黑窗
- 從 Releases 開啟新版 Manager 時，自動更新 Steam 實際呼叫的已安裝副本

本專案不包含遊戲檔案、解出的遊戲腳本或第三方字型。Manager 只會在使用者自己的遊戲安裝中讀取目標項目並產生差分。

## 使用方式

1. 從 Releases 下載對應作業系統的檔案。
2. 執行 Manager，分別設定點陣／傳統字型；留空代表使用遊戲內建。
3. 若 Steam 正在執行，允許 Manager 正常關閉；完成後會自動重開。
4. 從 Steam 正常啟動遊戲。

設定資料位置：

- Windows：`%LOCALAPPDATA%\SoulRemnantFontManager`
- Linux：`$XDG_DATA_HOME/SoulRemnantFontManager` 或 `~/.local/share/SoulRemnantFontManager`
- Linux Flatpak Steam：`~/.var/app/com.valvesoftware.Steam/data/SoulRemnantFontManager`
- macOS：`~/Library/Application Support/SoulRemnantFontManager`

安裝與解除安裝不會強制終止 Steam；正常關閉逾時時會停止操作。若 PCK 已被其他工具修改，Manager 會拒絕盲目還原。

## 本機開發

```bash
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests
python -m pip install -r requirements-build.txt
python build.py
```

## Release

推送格式為 `v*` 的 tag 後，GitHub Actions 會在 Windows、Linux、Intel macOS 與 Apple Silicon macOS 上分別執行測試、用 PyInstaller 建置，並建立 GitHub Release。

macOS Release 目前未簽署；第一次開啟時可能需要在「隱私權與安全性」中允許執行。正式公開前可在 Actions secrets 加入 Apple Developer 憑證與 notarization。

## 注意

PCK 腳本結構可能隨遊戲更新改變。所有修改都有明確的相容性錨點；找不到錨點時會停止，而不是猜測寫入。
