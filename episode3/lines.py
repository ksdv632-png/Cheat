"""Episode 3 screenplay data («Мама за дверью»).

Subtitle markup: a word prefixed with ^ is highlighted red, with ~ is highlighted yellow.
`text` is what is shown / aligned; `tts` is what is sent to the voice model (may contain audio tags).
`chunks` splits a line into on-screen subtitle cards. `gap` = silence after, `pre` = silence before.
"""

SPEAKERS = {
    "narrator": {"voice": "y0RLnxlYEbYtNjhcMVmG"},   # Deniel — warm deep calm Russian male
    "oldman":   {"voice": "0vJ96DzHePfGJitmI6UX"},   # Ivan Ivanovich — old low bass
    "mom":      {"voice": "zjHs7kT0lVQxsrxfoUpu"},   # Renie — soft female
    "thing":    {"voice": "y0RLnxlYEbYtNjhcMVmG"},   # the narrator's own voice, processed
}

LINES = [
    dict(id="l00", spk="mom", scene="door_cold", text="Димочка... открой. Мне очень холодно.",
         tts="[softly] Димочка... открой. Мне очень холодно.",
         chunks=["«Димочка…", "^открой.", "Мне очень ~холодно.»"], pre=1.4, gap=0.6),
    dict(id="l01", spk="narrator", scene="door_walk", text="Я узнал этот голос. Я узнал бы его из тысячи.",
         tts="[quietly] Я узнал этот голос. Я узнал бы его из тысячи.",
         chunks=["Я узнал этот ~голос.", "Я узнал бы его", "из ^тысячи."], pre=3.2, gap=0.5),
    dict(id="l02", spk="narrator", scene="door_walk", text="Ноги сами понесли меня к двери.",
         tts="Ноги сами понесли меня к двери.",
         chunks=["Ноги сами понесли меня", "к ^двери."], pre=0.1, gap=0.5),
    dict(id="l03", spk="oldman", scene="oldman", text="Стой! Оно не знает людей. Оно знает только голоса.",
         tts="[urgent whisper] Стой! Оно не знает людей. Оно знает только голоса.",
         chunks=["^«Стой!", "Оно не знает ~людей.", "Оно знает только ^голоса.»"], pre=0.2, gap=0.5),
    dict(id="l04", spk="oldman", scene="oldman", text="Задай вопрос. Такой, на который ответит только она.",
         tts="[whispers] Задай вопрос. Такой, на который ответит только она.",
         chunks=["«Задай ~вопрос.", "Такой, на который", "ответит только ^она.»"], pre=0.2, gap=0.6),
    dict(id="l05", spk="narrator", scene="door_hand", text="Я приложил ладонь к металлу. Лёд.",
         tts="[quietly] Я приложил ладонь к металлу. Лёд.",
         chunks=["Я приложил ладонь к ~металлу.", "^Лёд."], pre=0.2, gap=0.5),
    dict(id="l06", spk="narrator", scene="door_hand", text="Мама... что ты пела мне, когда я не мог уснуть?",
         tts="[hesitant, trembling] Мама... что ты пела мне, когда я не мог уснуть?",
         chunks=["«Мама…", "что ты ~пела мне,", "когда я не мог ^уснуть?»"], pre=0.1, gap=0.9),
    dict(id="l07", spk="mom", scene="lullaby", text="Спи, мой мальчик... Спи, мой Димочка...",
         tts="[singing softly, tender] Спи, мой мальчик... Спи, мой Димочка...",
         chunks=["«Спи, мой ~мальчик…", "Спи, мой ^Димочка…»"], pre=0.5, gap=0.9),
    dict(id="l08", spk="narrator", scene="dima_face", text="Те же слова. Тот же вздох на второй строчке.",
         tts="[breathless] Те же слова. Тот же вздох на второй строчке.",
         chunks=["Те же ~слова.", "Тот же ^вздох", "на второй строчке."], pre=0.3, gap=0.4),
    dict(id="l09", spk="narrator", scene="door_reach", text="Я уже тянул руку к колесу.",
         tts="Я уже тянул руку к колесу.",
         chunks=["Я уже тянул руку", "к ^колесу."], pre=0.2, gap=0.4),
    dict(id="l10", spk="oldman", scene="oldman", text="Ещё один. Последний.",
         tts="[whispers, tense] Ещё один. Последний.",
         chunks=["«Ещё ~один.", "^Последний.»"], pre=0.2, gap=0.6),
    dict(id="l11", spk="narrator", scene="door_hand", text="Мама... что ты сказала мне в тот день, когда я уходил?",
         tts="[voice cracking] Мама... что ты сказала мне в тот день, когда я уходил?",
         chunks=["«Мама…", "что ты ~сказала мне", "в тот день, когда я ^уходил?»"], pre=0.2, gap=0.8),
    dict(id="l12", spk="narrator", scene="silence", text="За дверью стало тихо. Слишком тихо.",
         tts="[whispers] За дверью стало тихо. Слишком тихо.",
         chunks=["За дверью стало ~тихо.", "Слишком ^тихо."], pre=0.2, gap=1.2),
    dict(id="l13", spk="mom", scene="silence", text="Я сказала...",
         tts="[slowly, uncertain] Я сказала...",
         chunks=["«Я ~сказала…»"], pre=0.2, gap=0.7),
    dict(id="l14", spk="thing", scene="behind", text="Не уходи.",
         tts="[whispers] Не уходи.",
         chunks=["«Не ^уходи.»"], pre=0.5, gap=1.0),
    dict(id="l15", spk="narrator", scene="behind", text="Ответ был верный. Но шепнули его не за дверью. А у меня за плечом. Моим голосом.",
         tts="[shaken] Ответ был верный. Но шепнули его не за дверью. А у меня за плечом. Моим голосом.",
         chunks=["Ответ был ~верный.", "Но шепнули его не за дверью.", "А у меня за ^плечом.", "Моим ^голосом."], pre=0.4, gap=0.8),
    dict(id="l16", spk="narrator", scene="dima_face", text="Оно не угадывало. Оно доставало ответы прямо из моей головы.",
         tts="[quietly, horrified] Оно не угадывало. Оно доставало ответы прямо из моей головы.",
         chunks=["Оно не ~угадывало.", "Оно доставало ответы", "прямо из моей ^головы."], pre=0.2, gap=0.6),
    dict(id="l17", spk="oldman", scene="oldman", text="Значит, оно было внутри с самого начала.",
         tts="[heavy whisper] Значит, оно было внутри с самого начала.",
         chunks=["«Значит, оно было ^внутри", "с самого ~начала.»"], pre=0.2, gap=0.7),
    dict(id="l18", spk="narrator", scene="wheel", text="Я хотел спросить: кого? Но колесо на двери дрогнуло.",
         tts="[quietly] Я хотел спросить: кого? Но колесо на двери дрогнуло.",
         chunks=["Я хотел спросить: ~кого?", "Но ^колесо на двери", "^дрогнуло."], pre=0.2, gap=0.5),
    dict(id="l19", spk="narrator", scene="wheel", text="Повернулось. Само. Изнутри.",
         tts="[whispers] Повернулось. Само. Изнутри.",
         chunks=["Повернулось.", "~Само.", "^Изнутри."], pre=0.2, gap=1.0),
    dict(id="l20", spk="narrator", scene="open", text="Дверь открылась.",
         tts="[barely audible] Дверь открылась.",
         chunks=["Дверь ^открылась."], pre=0.2, gap=1.1),
    dict(id="l21", spk="mom", scene="open", text="Спасибо, Дима. Теперь можно.",
         tts="[sweet, unnaturally calm] Спасибо, Дима. Теперь можно.",
         chunks=["~«Спасибо, Дима.", "Теперь ^можно.»"], pre=0.3, gap=1.2),
    dict(id="l22", spk="thing", scene="open", text="Считай заново.",
         tts="[low whisper] Считай заново.",
         chunks=["^«Считай заново.»"], pre=0.2, gap=1.4),
]

END_CARD = 4.4  # seconds of end card after last line
