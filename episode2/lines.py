"""Episode 2 screenplay data.

Subtitle markup: a word prefixed with ^ is highlighted red, with ~ is highlighted yellow.
`chunks` splits a line into on-screen subtitle cards (each chunk = words shown together).
`gap` is silence (seconds) after the line, `pre` is silence before it.
"""

SPEAKERS = {
    # voice_id values are ElevenLabs premade voices (multilingual); see tts.py for settings
    "narrator": {"voice": "JBFqnCBsd6RMkjVDRZzb"},   # George — low, worn storyteller
    "oldman":   {"voice": "pqHfZKP75CvOlQylNhV4"},   # Bill — old, dry
    "victor":   {"voice": "N2lVS1w4EtoT3dr4eOWO"},   # Callum — tense, raspy
    "mom":      {"voice": "EXAVITQu4vr4xnSDxMaL"},   # Sarah — soft female
    "thing":    {"voice": "JBFqnCBsd6RMkjVDRZzb"},   # the narrator's own voice, processed (it learns voices)
}

LINES = [
    # id, speaker, scene, text (spoken), chunks (subtitle cards), pre, gap
    dict(id="l00", spk="thing", scene="cold", text="Не оборачивайся.",
         chunks=["«Не ^оборачивайся.»"], pre=1.6, gap=0.5),
    dict(id="l01", spk="narrator", scene="back", text="Я не обернулся.",
         chunks=["Я ~не ^обернулся."], pre=2.6, gap=0.7),
    dict(id="l02", spk="narrator", scene="back", text="За спиной кто-то дышал. Медленно. Будто учился.",
         chunks=["За спиной кто-то ^дышал.", "Медленно.", "Будто ^учился."], pre=0.0, gap=0.9),
    dict(id="l03", spk="narrator", scene="wall_line", text="Я сказал: «Все — к стене. Спиной к стене».",
         chunks=["Я сказал:", "«Все — к ~стене.", "Спиной к ~стене».", ], pre=0.2, gap=0.5),
    dict(id="l04", spk="narrator", scene="count", text="Шесть человек. Семь теней.",
         chunks=["~Шесть человек.", "^Семь теней."], pre=0.3, gap=1.2),
    dict(id="l05", spk="oldman", scene="oldman", text="Поднимите правую руку. Все.",
         chunks=["«Поднимите ~правую руку.", "^Все.»"], pre=0.2, gap=0.6),
    dict(id="l06", spk="narrator", scene="hands", text="Семь рук поднялись одновременно. Почти.",
         chunks=["Семь рук поднялись одновременно.", "^Почти."], pre=0.4, gap=0.4),
    dict(id="l07", spk="narrator", scene="hands_late", text="Одна тень опоздала. На полсекунды.",
         chunks=["Одна тень ^опоздала.", "На ^полсекунды."], pre=0.2, gap=0.6),
    dict(id="l08", spk="narrator", scene="victor_reveal", text="Она стояла за Виктором.",
         chunks=["Она стояла за ~Виктором."], pre=0.1, gap=0.5),
    dict(id="l09", spk="narrator", scene="eyes", text="Страх быстро находит виноватого.",
         chunks=["Страх быстро находит", "^виноватого."], pre=0.2, gap=0.3),
    dict(id="l10", spk="victor", scene="victor_face", text="Это не я! Я никого не впускал!",
         chunks=["«Это ^не ^я!", "Я никого не ^впускал!»"], pre=0.1, gap=0.5),
    dict(id="l11", spk="narrator", scene="step", text="Он сделал шаг от стены. А его тень — осталась.",
         chunks=["Он сделал шаг от стены.", "А его тень —", "^осталась."], pre=0.2, gap=1.0),
    dict(id="l12", spk="narrator", scene="flicker", text="Фонарь мигнул.",
         chunks=["Фонарь ^мигнул."], pre=0.1, gap=2.0),
    dict(id="l13", spk="narrator", scene="five", text="Нас стало пятеро. Теней — всё ещё семь.",
         chunks=["Нас стало ~пятеро.", "Теней — всё ещё ^семь."], pre=0.3, gap=1.0),
    dict(id="l14", spk="narrator", scene="knock", text="А потом в дверь постучали. Снаружи.",
         chunks=["А потом в дверь ^постучали.", "^Снаружи."], pre=0.2, gap=0.7),
    dict(id="l15", spk="victor", scene="door_voice", text="Откройте... это я. Тут холодно.",
         chunks=["«Откройте…", "это ~я.", "Тут ^холодно.»"], pre=0.3, gap=0.9),
    dict(id="l16", spk="oldman", scene="oldman_door", text="Не открывай. Так оно вошло в первый раз.",
         chunks=["«Не ^открывай.", "Так оно ^вошло", "в первый раз.»"], pre=0.2, gap=1.0),
    dict(id="l17", spk="narrator", scene="flashback", text="И тут я вспомнил. У люка я слышал маму. Она звала меня по имени.",
         chunks=["И тут я ~вспомнил.", "У люка я слышал ~маму.", "Она звала меня", "по ^имени."], pre=0.2, gap=0.3),
    dict(id="l18", spk="mom", scene="flashback_mom", text="Дима...",
         chunks=["«Дима…»"], pre=0.3, gap=0.8),
    dict(id="l19", spk="narrator", scene="turn", text="И я обернулся.",
         chunks=["И я ^обернулся."], pre=0.2, gap=1.6),
    dict(id="l20", spk="thing", scene="ear", text="Вот видишь. Ты уже оборачивался.",
         chunks=["«Вот видишь.", "Ты ^уже ^оборачивался.»"], pre=0.8, gap=1.0),
    dict(id="l21", spk="mom", scene="door_mom", text="Димочка... открой. Это мама.",
         chunks=["«Димочка…", "^открой.", "Это ~мама.»"], pre=2.6, gap=1.6),
]

END_CARD = 4.2  # seconds of end card after last line
