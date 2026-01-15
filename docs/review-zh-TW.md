# 程式碼審查（zh-TW）

## 主要問題（依嚴重度）
1. 高 — 單一壞檔會中斷整批（未依規定記錄後跳過）
   - `src/doc_processor/phase1.py:108`
   - `src/doc_processor/phase2.py:67`
   - 說明：`parse_document`/`extract_text`/`extract_text_by_page` 直接拋例外，會讓整批終止，違反「失敗需記錄並跳過」規則。
   - 建議：在逐檔處理的迴圈加上 `try/except`，`logger.error` 後 `continue`，並讓退出碼呈現部分失敗。
2. 中 — Phase 2 以檔名取採購單號，與 PRD「只能靠內文解析/採購單號從進貨單內文抽取」不一致
   - `src/doc_processor/phase2.py:61`
   - 風險：檔名被改或不是 Phase 1 產出時，Excel 命名與內容可能錯；同時不符合需求。
   - 建議：改為從內文（進貨單）抽取採購單號，必要時可比對檔名並記錄不一致。

## 測試缺口/風險
- 缺少壞檔/無法解析 PDF 的錯誤處理測試（驗證「記錄並跳過」）
- 缺少 Phase 2 以內文抽取採購單號的測試用例

## 假設/問題
- 是否接受 Phase 2 只依賴 Phase 1 檔名？若 PRD 仍要求內文解析，我會把行為改回以進貨單內容為準。

## 變更摘要
- 無（僅審查）
