from __future__ import annotations

import json
import math
import re
from pathlib import Path

LOCALIZATION_PATH = "Scripts/Localization.gd"
PIXEL_FONT_RESOURCE = "res://UI/Fonts/04B_03__.TTF"
SIZE_CATEGORIES = ("general_ui", "description", "quest", "hud_world", "chat", "popup")

# These scripts retain their own font reference, bypassing the default Theme.
DIRECT_FONT_SCRIPTS = (
    "Scenes/Map/Map Objects/map_object.gd",
    "Scenes/Player/character.gd",
    "Scenes/UI/auto_potion_panel.gd",
    "Scenes/UI/chatbox_message.gd",
    "Scenes/UI/color_selection_window.gd",
    "Scenes/UI/crafting_complete_popup.gd",
    "Scenes/UI/guild_perk_slot.gd",
    "Scenes/UI/invite_banner.gd",
    "Scenes/UI/level_up_popup.gd",
    "Scenes/UI/loot_banner.gd",
    "Scenes/UI/price_history_graph.gd",
)


def payload_paths() -> list[str]:
    return [LOCALIZATION_PATH, *DIRECT_FONT_SCRIPTS]


def build_payload(
    source: dict[str, bytes],
    pixel_font_path: Path | None,
    traditional_font_path: Path | None,
    size_scales: dict[str, float] | None = None,
) -> dict[str, bytes]:
    localization = source[LOCALIZATION_PATH].decode("utf-8")
    pixel_path = _gd_path(pixel_font_path)
    traditional_path = _gd_path(traditional_font_path)
    scales = _validated_scales(size_scales)
    scale_literal = json.dumps(scales, ensure_ascii=False, sort_keys=True)

    old_loader = '''\tvar PI1O0tA : Font = null
\tif r9CenZs != "" and ResourceLoader.exists(r9CenZs):
\t\tPI1O0tA = load(r9CenZs)
\tif PI1O0tA == null and r9CenZs != "":'''
    new_loader = '''\tvar PI1O0tA : Font = null
\tvar sr_custom_path := _srfont_path_for_mode(qn86QKV())
\tif sr_custom_path != "":
\t\tPI1O0tA = _srfont_load_external(sr_custom_path)
\telif r9CenZs != "" and ResourceLoader.exists(r9CenZs):
\t\tPI1O0tA = load(r9CenZs)
\tif PI1O0tA == null and (r9CenZs != "" or sr_custom_path != ""):'''
    localization = _replace_once(localization, old_loader, new_loader, "字型載入區塊")

    old_early_return = '''\tif Vy6tJob == 1.0 and r9CenZs == "" and AEhzjvY == 1.0 \\
\t\t\tand not hLjyYsj and bwFCPma == null and W2abyvk == null:
\t\treturn'''
    new_early_return = '''\tif Vy6tJob == 1.0 and r9CenZs == "" and AEhzjvY == 1.0 \\
\t\t\tand not hLjyYsj and bwFCPma == null and W2abyvk == null \\
\t\t\tand _srfont_path_for_mode(qn86QKV()) == "" \\
\t\t\tand not _srfont_has_size_overrides():
\t\treturn'''
    localization = _replace_once(localization, old_early_return, new_early_return, "語系快速返回區塊")

    old_nh = '''func nhTAj3u(PKAwIwN : Font) -> Font:
\tif k54CPsP != null and PKAwIwN != null \\
\t\t\tand PKAwIwN.resource_path in WRZ4D7V:
\t\treturn k54CPsP
\treturn PKAwIwN'''
    new_nh = '''func nhTAj3u(PKAwIwN : Font) -> Font:
\tif k54CPsP != null and PKAwIwN != null \\
\t\t\tand PKAwIwN.resource_path in WRZ4D7V:
\t\treturn srfont_for(k54CPsP)
\treturn srfont_for(PKAwIwN)'''
    localization = _replace_once(localization, old_nh, new_nh, "直接字型轉換函式")

    old_yq = '''func YQUTyMs() -> bool:
\treturn AEhzjvY != 1.0 or k54CPsP != null'''
    new_yq = '''func YQUTyMs() -> bool:
\treturn AEhzjvY != 1.0 or k54CPsP != null \\
\t\t\tor _srfont_path_for_mode(qn86QKV()) != "" \\
\t\t\tor _srfont_has_size_overrides()'''
    localization = _replace_once(localization, old_yq, new_yq, "UI 字型處理條件")

    localization = _replace_once(
        localization,
        'const kDyxfQv := ["font", "normal_font"]',
        '''const kDyxfQv := [
\t"font", "normal_font", "bold_font", "italics_font",
\t"bold_italics_font", "mono_font", "title_font",
\t"font_separator", "font_accelerator", "title_button_font",
]''',
        "Theme 字型名稱清單",
    )

    localization = _replace_once(
        localization,
        '''\tif hUxk0s_ is Control and not hUxk0s_.is_in_group(DbzdOl4):''',
        '''\tif (hUxk0s_ is Control or hUxk0s_ is Window) and ( \\
\t\t\tnot hUxk0s_.is_in_group(DbzdOl4) \\
\t\t\tor _srfont_path_for_mode(qn86QKV()) != "" \\
\t\t\tor _srfont_has_size_overrides()):''',
        "固定字型群組排除條件",
    )
    localization = _replace_once(
        localization,
        "\t\tvar fZBXjsn := hUxk0s_ as Control",
        "\t\tvar fZBXjsn = hUxk0s_",
        "Control／Window Theme 節點",
    )

    localization = _replace_once(
        localization,
        "func Ii8vLFF(hUxk0s_ : Node) -> void:",
        "func Ii8vLFF(hUxk0s_ : Node, sr_recurse : bool = true) -> void:",
        "UI 遞迴函式",
    )
    localization = _replace_once(
        localization,
        '''\tfor agM_aRO in hUxk0s_.get_children(true):
\t\tIi8vLFF(agM_aRO)''',
        '''\tif not sr_recurse:
\t\treturn
\tfor agM_aRO in hUxk0s_.get_children(true):
\t\tIi8vLFF(agM_aRO)''',
        "UI 子節點遞迴位置",
    )

    localization = _replace_once(
        localization,
        "\t\t\tvar Ql0hEW5 : Font = k54CPsP if k54CPsP != null else a6l1_JC[GjwG6uc]",
        "\t\t\tvar Ql0hEW5 : Font = nhTAj3u(a6l1_JC[GjwG6uc])",
        "UI 字型覆寫位置",
    )
    localization = _replace_once(
        localization,
        '''\t\t\t\t\tif EBFvvZ6 == null or not (EBFvvZ6.resource_path in WRZ4D7V):
\t\t\t\t\t\tcontinue''',
        '''\t\t\t\t\tif EBFvvZ6 == null:
\t\t\t\t\t\tcontinue''',
        "匿名 Theme 字型判斷",
    )

    old_size_loop = '''\t\tvar hkeraqC : Dictionary = epFBHZp.get(PQJofSx, {})
\t\tfor GjwG6uc in oun1gb0:
\t\t\tvar hF859FM : bool = hkeraqC.has(GjwG6uc)
\t\t\tif not hF859FM and not fZBXjsn.has_theme_font_size_override(GjwG6uc):
\t\t\t\tcontinue
\t\t\tif not hF859FM:
\t\t\t\thkeraqC[GjwG6uc] = fZBXjsn.get_theme_font_size(GjwG6uc)
\t\t\tvar jnWdebw : int = sV2xmuS(hkeraqC[GjwG6uc])
\t\t\tif mYHnOM5 and hkeraqC[GjwG6uc] > FnkVleY:
\t\t\t\tjnWdebw = clampi(int(round(hkeraqC[GjwG6uc] * AL23xGl)),
\t\t\t\t\t\tFnkVleY, hkeraqC[GjwG6uc])
\t\t\tif fZBXjsn.get_theme_font_size(GjwG6uc) != jnWdebw:
\t\t\t\tfZBXjsn.add_theme_font_size_override(GjwG6uc, jnWdebw)
\t\tif not hkeraqC.is_empty():
\t\t\tepFBHZp[PQJofSx] = hkeraqC'''
    new_size_loop = '''\t\tvar hkeraqC : Dictionary = epFBHZp.get(PQJofSx, {})
\t\tvar sr_category_scale := _srfont_size_scale_for(fZBXjsn)
\t\tfor GjwG6uc in _srfont_size_names(fZBXjsn):
\t\t\tvar sr_has_override : bool = bool(
\t\t\t\tfZBXjsn.has_theme_font_size_override(GjwG6uc))
\t\t\tif not hkeraqC.has(GjwG6uc):
\t\t\t\tvar sr_base_size : int = int(fZBXjsn.get_theme_font_size(GjwG6uc))
\t\t\t\tif sr_base_size <= 0:
\t\t\t\t\tcontinue
\t\t\t\thkeraqC[GjwG6uc] = {
\t\t\t\t\t"value": sr_base_size, "had_override": sr_has_override,
\t\t\t\t\t"managed": false, "target": sr_base_size,
\t\t\t\t}
\t\t\tvar sr_record : Dictionary = hkeraqC[GjwG6uc]
\t\t\tvar sr_managed := bool(sr_record.get("managed", false))
\t\t\tif sr_has_override and sr_managed \\
\t\t\t\t\tand fZBXjsn.get_theme_font_size(GjwG6uc) != int(sr_record["target"]):
\t\t\t\tsr_record["value"] = fZBXjsn.get_theme_font_size(GjwG6uc)
\t\t\t\tsr_record["had_override"] = true
\t\t\t\tsr_record["managed"] = false
\t\t\t\tsr_managed = false
\t\t\telif sr_has_override and not sr_managed and not bool(sr_record["had_override"]):
\t\t\t\tsr_record["value"] = fZBXjsn.get_theme_font_size(GjwG6uc)
\t\t\t\tsr_record["had_override"] = true
\t\t\tvar sr_had_override := bool(sr_record["had_override"])
\t\t\tvar sr_original_size := int(sr_record["value"])
\t\t\tvar sr_game_size := sV2xmuS(sr_original_size) if sr_had_override else sr_original_size
\t\t\tif mYHnOM5 and sr_original_size > FnkVleY:
\t\t\t\tsr_game_size = clampi(int(round(sr_original_size * AL23xGl)),
\t\t\t\t\t\tFnkVleY, sr_original_size)
\t\t\tvar sr_target_size := maxi(1, int(round(sr_game_size * sr_category_scale)))
\t\t\tif is_equal_approx(sr_category_scale, 1.0) and not sr_had_override:
\t\t\t\tif bool(sr_record.get("managed", false)) and sr_has_override:
\t\t\t\t\tfZBXjsn.remove_theme_font_size_override(GjwG6uc)
\t\t\t\tsr_record["managed"] = false
\t\t\telse:
\t\t\t\tif not sr_has_override or fZBXjsn.get_theme_font_size(GjwG6uc) != sr_target_size:
\t\t\t\t\tfZBXjsn.add_theme_font_size_override(GjwG6uc, sr_target_size)
\t\t\t\tsr_record["managed"] = true
\t\t\t\tsr_record["target"] = sr_target_size
\t\tif not hkeraqC.is_empty():
\t\t\tepFBHZp[PQJofSx] = hkeraqC'''
    localization = _replace_once(localization, old_size_loop, new_size_loop, "分類字體大小區塊")

    old_refresh = '''\tif Vy6tJob != 1.0 or BpAubGA or k54CPsP != sXYbyrG:
\t\tvar aaPxiCg := sV2xmuS(l6RUQRa)'''
    new_refresh = '''\t_srfont_refresh_proxies()
\tif Vy6tJob != 1.0 or BpAubGA or k54CPsP != sXYbyrG \\
\t\t\tor _srfont_path_for_mode(qn86QKV()) != "" \\
\t\t\tor _srfont_has_size_overrides():
\t\tvar aaPxiCg := sV2xmuS(l6RUQRa)'''
    localization = _replace_once(localization, old_refresh, new_refresh, "UI 更新區塊")

    ready_anchor = "func _ready() -> void:\n"
    helpers = f'''const _SRFONT_PIXEL_PATH : String = {pixel_path}
const _SRFONT_TRADITIONAL_PATH : String = {traditional_path}
const _SRFONT_SIZE_SCALES : Dictionary = {scale_literal}
var _srfont_external_cache : Dictionary = {{}}
var _srfont_proxy_cache : Dictionary = {{}}
var _srfont_proxy_ids : Dictionary = {{}}
func _srfont_path_for_mode(sr_mode : int) -> String:
\tif sr_mode == Seoq0MK:
\t\treturn _SRFONT_TRADITIONAL_PATH
\treturn _SRFONT_PIXEL_PATH
func _srfont_has_size_overrides() -> bool:
\tfor sr_scale in _SRFONT_SIZE_SCALES.values():
\t\tif not is_equal_approx(float(sr_scale), 1.0):
\t\t\treturn true
\treturn false
func _srfont_control_context(sr_control : Node) -> String:
\tvar sr_parts := PackedStringArray()
\tvar sr_cursor : Node = sr_control
\twhile sr_cursor != null:
\t\tsr_parts.append(str(sr_cursor.name).to_lower())
\t\tvar sr_script = sr_cursor.get_script()
\t\tif sr_script != null and sr_script.resource_path != "":
\t\t\tsr_parts.append(sr_script.resource_path.to_lower())
\t\tif sr_cursor.scene_file_path != "":
\t\t\tsr_parts.append(sr_cursor.scene_file_path.to_lower())
\t\t\tbreak
\t\tsr_cursor = sr_cursor.get_parent()
\treturn " ".join(sr_parts)
func _srfont_size_category(sr_control : Node) -> String:
\tvar sr_context := _srfont_control_context(sr_control)
\tif "chatbox" in sr_context or "chat_pop" in sr_context or "chat_message" in sr_context:
\t\treturn "chat"
\tif "description_box" in sr_context or "tooltip" in sr_context:
\t\treturn "description"
\tif "quest_" in sr_context or "/quest" in sr_context:
\t\treturn "quest"
\tif "_popup" in sr_context or "_banner" in sr_context \\
\t\t\tor "notification" in sr_context or "death_screen" in sr_context:
\t\treturn "popup"
\tif "/hud." in sr_context or "/hot_slot." in sr_context \\
\t\t\tor "/character.gd" in sr_context or "/character.scn" in sr_context \\
\t\t\tor "map_object" in sr_context or "world_map" in sr_context:
\t\treturn "hud_world"
\treturn "general_ui"
func _srfont_size_scale_for(sr_control : Node) -> float:
\treturn float(_SRFONT_SIZE_SCALES.get(_srfont_size_category(sr_control), 1.0))
func _srfont_size_names(sr_control : Node) -> PackedStringArray:
\tvar sr_names := PackedStringArray()
\tconst sr_prefix := "theme_override_font_sizes/"
\tfor sr_property in sr_control.get_property_list():
\t\tvar sr_name := str(sr_property.get("name", ""))
\t\tif sr_name.begins_with(sr_prefix):
\t\t\tsr_names.append(sr_name.trim_prefix(sr_prefix))
\treturn sr_names
func _srfont_load_external(sr_path : String) -> FontFile:
\tif sr_path == "":
\t\treturn null
\tif _srfont_external_cache.has(sr_path):
\t\treturn _srfont_external_cache[sr_path]
\tvar sr_font := FontFile.new()
\tif sr_font.load_dynamic_font(sr_path) != OK:
\t\tpush_warning("[SRFONT] Failed to load " + sr_path)
\t\treturn null
\t_srfont_external_cache[sr_path] = sr_font
\treturn sr_font
func srfont_for(sr_original : Font) -> Font:
\tif sr_original == null:
\t\treturn sr_original
\tvar sr_original_id := sr_original.get_instance_id()
\tif _srfont_proxy_ids.has(sr_original_id):
\t\treturn sr_original
\tvar sr_active_path := _srfont_path_for_mode(qn86QKV())
\tif sr_active_path == "" and not (sr_original.resource_path in WRZ4D7V):
\t\treturn sr_original
\tvar sr_key := sr_original_id
\tif not _srfont_proxy_cache.has(sr_key):
\t\tvar sr_proxy := FontVariation.new()
\t\t_srfont_proxy_cache[sr_key] = {{"original": sr_original, "proxy": sr_proxy}}
\t\t_srfont_proxy_ids[sr_proxy.get_instance_id()] = true
\tvar sr_entry : Dictionary = _srfont_proxy_cache[sr_key]
\tvar sr_custom := _srfont_load_external(sr_active_path)
\tsr_entry["proxy"].base_font = sr_custom if sr_custom != null else sr_entry["original"]
\treturn sr_entry["proxy"]
func _srfont_refresh_proxies() -> void:
\tvar sr_custom := _srfont_load_external(_srfont_path_for_mode(qn86QKV()))
\tfor sr_key in _srfont_proxy_cache:
\t\tvar sr_entry : Dictionary = _srfont_proxy_cache[sr_key]
\t\tsr_entry["proxy"].base_font = sr_custom if sr_custom != null else sr_entry["original"]
\tprint("[SRFONT] ui_font=%d pixel=%s traditional=%s active=%s sizes=%s" % [
\t\tqn86QKV(), _SRFONT_PIXEL_PATH, _SRFONT_TRADITIONAL_PATH,
\t\t_srfont_path_for_mode(qn86QKV()), str(_SRFONT_SIZE_SCALES)])
func _srfont_node_added(sr_node : Node) -> void:
\tif not (sr_node is Control or sr_node is Window):
\t\treturn
\tif _srfont_path_for_mode(qn86QKV()) == "" and not _srfont_has_size_overrides():
\t\treturn
\t_srfont_apply_added.call_deferred(sr_node)
func _srfont_apply_added(sr_node) -> void:
\tif is_instance_valid(sr_node) and sr_node.is_inside_tree():
\t\tIi8vLFF(sr_node, false)
func _ready() -> void:
\tget_tree().node_added.connect(_srfont_node_added)
'''
    localization = _replace_once(localization, ready_anchor, helpers, "_ready()")

    result = {LOCALIZATION_PATH: localization.encode("utf-8")}
    for name in DIRECT_FONT_SCRIPTS:
        result[name] = _patch_direct_script(name, source[name].decode("utf-8")).encode("utf-8")
    return result


def _patch_direct_script(name: str, script: str) -> str:
    literal = re.escape(f'preload("{PIXEL_FONT_RESOURCE}")')
    replacement = f'Localization.srfont_for(load("{PIXEL_FONT_RESOURCE}"))'
    script, preload_count = re.subn(literal, replacement, script)
    if preload_count:
        script = re.sub(
            rf"(?m)^(\s*)const(\s+[^\n=]+(?:=|:=)\s*{re.escape(replacement)})",
            r"\1var\2",
            script,
        )

    plain_load = f'load("{PIXEL_FONT_RESOURCE}")'
    wrapped_load = f"Localization.srfont_for({plain_load})"
    if name.endswith("guild_perk_slot.gd"):
        script = script.replace(plain_load, wrapped_load)
    if name.endswith("auto_potion_panel.gd"):
        old = f'var mLO6BLl : FontFile = Utils.qsYXxNs("{PIXEL_FONT_RESOURCE}")'
        new = f'var mLO6BLl : Font = {wrapped_load}'
        script = _replace_once(script, old, new, f"{name} 字型載入")

    if PIXEL_FONT_RESOURCE not in script:
        raise RuntimeError(f"遊戲版本不相容：{name} 已找不到預期字型")
    return script


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Localization 模板版本不相容：找不到{label}")
    return text.replace(old, new, 1)


def _gd_path(path: Path | None) -> str:
    value = "" if path is None else path.resolve().as_posix()
    return json.dumps(value, ensure_ascii=False)


def _validated_scales(values: dict[str, float] | None) -> dict[str, float]:
    raw = values or {}
    result: dict[str, float] = {}
    for category in SIZE_CATEGORIES:
        value = float(raw.get(category, 1.0))
        if not math.isfinite(value) or not 0.10 <= value <= 3.00:
            raise ValueError(f"{category} 字體倍率必須介於 0.10～3.00")
        result[category] = value
    return result
