from pathlib import Path
from unittest import TestCase

from srfontmanager.payload import DIRECT_FONT_SCRIPTS, LOCALIZATION_PATH, build_payload


class PayloadTests(TestCase):
    def test_builds_mode_proxies_without_mutating_imported_fonts(self):
        source = {
            LOCALIZATION_PATH: b'''const WRZ4D7V := [
\t"res://UI/Fonts/04B_03__.TTF",
\t"res://UI/Fonts/Thixel.ttf",
]
const kDyxfQv := ["font", "normal_font"]
func nhTAj3u(PKAwIwN : Font) -> Font:
\tif k54CPsP != null and PKAwIwN != null \\
\t\t\tand PKAwIwN.resource_path in WRZ4D7V:
\t\treturn k54CPsP
\treturn PKAwIwN
func YQUTyMs() -> bool:
\treturn AEhzjvY != 1.0 or k54CPsP != null
func _ready() -> void:
\tvar Vy6tJob : float = float(naZAWHh.get("font_scale", 1.0))
\tvar r9CenZs : String = str(naZAWHh.get("font", ""))
\tif Vy6tJob == 1.0 and r9CenZs == "" and AEhzjvY == 1.0 \\
\t\t\tand not hLjyYsj and bwFCPma == null and W2abyvk == null:
\t\treturn
\tvar PI1O0tA : Font = null
\tif r9CenZs != "" and ResourceLoader.exists(r9CenZs):
\t\tPI1O0tA = load(r9CenZs)
\tif PI1O0tA == null and r9CenZs != "":
\tvar BpAubGA : bool = AEhzjvY != 1.0
\tif Vy6tJob != 1.0 or BpAubGA or k54CPsP != sXYbyrG:
\t\tvar aaPxiCg := sV2xmuS(l6RUQRa)
func Ii8vLFF(hUxk0s_ : Node) -> void:
\tif hUxk0s_ is Control and not hUxk0s_.is_in_group(DbzdOl4):
\t\tvar fZBXjsn := hUxk0s_ as Control
\t\t\t\t\tvar EBFvvZ6 : Font = fZBXjsn.get_theme_font(GjwG6uc)
\t\t\t\t\tif EBFvvZ6 == null or not (EBFvvZ6.resource_path in WRZ4D7V):
\t\t\t\t\t\tcontinue
\t\t\tvar Ql0hEW5 : Font = k54CPsP if k54CPsP != null else a6l1_JC[GjwG6uc]
\t\tvar hkeraqC : Dictionary = epFBHZp.get(PQJofSx, {})
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
\t\t\tepFBHZp[PQJofSx] = hkeraqC
\tfor agM_aRO in hUxk0s_.get_children(true):
\t\tIi8vLFF(agM_aRO)''',
        }
        for name in DIRECT_FONT_SCRIPTS:
            if name.endswith("auto_potion_panel.gd"):
                source[name] = b'var mLO6BLl : FontFile = Utils.qsYXxNs("res://UI/Fonts/04B_03__.TTF")'
            elif name.endswith("guild_perk_slot.gd"):
                source[name] = b'var F1LH0Pf = load("res://UI/Fonts/04B_03__.TTF")'
            else:
                source[name] = b'const test_font = preload("res://UI/Fonts/04B_03__.TTF")'

        result = build_payload(
            source,
            Path("C:/Fonts/pixel.ttf"),
            Path("C:/Fonts/traditional.otf"),
            {"general_ui": 0.9, "description": 1.1},
        )
        localization = result[LOCALIZATION_PATH].decode()

        self.assertIn("load_dynamic_font", localization)
        self.assertIn("FontVariation.new()", localization)
        self.assertIn("var sr_key := sr_original_id", localization)
        self.assertIn('"original": weakref(sr_original)', localization)
        self.assertIn('sr_original.has_meta("_srfont_proxy")', localization)
        self.assertNotIn("_srfont_proxy_ids", localization)
        self.assertNotIn("EBFvvZ6.resource_path in WRZ4D7V", localization)
        self.assertIn("bold_italics_font", localization)
        self.assertIn("get_tree().node_added.connect(_srfont_node_added)", localization)
        self.assertNotIn("theme_changed.connect", localization)
        self.assertNotIn("_srfont_theme_changed", localization)
        self.assertIn('"general_ui": 0.9', localization)
        self.assertIn("_srfont_size_category", localization)
        self.assertIn("_srfont_size_names", localization)
        self.assertIn("return PackedStringArray(oun1gb0)", localization)
        self.assertIn("if sr_proxy.base_font != sr_target:", localization)
        self.assertIn("_srfont_track_node(fZBXjsn)", localization)
        self.assertIn("_srfont_forget_node.bind(sr_node.get_instance_id())", localization)
        self.assertIn("Ozzd5ZL.erase(sr_id)", localization)
        self.assertIn("Ii8vLFF(sr_node, false)", localization)
        self.assertIn("hUxk0s_ is Control or hUxk0s_ is Window", localization)
        self.assertIn("var fZBXjsn = hUxk0s_", localization)
        self.assertIn("sr_node is Control or sr_node is Window", localization)
        self.assertIn("var sr_has_override : bool", localization)
        self.assertIn("var sr_base_size : int", localization)
        self.assertIn("_srfont_apply_added(sr_node)", localization)
        self.assertIn("or _srfont_path_for_mode(qn86QKV())", localization)
        self.assertIn("pixel.ttf", localization)
        self.assertIn("traditional.otf", localization)
        self.assertNotIn("_srfont_apply_direct_resources", localization)
        self.assertNotIn(".data =", localization)
        self.assertEqual(set(result), {LOCALIZATION_PATH, *DIRECT_FONT_SCRIPTS})
        self.assertIn("var test_font = Localization.srfont_for(load(", result[DIRECT_FONT_SCRIPTS[0]].decode())
        self.assertIn("var mLO6BLl : Font = Localization.srfont_for(load(", result["Scenes/UI/auto_potion_panel.gd"].decode())
