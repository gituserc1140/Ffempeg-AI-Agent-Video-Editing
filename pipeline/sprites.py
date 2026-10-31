"""12x12 pixel icons. 'a'/'A' = subject colour (main/dark); other letters are fixed colours."""

CHARS = {
    "w": 3, "g": 4, "d": 5, "o": 6, "O": 7, "c": 8, "C": 9, "n": 10,
    "r": 11, "y": 12, "p": 13, "u": 14, "N": 15, "k": 0, "b": 1,
}

ICONS = {
    "printer": [
        "gggggggggggg", "g..........g", "g....aa....g", "g....aa....g",
        "g....AA....g", "g.....A....g", "g..........g", "g..aaaaaa..g",
        "g..aaaaaa..g", "gggggggggggg", "dddddddddddd", "............",
    ],
    "spool": [
        "...aaaaaa...", "..aaaaaaaa..", ".aaaAAAAaaa.", "aaaAA..AAaaa",
        "aaAA....AAaa", "aaAA....AAaa", "aaAA....AAaa", "aaaAA..AAaaa",
        ".aaaAAAAaaa.", "..aaaaaaaa..", "...aaaaaa...", "............",
    ],
    "nozzle": [
        "..gggggggg..", "..gwwwwwwg..", "...gggggg...", "...gddddg...",
        "...gddddg...", "....gddg....", "....gaag....", ".....aa.....",
        ".....AA.....", ".....aa.....", "....a..a....", "............",
    ],
    "flame": [
        ".....r......", ".....rr.....", "....rrr.r...", "...rrrrrr...",
        "..rrrooorr..", "..rroooorr..", ".rrooyyoorr.", ".rrooyyoorr.",
        ".rrooyyyorr.", "..rooyyyor..", "..rrooooorr.", "...rrrrrr...",
    ],
    "snow": [
        ".....cc.....", "..c..cc..c..", "...c.cc.c...", "....cccc....",
        "cccccccccccc", "cccccccccccc", "....cccc....", "...c.cc.c...",
        "..c..cc..c..", ".....cc.....", "............", "............",
    ],
    "check": [
        "............", "..........nn", ".........nnn", "........nnn.",
        "nn.....nnn..", "nnn...nnn...", ".nnn.nnn....", "..nnnnn.....",
        "...nnn......", "....n.......", "............", "............",
    ],
    "cross": [
        "rr........rr", "rrr......rrr", ".rrr....rrr.", "..rrr..rrr..",
        "...rrrrrr...", "....rrrr....", "....rrrr....", "...rrrrrr...",
        "..rrr..rrr..", ".rrr....rrr.", "rrr......rrr", "rr........rr",
    ],
    "star": [
        ".....yy.....", ".....yy.....", "....yyyy....", "yyyyyyyyyyyy",
        ".yyyyyyyyyy.", "..yyyyyyyy..", "...yyyyyy...", "..yyyyyyyy..",
        "..yyy..yyy..", ".yy......yy.", ".y........y.", "............",
    ],
    "heart": [
        "............", ".rrr....rrr.", "rrrrr..rrrrr", "rrwrrrrrrrrr",
        "rrrrrrrrrrrr", "rrrrrrrrrrrr", ".rrrrrrrrrr.", "..rrrrrrrr..",
        "...rrrrrr...", "....rrrr....", ".....rr.....", "............",
    ],
    "bolt": [
        "......yyyy..", ".....yyyy...", "....yyyy....", "...yyyy.....",
        "..yyyyyyyy..", "....yyyyyy..", "......yyy...", ".....yyy....",
        "....yyy.....", "...yy.......", "..y.........", "............",
    ],
    "layers": [
        "............", "............", "..aaaaaaaa..", "..AAAAAAAA..",
        "..aaaaaaaa..", "..AAAAAAAA..", "..aaaaaaaa..", "..AAAAAAAA..",
        "..aaaaaaaa..", "..AAAAAAAA..", "............", "............",
    ],
    "strand": [
        "aaaa....aaaa", "aaaa....aaaa", "aaaawwwwaaaa", "aaaa....aaaa",
        "aaaawwwwaaaa", "aaaa....aaaa", "aaaa.ww.aaaa", "aaaa....aaaa",
        "aaaa....aaaa", "AAAA....AAAA", "............", "............",
    ],
    "warp": [
        "............", "............", "a..........a", "aa........aa",
        ".aa......aa.", "..aaaaaaaa..", "............", "gggggggggggg",
        "dddddddddddd", "............", "............", "............",
    ],
    "drop": [
        ".....aa.....", ".....aa.....", "....aaaa....", "....aaaa....",
        "...aaaaaa...", "..aaaaaaaa..", "..aawaaaaa..", "..aawaaaaa..",
        "..aaaaaaaa..", "...aaaaaa...", "....aaaa....", "............",
    ],
    "shield": [
        ".aaaaaaaaaa.", ".aAAAAAAAAa.", ".aAaaaaaaAa.", ".aAaaaaaaAa.",
        ".aAaaaaaaAa.", "..aAaaaaAa..", "..aAaaaaAa..", "...aAaaAa...",
        "....aAAa....", ".....aa.....", "............", "............",
    ],
    "gear": [
        ".....aa.....", ".a..aaaa..a.", ".aaaaaaaaaa.", "..aaa..aaa..",
        "..aa....aa..", "aaaa....aaaa", "aaaa....aaaa", "..aa....aa..",
        "..aaa..aaa..", ".aaaaaaaaaa.", ".a..aaaa..a.", ".....aa.....",
    ],
    "wave": [
        "............", "............", ".aa.....aa..", "aaaa...aaaa.",
        "a..aa.aa..aa", "....aaa.....", "............", "............",
        "............", "............", "............", "............",
    ],
    "hard": [
        "............", ".gggggggggg.", ".gwwwwwwwwg.", ".gwggggggwg.",
        ".gwgddddgwg.", ".gwgddddgwg.", ".gwggggggwg.", ".gwwwwwwwwg.",
        ".gggggggggg.", "............", "............", "............",
    ],
}

for _name, _rows in ICONS.items():
    assert len(_rows) == 12, _name
    assert all(len(r) == 12 for r in _rows), _name
