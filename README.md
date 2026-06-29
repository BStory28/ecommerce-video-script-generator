# 视频脚本生成器

国际化电商视频管线 **Skill2** — 根据产品卖点、品类、功能属性、用户痛点、目标市场，按爆款镜头结构生成 10s/15s 分镜脚本。

## 管线定位

```
Skill1: ecommerce-product-info-generator → product_layer.png + selling_points.json
                    ↓
Skill2 ← 本技能       → 输出: storyboard.json + storyboard.md
                    ↓
Skill3: ecommerce-video-generator → 最终视频
```

## 功能

- 根据产品卖点和目标市场生成结构化分镜脚本
- 支持 10s / 15s 短视频时长
- 支持 8 大视频类型（产品展示、开箱测评、使用教程、场景种草、对比评测、痛点解决方案、剧情故事、直播切片）
- 支持多国家/市场（北美、欧洲、中国、日本、韩国、东南亚、巴西）
- 输出 JSON（AI 管线用）+ Markdown（人工审阅用）

## 快速开始

```bash
# 纯 Python 标准库，无第三方依赖
python scripts/generate_storyboard.py \
  --product-img 产品图片.png \
  --config selling_points.json \
  --video-type "视频类型" \
  --category "产品品类" \
  --function "功能属性" \
  --pain-point "用户痛点" \
  --market "目标市场" \
  --duration 15
```

## 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--product-img` | ✅ | 产品白底图路径 |
| `--config` | ✅ | 卖点 JSON 路径（Skill1 输出） |
| `--video-type` | ✅ | 视频类型 |
| `--category` | ✅ | 产品品类 |
| `--market` | ✅ | 目标国家/市场 |
| `--duration` | ✅ | 视频时长（秒，10 或 15） |
| `--function` | ❌ | 功能属性描述 |
| `--pain-point` | ❌ | 用户痛点描述 |
| `--people` | ❌ | 人物特征描述 |
| `--output` | ❌ | 输出目录（默认 ./output） |

## 输出文件

| 文件 | 说明 |
|------|------|
| `output/storyboard.json` | 结构化分镜脚本（供 Skill3 消费） |
| `output/storyboard.md` | Markdown 格式文档（人工审阅） |

## 上下游

- **上游**: [ecommerce-product-info-generator](https://github.com/BStory28/ecommerce-product-info-generator) — 消费其输出的 `selling_points.json`
- **下游**: [ecommerce-video-generator](https://github.com/BStory28/ecommerce-video-generator) — 本技能输出的脚本供其渲染视频

## 注意事项

- 支持 AI API 生成（默认）和规则驱动备份（API 不可用时自动降级）
- 执行完成后 AI 会自动询问是否继续执行 Skill3
- 产品白底图仅作为视觉参考，人物和背景由纯文本生成
