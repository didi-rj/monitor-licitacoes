from flask import Flask, render_template_string, request
import sqlite3

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Monitor de Licitações</title>
    <style>
        body { font-family: Arial; margin: 40px; background-color: #f4f6f9; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; background: white; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #2c3e50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        a { color: #2980b9; text-decoration: none; }
        .search-box { margin-bottom: 20px; }
        input[type=text] { padding: 8px; width: 300px; }
        input[type=submit] { padding: 8px 12px; background: #2c3e50; color: white; border: none; cursor: pointer; }
        input[type=submit]:hover { background: #1a242f; }
        .contador { margin-bottom: 15px; font-weight: bold; }
    </style>
</head>
<body>

<h1>📡 Monitor de Licitações - Topografia</h1>

<div class="search-box">
    <form method="get">
        <input type="text" name="q" placeholder="Buscar no objeto..." value="{{ query }}">
        <input type="submit" value="Pesquisar">
    </form>
</div>

<div class="contador">
    Total de registros encontrados: {{ total }}
</div>

<table>
<tr>
    <th>Órgão</th>
    <th>Data</th>
    <th>Objeto</th>
    <th>Link</th>
</tr>

{% for row in rows %}
<tr>
    <td>{{ row[1] }}</td>
    <td>{{ row[3] }}</td>
    <td>{{ row[2] }}</td>
    <td><a href="{{ row[4] }}" target="_blank">Abrir</a></td>
</tr>
{% endfor %}

</table>

</body>
</html>
"""

@app.route("/")
def index():
    query = request.args.get("q", "").lower()

    conn = sqlite3.connect("banco.db")
    c = conn.cursor()

    if query:
        c.execute("SELECT * FROM licitacoes WHERE lower(objeto) LIKE ? ORDER BY data DESC", ('%' + query + '%',))
    else:
        c.execute("SELECT * FROM licitacoes ORDER BY data DESC")

    rows = c.fetchall()
    conn.close()

    return render_template_string(TEMPLATE, rows=rows, total=len(rows), query=query)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)