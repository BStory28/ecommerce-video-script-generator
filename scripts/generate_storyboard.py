#!/usr/bin/env python3
"""
国际化电商短视频分镜脚本生成器（AI驱动版）
根据产品白底图 + 商品卖点 + 视频类型 + 品类 + 国家 + 时长，
调用AI生成自然、生动、产品特化的爆款分镜脚本。

输出: storyboard.json + storyboard.md

用法:
  python generate_storyboard.py \\
    --product-img product.png \\
    --config selling_points.json \\
    --video-type 痛点解决 \\
    --category 家居日用 \\
    --market thailand \\
    --duration 15 \\
    --output ./output
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

_DESKTOP_SCRIPT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "AI视频脚本")

def _default_output_dir() -> str:
    path = _DESKTOP_SCRIPT_DIR
    os.makedirs(path, exist_ok=True)
    return path

def _format_storyboard_markdown(product_name: str, video_type: str, category: str, market: str,
                                duration: int, shot_count: int, output_dir: str) -> str:
    """Format storyboard result as Markdown for chat display"""
    lines = [
        f"📋 **分镜脚本生成完成** — {product_name} ({market})",
        "",
        "**【基本信息】**",
        f"- 视频类型：{video_type}",
        f"- 品类：{category}",
        f"- 时长：{duration}s",
        f"- 镜头数：{shot_count}",
        "",
        "**【输出文件】**",
        f"📁 输出目录：`{output_dir}`",
        f"   - `storyboard.json`（AI管线使用）",
        f"   - `storyboard.md`（人工审阅）",
        "",
        "---",
        "✅ **分镜脚本已生成**，可继续执行 Skill3（AI视频生成）",
    ]
    return "\n".join(lines)


# ============================================================
# 国家配置
# ============================================================
COUNTRY_CONFIG = {
    "thailand": {
        "language": "th",
        "lang_name": "泰语",
        "people": "泰国当地人，健康小麦肤色，表情丰富肢体热情，穿搭浅色棉麻宽松服",
        "scene_decor": "增加热带绿植、藤编软装、高饱和亮色装饰，家庭温馨氛围",
        "lighting_adj": "高饱和亮色暖调热带自然光",
        "emotion": "热情分享",
        "bgm_style": "泰式轻快电子/热带流行",
    },
    "cn": {
        "language": "zh",
        "lang_name": "中文",
        "people": "东亚黄皮肤当地人，表情含蓄温和，穿搭简约浅色系",
        "scene_decor": "简约居家风格，ins风软装，低饱和柔光色调，少量绿植点缀",
        "lighting_adj": "低饱和柔光窗边自然光",
        "emotion": "温和真诚",
        "bgm_style": "轻快电子国风",
    },
    "jp": {
        "language": "ja",
        "lang_name": "日语",
        "people": "日本人，白皮肤，动作温柔克制，穿搭米色棉麻简约系",
        "scene_decor": "原木极简风格，大量留白，低对比柔光，少量陶器装饰",
        "lighting_adj": "低对比柔和漫射光",
        "emotion": "温柔治愈",
        "bgm_style": "日系治愈Lo-fi",
    },
    "kr": {
        "language": "ko",
        "lang_name": "韩语",
        "people": "韩国人，白皮，潮流手势，穿搭浅色系ins风",
        "scene_decor": "马卡龙浅色系软装，高亮度柔光，可爱小物装饰，ins风布置",
        "lighting_adj": "高亮度柔光水光感",
        "emotion": "时尚精致",
        "bgm_style": "韩系时尚电子",
    },
    "us": {
        "language": "en",
        "lang_name": "英语",
        "people": "欧美人，多元肤色，肢体动作开放大方，穿搭休闲宽松",
        "scene_decor": "开放式大空间，硬朗自然光对比，简约实用软装",
        "lighting_adj": "硬朗自然光高对比",
        "emotion": "自信热情",
        "bgm_style": "Pop/EDM欧美流行",
    },
}

# ============================================================
# 视频类型镜头结构
# ============================================================
VIDEO_TYPE_STRUCTURE = {
    "痛点解决": {
        "description": "痛点冲击→产品亮相→实操演示→效果对比→[15s]推荐CTA",
        "10s": {"shot_count": 4, "durations": [2, 2, 3, 3], "functions": ["痛点冲击", "产品亮相", "实操演示", "效果对比"]},
        "15s": {"shot_count": 5, "durations": [3, 2, 3, 4, 3], "functions": ["痛点冲击", "产品亮相", "实操演示", "效果对比", "推荐CTA"]},
    },
    "UGC种草": {
        "description": "日常代入→产品全景→上手体验→亮点总结→[15s]种草推荐",
        "10s": {"shot_count": 4, "durations": [2, 2, 3, 3], "functions": ["日常场景代入", "产品全景展示", "上手真实体验", "亮点总结推荐"]},
        "15s": {"shot_count": 5, "durations": [3, 2, 3, 4, 3], "functions": ["日常场景代入", "产品全景展示", "上手真实体验", "多角度次卖点展示", "种草推荐"]},
    },
    "产品演示": {
        "description": "产品全景→功能演示1→功能演示2→整体效果→[15s]细节亮点",
        "10s": {"shot_count": 4, "durations": [2, 2, 3, 3], "functions": ["产品全景特写", "核心功能演示1", "核心功能演示2", "整体效果展示"]},
        "15s": {"shot_count": 5, "durations": [3, 2, 3, 4, 3], "functions": ["产品全景特写", "核心功能演示1", "核心功能演示2", "细节亮点展示", "最终效果展示"]},
    },
    "开箱种草": {
        "description": "开箱动作→产品露出→初次试用→细节亮点→[15s]满意推荐",
        "10s": {"shot_count": 4, "durations": [2, 2, 3, 3], "functions": ["开箱动作特写", "产品完整露出", "初次试用体验", "质感细节亮点"]},
        "15s": {"shot_count": 5, "durations": [3, 2, 3, 4, 3], "functions": ["开箱动作特写", "产品完整露出", "初次试用体验", "质感细节亮点", "满意表情推荐"]},
    },
    "CTA带货": {
        "description": "产品高光→卖点概括→快速实操→下单引导→[15s]多角度强化",
        "10s": {"shot_count": 4, "durations": [2, 2, 3, 3], "functions": ["产品高光特写", "核心卖点概括", "快速实操展示", "价格下单引导"]},
        "15s": {"shot_count": 5, "durations": [3, 2, 3, 4, 3], "functions": ["产品高光特写", "核心卖点概括", "快速实操展示", "多角度卖点强化", "价格下单引导"]},
    },
    "产品口播": {
        "description": "产品亮相→核心卖点口播→使用效果→细节补充→[15s]推荐CTA",
        "10s": {"shot_count": 4, "durations": [2, 2, 3, 3], "functions": ["产品亮相特写", "核心卖点口播", "使用效果展示", "推荐CTA"]},
        "15s": {"shot_count": 5, "durations": [3, 2, 3, 4, 3], "functions": ["产品亮相特写", "核心卖点口播", "使用效果展示", "细节亮点补充", "推荐CTA"]},
    },
}

# ============================================================
# 品类专属规则（概要，AI会基于此生成）
# ============================================================
CATEGORY_DESC = {
    "家居日用": "中速节奏，特写功能接触面和前后对比痕迹，跟拍手部操作，音效为工具摩擦/撕拉/水流ASMR，均匀室内柔光加侧逆光对比",
    "美妆护肤": "前慢后快，质地慢动作特写皮肤纹理，微距推镜环绕产品，开盖涂抹ASMR，柔和水光低对比",
    "食品零食": "快节奏开袋入口放慢，特写食材汤汁咀嚼，俯拍微距滴落慢动作，高饱和暖光食物通透光泽",
    "服饰鞋包": "全程慢速展示版型，特写面料纹理logo走线，环绕全身平移平铺，柔和漫射光真实色彩",
    "数码3C": "中快速功能切换加速，特写按键屏幕接口材质，45度斜推环绕固定，冷调产品光金属反光",
}

# ============================================================
# 功能属性专属规则（品类 × 功能属性 → 差异化规则）
# 优先级高于 CATEGORY_DESC，当 product_function 匹配时覆盖品类通用规则
# ============================================================
FUNCTION_ATTR_RULES = {
    # ---- 美妆护肤 ----
    ("美妆护肤", "遮盖修饰"): "节奏快→慢（先快速展示问题，慢速展示遮盖过程），特写瑕疵部位before/after对比、遮盖力变化、拍开边界，固定机位对比→微距推镜，音效轻点拍开声、叠加涂抹声，单侧硬光制造阴影凸显遮盖力，差异化关键：必须展示before/after对比，光影要强对比",
    ("美妆护肤", "色彩表达"): "节奏慢→快（慢展示色号质感，快展示上脸效果），特写唇部纹理/色泽层次、晕染边界、多肤色试色，微距推镜→环绕产品，音效开盖声、涂抹声，柔和水光低对比（还原真实色），差异化关键：多肤色试色，自然光下真实肤色展示",
    ("美妆护肤", "质地体验"): "全程慢速（展示质地变化全过程），特写质地延展、吸收过程、水润→哑光/光泽变化，滴管慢动作→吸收延时，音效挖取声、拍打声，柔和侧光展示质地层次，差异化关键：必须展示质地变化全过程",
    ("美妆护肤", "工具辅助"): "中速（展示手法+效果），特写工具材质、使用手法、效果差异，手部动作特写→跟拍，音效工具摩擦声、弹响声，均匀柔光手部清晰，差异化关键：手法教学感，效果对比",
    ("美妆护肤", "持久定妆"): "中速（时间维度展示），特写刚上脸效果→几小时后持妆状态，扑粉瞬间慢镜头→时间切换，音效按压声、喷雾声，逆光展示光泽度/哑光度，差异化关键：必须展示时间维度对比",
    # ---- 食品零食 ----
    ("食品零食", "即食口感"): "整体快节奏、入口放慢，特写酥脆/丝滑质地、咀嚼表情、食物光泽，俯拍→微距入口→慢动作咀嚼，音效撕袋脆响、咀嚼声、嘎嘣声ASMR，高饱和暖光食物通透光泽，差异化关键：声音ASMR是核心，口感可视化",
    ("食品零食", "冲泡过程"): "前慢后快（冲泡慢，饮用快），特写粉末/液体融合、色泽变化、蒸汽，俯拍冲泡→微距滴落→搅拌环绕，音效倒水声、搅拌声、气泡声，暖光+蒸汽光晕，差异化关键：过程仪式感，色泽诱人",
    ("食品零食", "开箱仪式"): "全程慢速，特写包装质感、分层展示、赠品，开箱跟拍→平铺展示→环绕，音效撕拉包装、开箱惊喜声，柔和暖光包装反光，差异化关键：价值感知，赠品展示",
    ("食品零食", "健康功能"): "中速，特写成分表、质地、食用后状态，成分特写→食用过程→前后对比，音效健康感轻音乐、咀嚼声，自然光清新明亮，差异化关键：成分信任，效果承诺",
    # ---- 家居日用 ----
    ("家居日用", "便捷收纳"): "快节奏（展示便捷），特写使用前后对比、安装简便性，跟拍手部→快速安装，音效工具摩擦、卡扣声，均匀室内柔光，差异化关键：便捷性，一看就会",
    ("家居日用", "清洁效果"): "中速（问题→解决），特写污渍前后对比、清洁过程，固定机位对比→微距清洁，音效水流声、摩擦声、泡沫声，侧逆光对比（看清污渍/洁净），差异化关键：before/after必须强烈",
    ("家居日用", "舒适体验"): "慢速（展示舒适感），特写材质柔软度、使用姿态、放松表情，慢动作按压→身体接触特写，音效柔软摩擦声、叹息声，柔和暖光温馨氛围，差异化关键：舒适感传递，情绪共鸣",
    ("家居日用", "耐用品质"): "中速（展示耐用），特写材质细节、使用痕迹、承重测试，微距材质→使用过程→测试，音效金属碰撞、切割声，冷调产品光金属反光，差异化关键：耐用性证明，质量信任",
    ("家居日用", "效果对比"): "快→慢（先展示问题，慢展示效果），特写使用前后差异、对比效果，固定机位对比→微距细节，音效问题音→效果音变化，侧逆光凸显对比，差异化关键：差异必须肉眼可见",
    # ---- 服饰鞋包 ----
    ("服饰鞋包", "日常百搭"): "中速（展示搭配），特写面料纹理、多场景搭配、版型，全身平移→搭配切换→平铺，音效布料摩擦、脚步声，柔和漫射光真实色彩，差异化关键：百搭性，一衣多穿",
    ("服饰鞋包", "场景氛围"): "慢速（展示氛围），特写整体氛围、场景融入、细节设计，环境环绕→动态展示→场景切换，音效环境音、节奏BGM，场景光（舞台光/自然光/运动光），差异化关键：场景代入，情感共鸣",
    ("服饰鞋包", "功能实测"): "中速（展示功能），特写功能细节、实测过程、效果，功能特写→测试过程→对比，音效功能音效（雨声/摩擦声），真实环境光、功能对比光，差异化关键：功能实测，效果证明",
    ("服饰鞋包", "品质工艺"): "慢速（展示工艺），特写皮革纹理、缝线细节、五金质感，微距工艺→环绕展示→手部触摸，音效皮革摩擦、金属扣声，侧光展示质感层次、高端冷光，差异化关键：工艺细节，品质信任",
    # ---- 数码3C ----
    ("数码3C", "性能参数"): "中快速（展示性能），特写跑分界面、游戏帧率、加载速度，屏幕录制→45°斜推→环绕，音效科技BGM、按键提示音，冷调产品光、屏幕发光，差异化关键：参数可视化，性能震撼",
    ("数码3C", "便捷易用"): "中速（展示便捷），特写一键操作、连接过程、使用场景，手部操作特写→场景切换，音效连接提示音、操作反馈音，柔和室内光、产品发光，差异化关键：易用性，一看就会",
    ("数码3C", "外观设计"): "慢速（展示设计），特写材质细节、色彩层次、佩戴效果，环绕展示→佩戴特写→光影变化，音效轻音乐、佩戴声，多光位展示质感、金属/玻璃反光，差异化关键：设计美学，颜值吸引",
    ("数码3C", "耐用品质"): "中速（展示耐用），特写材质强度、接口细节、弯折测试，微距材质→测试过程→使用场景，音效耐用测试声、使用声，均匀产品光细节清晰，差异化关键：耐用性证明，质量信任",
}

# ============================================================
# 用户痛点 → 镜头策略调整
# ============================================================
PAIN_POINT_RULES = {
    "遮不住": "强化before/after对比，特写遮盖力变化，单侧硬光凸显遮盖效果，增加对比镜",
    "太干卡纹": "展示质地延展性，特写推开瞬间水润感，强调滋润保湿效果",
    "不知道色号": "增加多肤色试色对比，自然光下真实效果展示，色调对比清晰",
    "容易掉色": "展示持久测试（喝水/擦拭），时间维度对比，锁定效果展示",
    "不好吃": "强化口感可视化，咀嚼ASMR放大，表情反应真实记录，诱人特写",
    "不会用": "手法教学式展示，分步骤操作特写，简易标签式字幕引导",
    "太贵": "价值感知强化，性价比计算，日常使用成本拆分，使用频次展示",
    "不耐用": "耐用测试展示，长时间使用对比，材质强度可视化，承重/弯折实测",
    "充电慢": "充电速度实测对比，时间线可视化，快充效果展示",
    "发热严重": "散热功能展示，温度实测对比，长时间使用稳定性展示",
    "收纳乱": "使用前后空间对比，收纳效果可视化，井井有条的整理过程",
    "清洁难": "清洁过程展示，去污效果对比，省力省时直观化",
    "操作复杂": "简化操作步骤展示，一键式便捷演示，老人/小孩也能轻松上手",
    "效果不明显": "使用前后强烈对比，效果渐变展示，周期效果呈现",
    "占空间": "收纳前后空间对比，折叠/拆卸展示，小巧便携突出",
    "不贴合": "贴合度特写展示，边缘细节看，多角度贴合测试",
    "噪音大": "静音效果对比测试，分贝数值可视化，安静环境对比",
    "伤皮肤": "温和成分展示，敏感肌适用测试，肤感温和实测",
}

# ============================================================
# 场景基底
# ============================================================
SCENE_BASE = {
    ("痛点解决", "家居日用"): "室内居家客厅/卧室，日常杂乱感的真实家庭环境",
    ("痛点解决", "美妆护肤"): "室内梳妆台/洗漱间镜前，整洁真实的美妆护理场景",
    ("痛点解决", "食品零食"): "室内厨房/餐厅，日常生活饮食场景",
    ("痛点解决", "服饰鞋包"): "室内玄关/衣帽间，日常出门前场景",
    ("痛点解决", "数码3C"): "室内书房/办公桌，电子设备使用场景",
    ("UGC种草", "家居日用"): "明亮客厅，生活博主vlog风格日常场景",
    ("UGC种草", "美妆护肤"): "卧室窗边梳妆台，博主护肤vlog场景",
    ("UGC种草", "食品零食"): "室内餐桌或休闲区，茶饮美食分享场景",
    ("UGC种草", "服饰鞋包"): "衣帽间全身镜前，穿搭分享场景",
    ("UGC种草", "数码3C"): "桌面工作区，数码产品日常使用场景",
    ("产品演示", "家居日用"): "简洁室内空间，干净操作区",
    ("产品演示", "美妆护肤"): "简洁桌面试用区，专业护肤操作场景",
    ("产品演示", "食品零食"): "简洁厨房操作台，食品加工演示",
    ("产品演示", "服饰鞋包"): "简洁室内全身镜/平铺展示区",
    ("产品演示", "数码3C"): "简洁桌面工作区，数码操作演示",
    ("开箱种草", "家居日用"): "博主家中整洁桌面开箱布置",
    ("开箱种草", "美妆护肤"): "梳妆台前美妆开箱布景",
    ("开箱种草", "食品零食"): "厨房岛台零食开箱摆盘",
    ("开箱种草", "服饰鞋包"): "衣帽间客厅地毯开箱场景",
    ("开箱种草", "数码3C"): "桌面开箱区数码布景",
    ("CTA带货", "家居日用"): "生活化场景产品居中展示",
    ("CTA带货", "美妆护肤"): "梳妆台产品居中美妆氛围",
    ("CTA带货", "食品零食"): "餐桌产品居中诱人摆盘",
    ("CTA带货", "服饰鞋包"): "简洁背景产品居中模特展示",
    ("CTA带货", "数码3C"): "简洁桌面产品居中科技背景",
}

# ============================================================
# 场景修饰（品类 × 镜头功能 → 具体画面提示）
# ============================================================
VISUAL_HINTS = {
    ("家居日用", "痛点冲击"): "展示无产品时的麻烦和困扰，衣物沾满毛发难以清理，表情困扰焦虑",
    ("家居日用", "产品亮相"): "完整展示粘毛器外观造型，镜头缓慢推近突出热熔滚轮和手柄设计",
    ("家居日用", "实操演示"): "手持产品在衣物上滚动操作，毛发被轻松粘走，动作顺滑流畅",
    ("家居日用", "效果对比"): "使用前后对比，左边沾满毛发，右边干净如新，差异明显",
    ("家居日用", "推荐CTA"): "手持产品微笑推荐，展示干净衣物和产品，热情呼吁行动",
    ("美妆护肤", "痛点冲击"): "展示皮肤问题如干燥暗沉，表情困扰不自信",
    ("美妆护肤", "产品亮相"): "精华液瓶身完整展示，缓慢旋转突出瓶身设计和质地",
    ("美妆护肤", "实操演示"): "挤压精华液于掌心，涂抹于面部，质地推开瞬间水润光泽",
    ("美妆护肤", "效果对比"): "左右脸对比，使用侧水润透亮有光泽，未使用侧干燥暗沉",
    ("食品零食", "产品亮相"): "包装完整展示，突出品牌和产品名称",
    ("食品零食", "实操演示"): "打开包装倒出内容物，热气腾腾或酥脆声响",
    ("数码3C", "产品亮相"): "产品45度斜放展示全貌，金属质感反光流转",
    ("数码3C", "核心功能演示1"): "手指点击屏幕/按下按键，界面响应流畅或功能启动",
    ("数码3C", "价格下单引导"): "产品居中展示，价格标签醒目弹出，购物车图标动画",
}


def load_env_sudocode_key() -> str:
    """Load Sudocode API key from env var or .env"""
    key = os.environ.get("SUDOCODE_API_KEY", "")
    if key:
        return key
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir] + list(script_dir.parents):
        env_path = parent / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SUDOCODE_API_KEY="):
                        return line.split("=", 1)[1].strip().strip("\"'")
            break
    return ""


def call_llm(prompt: str, system: str = "") -> str:
    """Call Sudocode gpt-5.4-mini API"""
    if requests is None:
        raise RuntimeError("requests module not available, cannot call AI")
    key = load_env_sudocode_key()
    if not key:
        raise RuntimeError("SUDOCODE_API_KEY not found in .env")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": "gpt-5.4-mini", "messages": messages, "max_tokens": 4096, "temperature": 0.7}
    resp = requests.post("https://sudocode.run/v1/chat/completions", json=payload, headers=headers, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict:
    """Extract JSON from AI response (handles <think> tags, markdown code fences, trailing commas)"""
    text = text.strip()
    # Remove <think> reasoning tags (the model outputs thinking before JSON)
    if "<think>" in text and "</think>" in text:
        text = text.split("</think>")[-1].strip()
    # Remove markdown code fences
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    # Find JSON boundaries: first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        text = text[first_brace:last_brace+1]
    # Remove trailing commas before ] or }
    import re
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return json.loads(text)


def build_generation_prompt(cfg: dict, video_type: str, category: str, market: str, duration: int, product_refs: list, details: str = "", angle: str = "", product_function: str = "", user_pain_point: str = "") -> str:
    """Build the prompt for AI storyboard generation"""
    country = COUNTRY_CONFIG.get(market, COUNTRY_CONFIG["thailand"])
    vt_cfg = VIDEO_TYPE_STRUCTURE[video_type]
    dur_key = f"{duration}s"
    dur_cfg = vt_cfg[dur_key]

    product_name = cfg.get("商品名称", cfg.get("product_name", ""))
    main_sell = cfg.get("核心卖点", {}).get("主卖点", "")
    second_sell = cfg.get("核心卖点", {}).get("次卖点", [])
    audience = cfg.get("适用人群", "")
    scenario = cfg.get("适用场景", "")
    price = cfg.get("price", "")
    hook_points = cfg.get("hook_points", "")
    scene_key = (video_type, category)
    scene_base = SCENE_BASE.get(scene_key, "简洁室内家庭环境")
    cat_desc = CATEGORY_DESC.get(category, "中速自然节奏")

    # 功能属性规则（优先级高于品类通用规则）
    func_rule = FUNCTION_ATTR_RULES.get((category, product_function), "")
    func_rule_section = f"\n 【产品功能属性：{product_function}】\n 功能属性专属规则（优先级高于品类通用规则）：{func_rule}\n" if product_function and func_rule else ""
    # 用户痛点策略
    pain_rule = PAIN_POINT_RULES.get(user_pain_point, "")
    pain_rule_section = f"\n 【用户痛点：{user_pain_point}】\n 痛点对应的镜头策略：{pain_rule}\n" if user_pain_point and pain_rule else ""

    # Build shot structure description
    functions = dur_cfg["functions"]
    durations = dur_cfg["durations"]
    shot_lines = []
    for i, (func, d) in enumerate(zip(functions, durations), 1):
        shot_lines.append(f"  镜{i}: 功能=[{func}], 时长={d}秒")

    hint_lines = []
    for (cat_k, func_k), hint in VISUAL_HINTS.items():
        if cat_k == category:
            hint_lines.append(f"    {func_k}: {hint}")

    # Build reference images section
    ref_lines = []
    labels = ["产品白底图", "三视图", "产品细节图"]
    for i, path in enumerate(product_refs):
        label = labels[i] if i < len(labels) else f"产品参考图{i+1}"
        ref_lines.append(f"  {label}：@{path}")
    ref_section = "\n".join(ref_lines)

    details_section = f"\n细节说明：{details}" if details else ""
    angle_section = f"\n视频角度：{angle}" if angle else ""

    prompt = f"""你是一个专业的电商短视频分镜脚本创作专家。请根据以下信息生成一个{duration}秒的{video_type}类型爆款短视频分镜脚本。

【商品信息】
商品名称：{product_name}
核心卖点：主卖点「{main_sell}」，次卖点「{'、'.join(second_sell)}」
适用人群：{audience}
适用场景：{scenario}
产品参考图：
{ref_section}{details_section}{angle_section}{f'''
价格信息：{price}''' if price else ''}{f'''
吸睛点：{hook_points}''' if hook_points else ''}

【目标市场：{market}】
人物特征（必须参考商品适用人群来设定）：适用人群为「{audience}」，请据此设定人物的身份、年龄层、生活状态和穿搭风格
场景风格辅助：{country['scene_decor']}
场景内容（必须参考商品适用场景来安排）：适用场景为「{scenario}」，所有镜头画面必须围绕这些场景展开
台词/字幕语言：{country['lang_name']}
光影偏好：{country['lighting_adj']}
BGM风格：{country['bgm_style']}
沟通风格：{country['emotion']}

【视频类型：{video_type}】
结构说明：{vt_cfg['description']}
固定镜头框架：
{chr(10).join(shot_lines)}

 【产品品类：{category}】
 品类拍摄规则：{cat_desc}
 基础场景：{scene_base}
 {func_rule_section}{pain_rule_section}
 【品类 × 镜头功能 画面提示】
 {chr(10).join(hint_lines) if hint_lines else "根据品类特征和镜头功能自然生成"}

 【输出要求】
请严格按以下JSON格式输出（不要加markdown代码块标记，直接输出纯JSON）：

```json
{{
  "镜头脚本": [
    {{
      "镜号": 1,
      "单镜时长": "{durations[0]}s",
      "景别": "根据功能选择最合适的景别",
      "运镜": "根据功能选择最合适的运镜方式",
      "拍摄角度": "根据功能选择最合适的角度",
      "画面内容": "用生动自然的中文描述画面，人物动作、产品交互、场景细节，出现产品时直接用产品名称（如'{product_name}'），不要使用@product_ref引用路径",
      "本地台词": "用{country['lang_name']}写台词",
      "本地字幕": "用{country['lang_name']}写短字幕/弹幕，可加emoji",
      "音效_BGM": "描述音效和背景音乐",
      "光影色调": "描述光影风格和色调",
      "真实感约束": "明确真实感要求，如产品外观统一、皮肤质感、动作自然等"
    }}
    // ... 共{len(functions)}镜
  ]
}}
```

**创作要点：**
1. 画面内容要生动自然、有画面感，像人类导演写的分镜描述
2. 每镜的景别/运镜/角度根据内容自然选择，避免重复
3. 台词用{country['lang_name']}，要符合当地口语习惯
4. 字幕要简短带emoji，适合短视频弹幕风格
5. 音效和BGM描述要具体，包括ASAMR细节
6. 画面中出现产品时直接用产品名称「{product_name}」，不要使用@product_ref或任何引用路径
7. 整体要有情绪起伏，符合爆款短视频节奏
8. 【优先级】当【产品功能属性】和【用户痛点】有内容时，其规则优先级高于品类通用规则，镜头设计必须以功能属性和痛点为先

【字数约束】
整段视频脚本（含所有镜头的画面/台词/字幕/音效/光影/真实感描述）最终给视频模型的总字数不能超过2000字。撰写每个镜头时请控制画面描述的长度，确保{len(functions)}镜的总内容不超过2000字。画面描述保持生动但不啰嗦，每镜画面内容控制在200-400字之间为宜。"""
    return prompt


def generate_storyboard(cfg: dict, product_img_paths: list, video_type: str, category: str,
                        market: str, duration: int, output_dir: str, details: str = "", angle: str = "",
                        product_function: str = "", user_pain_point: str = ""):
    os.makedirs(output_dir, exist_ok=True)

    product_refs = [p for p in product_img_paths if os.path.exists(p)]
    if not product_refs:
        product_refs = ["product_layer.png"]
    product_name = cfg.get("商品名称", cfg.get("product_name", ""))
    country = COUNTRY_CONFIG.get(market, COUNTRY_CONFIG["thailand"])
    # 从cfg中继承（如果CLI未传但cfg中有）
    if not product_function:
        product_function = cfg.get("product_function", "")
    if not user_pain_point:
        user_pain_point = cfg.get("user_pain_point", "")

    # Build prompt and call AI
    prompt = build_generation_prompt(cfg, video_type, category, market, duration, product_refs, details, angle, product_function, user_pain_point)

    print(f"  正在调用AI生成 {video_type}/{market}/{duration}s 分镜脚本...")
    print(f"  提示词长度: {len(prompt)} 字符")
    if details:
        print(f"  细节说明: {details[:80]}...")
    if angle:
        print(f"  视频角度: {angle[:80]}...")

    try:
        response = call_llm(prompt)
        print(f"  AI响应长度: {len(response)} 字符")
        result = extract_json(response)
    except Exception as e:
        print(f"  AI调用失败: {e}")
        print(f"  使用规则备份生成...")
        result = _fallback_generate(cfg, product_refs, video_type, category, market, duration, country, details, angle, product_function, user_pain_point)

    shot_list = result.get("镜头脚本", [])
    if not shot_list:
        print("  AI未生成有效镜头，使用规则备份")
        result = _fallback_generate(cfg, product_refs, video_type, category, market, duration, country, details, angle, product_function, user_pain_point)
        shot_list = result.get("镜头脚本", [])

    # ================================================================
    # Output files
    # ================================================================
    product_slug = product_name.replace(" ", "_")

    # Ref images section
    labels = ["产品白底图", "三视图", "产品细节图"]
    ref_section_lines = []
    for i, path in enumerate(product_refs):
        label = labels[i] if i < len(labels) else f"产品参考图{i+1}"
        ref_section_lines.append(f"@{path}  ← {label}")

    # Build final JSON with 3-section format
    json_output = {
        f"{product_name}产品参考图": "\n".join(ref_section_lines),
        "人物形象特征参考": f"根据适用人群「{cfg.get('适用人群', '')}」设定：{country['people']}，{country['emotion']}沟通风格，穿搭适合{category}使用场景（适用场景：{cfg.get('适用场景', '')}）",
        "镜头脚本": shot_list,
    }
    if details:
        json_output["细节说明"] = details
    if angle:
        json_output["视频角度"] = angle
    if product_function:
        json_output["产品功能属性"] = product_function
    if user_pain_point:
        json_output["用户痛点"] = user_pain_point

    json_path = os.path.join(output_dir, f"{product_slug}_{market}_{video_type}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    # Markdown
    lines = []
    lines.append(f"# {product_name} 视频脚本")
    lines.append("")
    lines.append(f"### {product_name}产品参考图")
    for line in ref_section_lines:
        lines.append(line)
    lines.append("")
    if details:
        lines.append("### 细节说明")
        lines.append(details)
        lines.append("")
    if angle:
        lines.append("### 视频角度")
        lines.append(angle)
        lines.append("")
    if product_function:
        lines.append("### 产品功能属性")
        lines.append(product_function)
        lines.append("")
    if user_pain_point:
        lines.append("### 用户痛点")
        lines.append(user_pain_point)
        lines.append("")
    lines.append("### 人物形象特征参考")
    lines.append(f"根据适用人群「{cfg.get('适用人群', '')}」设定：{country['people']}，{country['emotion']}沟通风格，穿搭适合{category}使用场景（适用场景：{cfg.get('适用场景', '')}）")
    lines.append("")
    lines.append("### 镜头脚本")
    lines.append("| 镜号 | 单镜时长 | 景别 | 运镜 | 拍摄角度 | 画面内容 | 本地台词 | 本地字幕/弹幕 | 音效+BGM | 光影色调 | 真实感约束 |")
    lines.append("|------|----------|------|------|----------|------------------------------------------|----------|---------------|----------|----------|------------|")
    for s in shot_list:
        lines.append(
            f"| {s.get('镜号','')} | {s.get('单镜时长','')} | {s.get('景别','')} | {s.get('运镜','')} | "
            f"{s.get('拍摄角度','')} | {s.get('画面内容','')} | {s.get('本地台词','')} | "
            f"{s.get('本地字幕','')} | {s.get('音效_BGM','')} | {s.get('光影色调','')} | {s.get('真实感约束','')} |"
        )

    md_path = os.path.join(output_dir, f"{product_slug}_{market}_{video_type}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    shot_count = len(shot_list)
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")
    print(f"\n  完成! {shot_count} 镜, {duration}s")
    print(f"  类型: {video_type} | 品类: {category} | 市场: {market}")

    _print_chat_markdown(product_name, video_type, category, market, duration, shot_count, output_dir)


def _fallback_generate(cfg, product_refs, video_type, category, market, duration, country, details="", angle="", product_function="", user_pain_point=""):
    """Rule-based fallback when AI is unavailable"""
    vt_cfg = VIDEO_TYPE_STRUCTURE[video_type]
    dur_cfg = vt_cfg[f"{duration}s"]
    functions = dur_cfg["functions"]
    durations = dur_cfg["durations"]
    product_name = cfg.get("商品名称", cfg.get("product_name", ""))
    scene_key = (video_type, category)
    scene_base = SCENE_BASE.get(scene_key, "简洁室内家庭环境")
    # 功能属性规则（若有则用作镜头提示）
    func_rule_str = FUNCTION_ATTR_RULES.get((category, product_function), "")
    pain_str = PAIN_POINT_RULES.get(user_pain_point, "")

    shot_list = []
    for i, (func, dur) in enumerate(zip(functions, durations), 1):
        hint_key = (category, func)
        visual_hint = VISUAL_HINTS.get(hint_key, f"展示{product_name}的{func}场景")
        has_product = func not in ["痛点冲击", "日常场景代入"]
        product_note = f"，展示{product_name}" if has_product else "，无产品出镜"
        detail_note = f"。细节说明：{details[:60]}…" if details else ""
        func_note = f"。功能属性规则：{func_rule_str[:60]}…" if func_rule_str else ""
        pain_note = f"。痛点策略：{pain_str[:60]}…" if pain_str else ""

        shot = {
            "镜号": i,
            "单镜时长": f"{dur}s",
            "景别": "近景" if i % 2 == 0 else "特写",
            "运镜": "固定" if i % 3 == 0 else "缓慢推镜",
            "拍摄角度": "平视" if i % 2 == 0 else "侧拍",
            "画面内容": f"{country['people']}在{scene_base}中{visual_hint}{product_note}{detail_note}{func_note}{pain_note}，{country['scene_decor']}",
            "本地台词": f"[{country['lang_name']}台词]",
            "本地字幕": f"[{country['lang_name']}字幕✨]",
            "音效_BGM": f"{country['bgm_style']}背景音乐",
            "光影色调": country["lighting_adj"],
            "真实感约束": f"产品外观与{product_name}完全统一，人物表情自然不僵硬",
        }
        shot_list.append(shot)

    return {"镜头脚本": shot_list}


def _print_chat_markdown(product_name, video_type, category, market, duration, shot_count, output_dir):
    """Print formatted markdown for chat display"""
    md = _format_storyboard_markdown(product_name, video_type, category, market, duration, shot_count, output_dir)
    print("\n" + "=" * 60)
    print("ARKCLAW_CHAT_OUTPUT")
    print("=" * 60)
    print(md)


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="AI电商分镜脚本生成器（AI驱动版）")
    parser.add_argument("--product-img", "-p", nargs="+", required=True, help="产品参考图路径（白底图 三视图 产品细节图，可传多个，用空格分隔）")
    parser.add_argument("--config", "-c", required=True, help="商品卖点JSON路径")
    parser.add_argument("--video-type", "-t", required=True, choices=list(VIDEO_TYPE_STRUCTURE.keys()), help="视频类型")
    parser.add_argument("--category", "-cat", default="家居日用", choices=list(CATEGORY_DESC.keys()), help="产品品类")
    parser.add_argument("--market", "-m", default="thailand", choices=list(COUNTRY_CONFIG.keys()), help="目标市场")
    parser.add_argument("--duration", "-d", type=int, default=15, choices=[10, 15], help="视频时长 10或15秒")
    parser.add_argument("--details", default="", help="细节说明（可选，生成脚本时参考）")
    parser.add_argument("--angle", default="", help="视频想法角度（可选，如'从产品开箱切入'等，生成脚本时参考）")
    parser.add_argument("--product-function", default="", help="产品功能属性（如'遮盖修饰'/'即食口感'/'便捷收纳'等，可选，优先级高于品类通用规则）")
    parser.add_argument("--pain-point", default="", help="用户核心痛点（如'遮不住'/'不好吃'/'收纳乱'等，可选，调整镜头重点）")
    parser.add_argument("--output", "-o", default=_default_output_dir(), help="输出目录（默认桌面AI视频脚本文件夹）")
    parser.add_argument("--output-format", default="json", choices=["json", "markdown"], help="输出格式: json(文件)|markdown(聊天展示)")
    args = parser.parse_args()

    missing = [p for p in args.product_img if not os.path.exists(p)]
    if missing:
        print(f"错误: 以下图片不存在: {missing}")
        sys.exit(1)

    cfg = load_config(args.config)

    generate_storyboard(
        cfg=cfg,
        product_img_paths=args.product_img,
        video_type=args.video_type,
        category=args.category,
        market=args.market,
        duration=args.duration,
        output_dir=args.output,
        details=args.details,
        angle=args.angle,
        product_function=args.product_function,
        user_pain_point=args.pain_point,
    )


if __name__ == "__main__":
    main()
