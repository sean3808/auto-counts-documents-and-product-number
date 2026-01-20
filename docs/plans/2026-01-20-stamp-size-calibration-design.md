# 印章尺寸校正系統設計

## 背景

供應商印章在列印後的實際尺寸與預期不符。需要建立一個校正系統，讓用戶可以：
1. 測量每個印章的期望列印尺寸 (cm)
2. 系統自動計算正確的 PDF pt 尺寸

## 實測數據

從採購單 PDF 的「承製廠商簽回」框測量：
- PDF 尺寸：213.00 × 66.75 pt（理論 7.51 × 2.35 cm）
- 實測尺寸：7.2 × 2.3 cm
- **列印縮放比例：0.97**（縮小約 3%）

## 設計決策

| 項目 | 決策 |
|------|------|
| 配置方式 | YAML 檔案 (`config/stamps.yaml`) |
| 縮放比例 | 固定係數 0.97 |
| 未配置印章 | 報錯 + 跳過 |
| 印章圖片 | 使用裁切後版本（已移除空白邊距） |

## 配置檔格式

**檔案：** `config/stamps.yaml`

```yaml
# 列印環境校正
# 從「承製廠商簽回」框計算：PDF 7.51×2.35 cm，實測 7.2×2.3 cm
print_scale: 0.97

# 供應商印章期望列印尺寸 (cm)
# 新增印章前，請先實測期望尺寸再加入
vendors:
  TW111:
    width_cm: 4.5
    height_cm: 3.0
  TW113:
    width_cm: 4.5
    height_cm: 3.0
```

## 計算公式

```python
def get_target_pt(width_cm: float, height_cm: float, print_scale: float) -> tuple[float, float]:
    """從期望列印 cm 計算所需的 PDF pt"""
    target_width_pt = width_cm / print_scale * 28.35
    target_height_pt = height_cm / print_scale * 28.35
    return target_width_pt, target_height_pt
```

**範例：** TW111 期望 4.5 × 3.0 cm
- `target_pt = (4.5 / 0.97 * 28.35, 3.0 / 0.97 * 28.35)`
- `= (131.5, 87.7) pt`

## 資料流

```
config/stamps.yaml
    ↓ load_stamps_config()
期望尺寸 (cm) + print_scale
    ↓ get_target_pt()
目標框 (pt)
    ↓ scale_image_to_fit()
實際渲染尺寸 (pt)
    ↓ insert_image()
PDF 輸出
```

## 變更檔案

| 檔案 | 變更 |
|------|------|
| `config/stamps.yaml` | 新增 - 印章尺寸配置 |
| `src/doc_processor/stamper/base.py` | 新增 `load_stamps_config()`, `get_target_pt()` |
| `src/doc_processor/stamper/purchase_order.py` | 移除硬編碼 `STAMP_CONFIG_VENDOR_*`，改讀 YAML |

## 錯誤處理

遇到沒有配置的供應商印章時：
1. 輸出錯誤訊息，提示需要新增配置
2. 跳過此印章，繼續處理其他單據
3. Log 結尾摘要列出所有「缺配置」的供應商

## 向後相容

- 承辦人章（雅萍、簡銘佑）維持現有硬編碼座標和尺寸
- 僅供應商章改用 YAML 配置

## 印章圖片前處理

所有印章已批量裁切，移除空白邊距：
- 裁切前空白比例：0.2% ~ 44%
- 裁切後：有效內容 = 100%
