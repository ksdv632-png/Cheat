"""Episode 4 screenplay data («Считай заново»). Short format: ~62 s, hook in the first second.

Subtitle markup: a word prefixed with ^ is red, with ~ is yellow (put the marker BEFORE an opening «).
`text` is shown / aligned; `tts` goes to the voice model. `gap` = silence after, `pre` = silence before.
"""

SPEAKERS = {
    "narrator": {"voice": "y0RLnxlYEbYtNjhcMVmG"},   # Deniel
    "oldman":   {"voice": "0vJ96DzHePfGJitmI6UX"},   # Ivan Ivanovich
    "mom":      {"voice": "zjHs7kT0lVQxsrxfoUpu"},   # Renie
    "thing":    {"voice": "y0RLnxlYEbYtNjhcMVmG"},   # narrator's voice, processed
}

LINES = [
    dict(id="l00", spk="narrator", scene="hook", text="Нас было пятеро. Теперь — шестнадцать.",
         tts="[tense, quiet] Нас было пятеро. Теперь — шестнадцать.",
         chunks=["Нас было ~пятеро.", "Теперь — ^шестнадцать."], pre=0.2, gap=1.0),
    dict(id="l01", spk="narrator", scene="wall", text="Они вошли молча и встали у стены. Рядом с нами.",
         tts="[whispers] Они вошли молча и встали у стены. Рядом с нами.",
         chunks=["Они вошли ~молча", "и встали у стены.", "Рядом ^с нами."], pre=0.1, gap=0.8),
    dict(id="l02", spk="oldman", scene="oldman", text="Не смотри им в глаза. Смотри на тени.",
         tts="[urgent whisper] Не смотри им в глаза. Смотри на тени.",
         chunks=["«Не смотри им в ^глаза.", "Смотри на ~тени.»"], pre=0.1, gap=0.8),
    dict(id="l03", spk="narrator", scene="shadows", text="У людей есть тени. У них — нет.",
         tts="[quietly] У людей есть тени. У них — нет.",
         chunks=["У людей есть ~тени.", "У них — ^нет."], pre=0.1, gap=0.7),
    dict(id="l04", spk="narrator", scene="shadows", text="Я считал. Одна. Две. Три. Четыре. Пять.",
         tts="[slowly, counting under breath] Я считал. Одна. Две. Три. Четыре. Пять.",
         chunks=["Я считал.", "~Одна. ~Две. ~Три.", "~Четыре. ~Пять."], pre=0.1, gap=1.0),
    dict(id="l05", spk="narrator", scene="shadows", text="Пять теней. А нас — пятеро.",
         tts="[relieved, then unsure] Пять теней. А нас — пятеро.",
         chunks=["Пять теней.", "А нас — ~пятеро."], pre=0.1, gap=1.3),
    dict(id="l06", spk="mom", scene="mom", text="Димочка... а свою ты посчитал?",
         tts="[sweet, too calm] Димочка... а свою ты посчитал?",
         chunks=["^«Димочка…", "а ~свою ты ^посчитал?»"], pre=0.3, gap=1.2),
    dict(id="l07", spk="narrator", scene="feet", text="Я посмотрел под ноги.",
         tts="[quietly] Я посмотрел под ноги.",
         chunks=["Я посмотрел под ~ноги."], pre=0.1, gap=1.6),
    dict(id="l08", spk="narrator", scene="feet", text="Моей тени не было.",
         tts="[whispers, shocked] Моей тени не было.",
         chunks=["Моей ^тени", "не ^было."], pre=0.1, gap=1.8),
    dict(id="l09", spk="oldman", scene="oldman", text="Значит, ты уже не с нами.",
         tts="[heavy, slow] Значит, ты уже не с нами.",
         chunks=["«Значит, ты уже", "^не ^с ^нами.»"], pre=0.2, gap=0.9),
    dict(id="l10", spk="thing", scene="ear", text="Нет. Он — с нами.",
         tts="[low whisper] Нет. Он — с нами.",
         chunks=["«^Нет.", "Он — ^с ^нами.»"], pre=0.8, gap=1.0),
    dict(id="l11", spk="narrator", scene="turn", text="И все шестнадцать теней повернулись ко мне.",
         tts="[barely audible] И все шестнадцать теней повернулись ко мне.",
         chunks=["И все ~шестнадцать теней", "^повернулись ко мне."], pre=0.3, gap=2.0),
]

END_CARD = 3.6  # short end card
