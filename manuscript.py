"""Escape all external text before rendering manuscript layouts."""

from html import escape


def comparison_table(pairs, past_year, later_year):
    past_label = f"{past_year}年の出来事"
    later_label = f"60年後・{later_year}年の出来事"
    rows = []
    for pair in pairs:
        themes = ''.join(f'<span class="theme-label">{escape(theme)}</span>' for theme in pair['themes'])
        words = '・'.join(pair['words']) or '同じ分類の異なる語'
        rows.append(
            f'<tr><td data-label="{past_label}">{escape(pair["past"])}</td>'
            f'<td data-label="{later_label}">{escape(pair["later"])}</td>'
            f'<td data-label="共通テーマ">{themes}'
            f'<span class="shared-words">共通する語：{escape(words)}</span></td></tr>'
        )
    return (
        f'<table class="chronicle-table" aria-label="{past_year}年と{later_year}年の出来事の比較">'
        f'<thead><tr><th scope="col">{past_label}</th><th scope="col">{later_label}</th>'
        '<th scope="col">共通テーマ</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
    )


def prediction_card(prediction):
    evidence = ''.join(f'<li>{escape(event)}</li>' for event in prediction['evidence'])
    return (
        '<article class="forecast-sheet">'
        f'<h3>{escape(prediction["theme"])}</h3>'
        f'<p class="prediction">{escape(prediction["prediction"])}</p>'
        '<details><summary>過去の手掛かりと理由を読む</summary>'
        f'<p>{escape(prediction["reason"])}</p><ul>{evidence}</ul></details></article>'
    )
