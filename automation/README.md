# P0 自动化说明

本目录是《头版》的自动化包，配合仓库根目录的 `scripts/update_quotes.py` 使用。

## 内容

- `edition-guard.yml` — 巡刊守卫：每天 07:20 和 12:30（Asia/Shanghai）检查当天期次，
  缺刊时自动开一个告警 issue（不重复开），并让 workflow 运行失败以便可见。
- `update-quotes.yml` — 行情刷新：每 30 分钟运行 `scripts/update_quotes.py`，
  以 raemyn24-bot 的名义把三个 `*-quotes.json` 备用快照提交回 main。

## 激活方法（一次性）

这两个文件最终要放在 `.github/workflows/` 下才生效。由于 Muse 的 GitHub App
没有 Workflows 权限，无法代为提交该目录，需仓库所有者在 GitHub 网页端手动放一次：

1. 切到包含本文件的分支；
2. 用 “Add file → Create new file”，路径填 `.github/workflows/edition-guard.yml`，
   内容粘贴本目录同名文件全文，提交到同一分支；
3. 对 `update-quotes.yml` 重复一次；
4. 合并 PR 后，两个 workflow 即开始按计划运行，可在 Actions 页查看。

激活完成后，本目录的两个 yml 副本可保留作备份，也可删除。

## 行情脚本

`scripts/update_quotes.py` 无需任何 API key：

- 加密：OKX 公共行情（现价对 24 小时开盘价算涨跌）
- 常用与美股：Yahoo Finance chart 接口（现价对上一交易日收盘算涨跌，含重试与 query2 备用域名）
- 任一文件抓取失败时不覆盖旧文件；三份全失败时脚本以非零码退出，workflow 会标红。
