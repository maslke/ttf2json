from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import warnings
import json
import argparse

from util import commands_to_svg, extra_settings


class TTF2JSON:
    def __init__(self, ttf_path: str):
        self.ttf_path = ttf_path
        self.loaded = False

    def _load_ttf(self):
        try:
            self.ttf = TTFont(self.ttf_path)
        except IOError as e:
            print(f"font file can not be read: {self.ttf_path} - {e}")
            raise e
        self.loaded = True

    def convert2json(self, words: str = None):
        if not self.loaded:
            self._load_ttf()
        ttf = self.ttf
        words_dict = dict(zip(words, [1] * len(words)))
        cmap = ttf.getBestCmap()
        mapper = {
            ord(word): cmap[ord(word)]
            for word in words_dict
            if ord(word) in cmap
        }
        return self._convert(mapper)

    def dump2json(self):
        if not self.loaded:
            self._load_ttf()
        ttf = self.ttf
        cmap = ttf.getBestCmap()
        return self._convert(cmap)

    def _convert(self, mapper):
        ttf = self.ttf
        head_table = ttf.get("head")
        glyf_table = ttf.get("glyf")
        units_per_em = head_table.unitsPerEm
        hmtx_table = ttf.get("hmtx")
        scale = (1000 * 100) / (units_per_em * 72)
        cmap = ttf.getBestCmap()
        glyfs = {}
        for c in mapper:
            g = glyf_table[mapper[c]]
            if g.numberOfContours > 0:
                spen = SVGPathPen(glyf_table)
                g.draw(spen, glyf_table)
                commands = spen._commands
                obj = {
                    "o": commands_to_svg(commands, scale),
                    "x_min": round(g.xMin * scale),
                    "x_max": round(g.xMax * scale),
                    "ha": round(hmtx_table[cmap[c]][0] * scale),
                }
                glyfs[chr(c)] = obj
        extra = extra_settings(ttf)
        settings = {
            "glyphs": glyfs,
        }
        settings.update(extra)
        return settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--font_file", type=str, required=True, help="input font file"
    )
    parser.add_argument(
        "--json_file", type=str, required=True, help="output json file"
    )
    parser.add_argument(
        "--words", type=str, required=False, help="provide words you need"
    )
    parser.add_argument(
        "--words_from_file",
        type=str,
        required=False,
        help="provides words you need from a file",
    )
    args = parser.parse_args()
    font_file = args.font_file
    json_file = args.json_file
    words = args.words
    from_file = args.words_from_file

    if words is not None and from_file is not None:
        warnings.warn(
            "both words and from_file is not empty, prefer words and ignores from_file"
        )

    if from_file is not None:
        try:
            with open(from_file, "r") as ffile:
                try:
                    words = ffile.read()
                except IOError:
                    warnings.warn(
                        "can not read the open file:{},the file will be ignored".format(
                            from_file
                        )
                    )
        except (FileNotFoundError, PermissionError):
            warnings.warn(
                "can not open the from file:{},the file will be ignored".format(
                    from_file
                )
            )

    ttf2json = TTF2JSON(font_file)
    settings = ttf2json.convert2json(words)
    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False)
    except PermissionError:
        warnings.warn("can not write to the json file:{}".format(json_file))
    print("finished, the output json file is :{}".format(json_file))


if __name__ == "__main__":
    main()
