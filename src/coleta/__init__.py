"""Scripts de coleta das bases de energia, frota e emissoes (rodada 13).

Cada script baixa o original para `dados/bruto/<fonte>/`, registra URL, data,
tamanho e SHA-256 no manifesto da fonte e, quando o original passa de 50 MB,
refaz o bruto reduzido em parquet (`dados/bruto/<fonte>/reduzido/`).
"""
