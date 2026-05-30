# CLI（`cli.py`）

命令列介面以 [Typer](https://typer.tiangolo.com/) 建構。它的工作很薄：解析參數、
載入並覆寫設定、呼叫 `converter.convert()`、呈現乾淨的成功／錯誤輸出。

## 指令

| 指令 | 用途 |
|------|------|
| `md2pdf <file.md>` | 轉檔（簡寫——見下方*預設指令*）。 |
| `md2pdf convert <file.md>` | 轉檔，明確寫法。 |
| `md2pdf init [DIR]` | 產生 `md2pdf.toml` + `theme.css` 範本。 |
| `md2pdf --version` | 印出版本並結束。 |

## 預設指令技巧：`DefaultGroup`

預設情況下 Typer/Click 會拒絕 `md2pdf report.md`，因為 `report.md` 不是已知的子指令。
我們希望 `md2pdf <file>` 等同於 `md2pdf convert <file>`，又不失去 `init` 這種真正的
子指令。

`DefaultGroup(TyperGroup)`（cli.py:31）覆寫 `resolve_command`：

```python
def resolve_command(self, ctx, args):
    try:
        return super().resolve_command(ctx, args)   # 是真的子指令嗎？
    except UsageError:
        if args and not args[0].startswith("-"):     # 看起來像檔案，不是旗標
            return super().resolve_command(ctx, [self.default_command, *args])
        raise
```

於是「第一個參數不是旗標、又是未知指令」就會被改用 `convert <arg>` 重試。光打 `-o`
而沒有指令時仍會（正確地）拋錯，因為守衛要求第一個參數不能以 `-` 開頭。

### Typer 內嵌了 Click

Typer 0.26.3 把 Click vendored 在 `typer._click` 底下。這就是為什麼 import 是：

```python
from typer._click.core import Context as ClickContext
from typer._click.exceptions import UsageError
```

在這個環境直接 import 頂層 `click` 套件會失敗（`ModuleNotFoundError: No module named
'click'`）。若你升級 Typer，請重新確認這些 import 路徑。

## 旗標如何覆寫設定

`convert` 為每個可覆寫的設定宣告一個 Typer `Option`，預設都是 `None`，代表「CLI 上沒給」。
`_apply_overrides()`（cli.py:130）接著**只針對使用者實際傳入的旗標**改寫已載入的
`Config`——這就是 *CLI > 檔案 > 預設* 優先序的實作。

值得注意的細節：

- `--margin 2cm` 會展開成四邊一致的 `Margin(top, bottom, left, right)`。
- `--css` 可重複，並**附加**到設定的 CSS 清單後，所以 CLI 的 CSS 會贏（後面的檔案蓋掉
  前面的）。CLI 的 CSS 路徑相對於 **CWD** 解析（`p.resolve()`），與設定檔內的 CSS
  相對於設定檔目錄解析不同。
- `--header`／`--footer` 會一次同時*啟用*該頁眉／頁腳並設定其模板。
- 像 `--toc/--no-toc` 這種布林對是三態（`None`／`True`／`False`），所以能分辨「未設定」
  與「明確關閉」。

> **B008 註記：** ruff 的 B008（「預設參數中呼叫函式」）在全專案被*忽略*，因為在預設值裡
> 呼叫 `typer.Option(...)`／`typer.Argument(...)` 是 Typer 規定的慣用法，不是 bug。

## `init`

`init` 用模組內的 `_SAMPLE_TOML` 與 `_SAMPLE_CSS` 常數寫出兩個起始檔。除非加 `--force`，
否則會跳過既有檔案，並印出下一步（安裝 Chromium、再執行）。若你改了預設設定形狀，記得
同步更新 `_SAMPLE_TOML`。

## 輸出與錯誤呈現

- 成功：透過 stdout 的 `rich.Console` 印 `✓ input → output`（綠色）。
- 錯誤：用另一個 stderr `Console`。三個 `except` 分支把例外對應到訊息並以 exit code 1
  結束（見 [架構 → 失敗處理](Architecture.md)）。注意 `raise typer.Exit(code=1) from exc`
  的寫法——`from exc` 同時滿足 ruff B904 並保留原因鏈。
