SAMPLES={
 'hu':('Hungarian','Árvíztűrő tükörfúrógép. Őő Űű: hosszú ősz, gyönyörű idő.'),
 'cy':('Welsh','Dŵr, tŷ, ŵyn a gŵyl. Ŵŵ Ŷŷ Ẁẁ Ẃẃ Ẅẅ Ỳỳ.'),
 'lb':('Luxembourgish','Moien! Lëtzebuergesch: Äppel, schéin Zäit a grousse Spaass.'),
 'gsw':('Alsatian','Elsässisch: Äpfel, Bààrg, güet, d’Strooss un s’Hüs.'),
 'vi':('Vietnamese','Tiếng Việt: Nguyễn, Trường, tiếng nói; Ắ ằ ễ ộ ớ ự ỹ.'),
 'tok':('Toki Pona','jan ale li ken kama sona. mi toki pona lon tenpo suno ni.'),
 'el':('Greek','Ελληνικά: Καλημέρα κόσμε. ΆΈΉΊΌΎΏ ΐ ΰ ς.'),
 'ru':('Cyrillic','Съешь ещё этих мягких французских булок. Ёё Йй Її Єє Ґґ.'),
 'ja':('Japanese','丸みのある文字で、長い文章を読みやすく。東京と京都、ひらがな・カタカナ。がぎぐげご パピプペポ。※ ★ ♪ Å。'),
}
ALPHABETS={
 'hu':'aábcdeéfghiíjklmnoóöőpqrstuúüűvwxyz',
 'cy':'abcdefghijklmnopqrstuvwxyzâêîôûŵŷáéíóúẃýàèìòùẁỳäëïöüẅÿ',
 'lb':'abcdefghijklmnopqrstuvwxyzäëé',
 'gsw':'abcdefghijklmnopqrstuvwxyzàâäéèêëìîïòôöùûü',
 'vi':'aăâbcdđeêghiklmnoôơpqrstuưvxyàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ',
 'tok':'aeijklmnopstuw',
 'el':'αβγδεζηθικλμνξοπρσςτυφχψωάέήίόύώϊϋΐΰ',
 'ru':'абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїєґђјљњћџ',
 'ja':'あいうえおかきくけこがぎぐげごぱぴぷぺぽアイウエオカキクケコガギグゲゴパピプペポ丸文字日本語東京京都漢字',
}
MARK_SAMPLES=['x\u0302\u0301','q\u0308','a\u030b','o\u031b\u0301','u\u031b\u0323','α\u0308','и\u0306','か\u3099','ハ\u309a']
CODE='''def hello(name: str) -> str:
    # 日本語コメントと Nguyễn / dŵr / őr
    items = {"O0": 10, "Il1": 0x0F}
    if name != "":
        return f"Hello, {name}!"  # [] {} ()
    return "こんにちは、世界。"
'''
