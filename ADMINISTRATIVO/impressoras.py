import io
import os
import re
import sqlite3
from datetime import datetime

from flask import Blueprint, Flask, jsonify, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "impressoras.db")

_LOCAIS_1_ANDAR = {
    "TRIAGEM",
    "CONSULTÓRIO 1",
    "CONSULTÓRIO 2",
    "CONSULTÓRIO 3",
    "CONSULTÓRIO 4",
    "CONSULTÓRIO 5",
    "RECEPÇÃO",
    "PRÉ-RECEPÇÃO",
    "PAINEL RECEPÇÃO",
    "PAINEL SUB-ESPERA",
    "FARMÁCIA",
    "COLETA",
    "OBSERVAÇÃO",
    "ASSISTÊNCIA FARMACÊUTICA",
    "MULTIUSO",
    "VACINA",
    "ZOONOSES",
}

_LOCAIS_2_ANDAR = {
    "ODONTOLOGIA",
    "CONSULTÓRIO 6",
    "CONSULTÓRIO 7",
    "CONSULTÓRIO 8",
    "CONSULTÓRIO 9",
    "CONSULTÓRIO 10",
    "CONSULTÓRIO 11",
    "CONSULTÓRIO 12",
    "CONSULTÓRIO 13",
    "CONSULTÓRIO 14",
    "CONSULTÓRIO 15",
    "CONSULTÓRIO 16",
    "CONSULTÓRIO 17",
    "GERÊNCIA",
    "ADMINISTRATIVO",
    "SALA DOS AGENTES",
    "NOTEBOOK",
    "COPA",
}

_DADOS = []


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _normalizar_ip(valor):
    texto = str(valor or "").strip().upper()
    if not texto:
        return ""
    if "CABO" in texto:
        return "A CABO"
    return texto


def _normalizar_serie(valor):
    return str(valor or "").strip().upper()


def _normalizar_modelo(valor):
    return str(valor or "").strip().upper()


def _chave_ordenacao(item):
    andar = str(item.get("andar") or "zzz").lower()
    local = str(item.get("local") or "").lower()
    partes_local = [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", local)]
    return (int(bool(item.get("trocado"))), andar, partes_local, item.get("id", 0))


def init_db():
    with _conn() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS impressoras_itens (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                andar            TEXT NOT NULL DEFAULT '',
                local            TEXT NOT NULL,
                modelo           TEXT NOT NULL DEFAULT '',
                ip               TEXT NOT NULL DEFAULT '',
                serie            TEXT NOT NULL DEFAULT '',
                trocado          INTEGER NOT NULL DEFAULT 0,
                novo_modelo      TEXT NOT NULL DEFAULT '',
                novo_ip          TEXT NOT NULL DEFAULT '',
                nova_serie       TEXT NOT NULL DEFAULT '',
                obs              TEXT NOT NULL DEFAULT '',
                trocado_em       TEXT NOT NULL DEFAULT ''
            )"""
        )

        colunas_existentes = {
            row["name"] for row in con.execute("PRAGMA table_info(impressoras_itens)").fetchall()
        }
        novas_colunas = {
            "andar": "TEXT NOT NULL DEFAULT ''",
            "modelo": "TEXT NOT NULL DEFAULT ''",
            "ip": "TEXT NOT NULL DEFAULT ''",
            "serie": "TEXT NOT NULL DEFAULT ''",
            "trocado": "INTEGER NOT NULL DEFAULT 0",
            "novo_modelo": "TEXT NOT NULL DEFAULT ''",
            "novo_ip": "TEXT NOT NULL DEFAULT ''",
            "nova_serie": "TEXT NOT NULL DEFAULT ''",
            "obs": "TEXT NOT NULL DEFAULT ''",
            "trocado_em": "TEXT NOT NULL DEFAULT ''",
        }
        for col, tipo in novas_colunas.items():
            if col not in colunas_existentes:
                con.execute(f"ALTER TABLE impressoras_itens ADD COLUMN {col} {tipo}")

        con.execute("UPDATE impressoras_itens SET andar = '2º Andar' WHERE UPPER(TRIM(local)) = 'COPA'")

        sem_andar = con.execute(
            "SELECT id, local FROM impressoras_itens WHERE TRIM(andar) = ''"
        ).fetchall()
        for r in sem_andar:
            loc = str(r["local"] or "").strip().upper()
            if loc in _LOCAIS_1_ANDAR:
                con.execute("UPDATE impressoras_itens SET andar = '1º Andar' WHERE id = ?", (r["id"],))
            elif loc in _LOCAIS_2_ANDAR:
                con.execute("UPDATE impressoras_itens SET andar = '2º Andar' WHERE id = ?", (r["id"],))

        vazio = con.execute("SELECT COUNT(*) FROM impressoras_itens").fetchone()[0] == 0
        if vazio and _DADOS:
            con.executemany(
                """INSERT INTO impressoras_itens (andar, local, modelo, ip, serie)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (andar, local, _normalizar_modelo(modelo), _normalizar_ip(ip), _normalizar_serie(serie))
                    for (andar, local, modelo, ip, serie) in _DADOS
                ],
            )


def _item_para_dict(row):
    item = dict(row)
    item["andar"] = item.get("andar", "")
    item["modelo"] = item.get("modelo", "")
    item["ip"] = item.get("ip", "")
    item["serie"] = item.get("serie", "")
    item["trocado"] = bool(item.get("trocado", 0))
    item["novo_modelo"] = item.get("novo_modelo", "")
    item["novo_ip"] = item.get("novo_ip", "")
    item["nova_serie"] = item.get("nova_serie", "")
    item["obs"] = item.get("obs", "")
    item["trocado_em"] = item.get("trocado_em", "")
    return item


def listar_impressoras():
    with _conn() as con:
        rows = con.execute("SELECT * FROM impressoras_itens").fetchall()
    itens = [_item_para_dict(r) for r in rows]
    itens.sort(key=_chave_ordenacao)
    return itens


def _erro(msg, status=400):
    resp = jsonify({"erro": msg})
    resp.status_code = status
    return resp


def _texto(dados, campo):
    return str(dados.get(campo) or "").strip()


# ---------------------------------------------------------------------------
# ROTAS
# ---------------------------------------------------------------------------
impressoras_bp = Blueprint("impressoras", __name__)


@impressoras_bp.route("/impressoras.html")
@impressoras_bp.route("/impressoras")
def pagina_impressoras():
    return render_template("impressoras.html")


@impressoras_bp.route("/api/impressoras")
def api_listar():
    return jsonify(listar_impressoras())


@impressoras_bp.route("/api/impressoras", methods=["POST"])
def api_adicionar():
    d = request.get_json(silent=True) or {}
    andar = _texto(d, "andar")
    local = _texto(d, "local").upper()
    modelo = _normalizar_modelo(d.get("modelo"))
    ip = _normalizar_ip(d.get("ip"))
    serie = _normalizar_serie(d.get("serie"))

    if not andar:
        return _erro("Informe o andar da impressora.")
    if not local:
        return _erro("Informe o local da impressora.")
    if not modelo:
        return _erro("Informe o modelo da impressora.")

    with _conn() as con:
        cur = con.execute(
            """INSERT INTO impressoras_itens (andar, local, modelo, ip, serie)
               VALUES (?, ?, ?, ?, ?)""",
            (andar, local, modelo, ip, serie),
        )
        row = con.execute("SELECT * FROM impressoras_itens WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(_item_para_dict(row)), 201


@impressoras_bp.route("/api/impressoras/<int:item_id>", methods=["PUT"])
def api_editar(item_id):
    d = request.get_json(silent=True) or {}
    andar = _texto(d, "andar")
    local = _texto(d, "local").upper()
    modelo = _normalizar_modelo(d.get("modelo"))
    ip = _normalizar_ip(d.get("ip"))
    serie = _normalizar_serie(d.get("serie"))

    if not andar:
        return _erro("Informe o andar da impressora.")
    if not local:
        return _erro("Informe o local da impressora.")
    if not modelo:
        return _erro("Informe o modelo da impressora.")

    trocado = bool(d.get("trocado"))
    novo_modelo = _normalizar_modelo(d.get("novo_modelo")) if trocado else ""
    novo_ip = _normalizar_ip(d.get("novo_ip")) if trocado else ""
    nova_serie = _normalizar_serie(d.get("nova_serie")) if trocado else ""
    obs = _texto(d, "obs") if trocado else ""
    trocado_em = datetime.now().strftime("%d/%m/%Y %H:%M") if trocado else ""

    if trocado:
        if not novo_modelo:
            return _erro("Informe o modelo da nova impressora.")
        if not nova_serie and not novo_ip:
            return _erro("Informe o número de série ou o IP da nova impressora.")

    novo_criado = None

    with _conn() as con:
        atual = con.execute(
            "SELECT * FROM impressoras_itens WHERE id = ?", (item_id,)
        ).fetchone()
        if atual is None:
            return _erro("Impressora não encontrada.", 404)

        ja_estava_trocado = bool(atual["trocado"])
        if trocado and ja_estava_trocado:
            trocado_em = atual["trocado_em"]

        con.execute(
            """UPDATE impressoras_itens
               SET andar = ?, local = ?, modelo = ?, ip = ?, serie = ?,
                   trocado = ?, novo_modelo = ?, novo_ip = ?, nova_serie = ?, obs = ?, trocado_em = ?
               WHERE id = ?""",
            (andar, local, modelo, ip, serie, int(trocado), novo_modelo, novo_ip, nova_serie, obs, trocado_em, item_id),
        )

        if trocado and (nova_serie or novo_ip):
            existe_novo = con.execute(
                """SELECT 1 FROM impressoras_itens
                   WHERE andar = ? AND local = ? AND modelo = ? AND serie = ? AND trocado = 0""",
                (andar, local, novo_modelo, nova_serie),
            ).fetchone()
            if not existe_novo:
                cur_novo = con.execute(
                    """INSERT INTO impressoras_itens (andar, local, modelo, ip, serie)
                       VALUES (?, ?, ?, ?, ?)""",
                    (andar, local, novo_modelo, novo_ip, nova_serie),
                )
                row_novo = con.execute(
                    "SELECT * FROM impressoras_itens WHERE id = ?", (cur_novo.lastrowid,)
                ).fetchone()
                novo_criado = _item_para_dict(row_novo)

        row = con.execute("SELECT * FROM impressoras_itens WHERE id = ?", (item_id,)).fetchone()

    return jsonify({"item": _item_para_dict(row), "novo_item": novo_criado})


@impressoras_bp.route("/api/impressoras/<int:item_id>", methods=["DELETE"])
def api_excluir(item_id):
    with _conn() as con:
        cur = con.execute("DELETE FROM impressoras_itens WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            return _erro("Impressora não encontrada.", 404)
    return jsonify({"ok": True})


@impressoras_bp.route("/api/impressoras/pdf", methods=["POST"])
def api_gerar_pdf():
    try:
        d = request.get_json(silent=True) or {}
        itens = d.get("itens")
        if itens is None:
            itens = listar_impressoras()

        filtro_desc = _texto(d, "filtro") or "Todos os registros"
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title="Relatório de Impressoras - CS Itamarati",
        )

        estilos = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle(
            "TituloCSI",
            parent=estilos["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=colors.HexColor("#0f3d47"),
            spaceAfter=2,
        )
        estilo_sub = ParagraphStyle(
            "SubCSI",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=colors.HexColor("#444444"),
            spaceAfter=8,
        )
        estilo_celula = ParagraphStyle(
            "CelulaCSI",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1a1a1a"),
        )
        estilo_celula_bold = ParagraphStyle(
            "CelulaBoldCSI",
            parent=estilo_celula,
            fontName="Helvetica-Bold",
        )

        elementos = [
            Paragraph("Centro de Saúde Itamarati — Inventário de Impressoras", estilo_titulo),
            Paragraph(
                f"Emitido em {agora} &nbsp;|&nbsp; Filtro: <b>{filtro_desc}</b> &nbsp;|&nbsp; Total listado: <b>{len(itens)}</b>",
                estilo_sub,
            ),
        ]

        ativos = [i for i in itens if not i.get("trocado")]
        qtd_xm3350 = sum(1 for i in ativos if "xm 3350" in str(i.get("modelo", "")).lower() or "xm3350" in str(i.get("modelo", "")).lower())
        qtd_ms521 = sum(1 for i in ativos if "ms 521" in str(i.get("modelo", "")).lower() or "ms521" in str(i.get("modelo", "")).lower())
        qtd_ms531 = sum(1 for i in ativos if "ms 531" in str(i.get("modelo", "")).lower() or "ms531" in str(i.get("modelo", "")).lower())

        tabela_resumo = Table(
            [
                ["CS ITAMARATI — Resumo das impressoras em uso listadas", "", "", ""],
                [
                    f"XM 3350: {qtd_xm3350}",
                    f"MS 521: {qtd_ms521}",
                    f"MS 531: {qtd_ms531}",
                    f"Total em uso: {len(ativos)}",
                ],
            ],
            colWidths=[67 * mm, 67 * mm, 67 * mm, 68 * mm],
        )
        tabela_resumo.setStyle(
            TableStyle([
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f4c5c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eef5f7")),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 9),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#102a30")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b7ccd1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elementos.append(tabela_resumo)
        elementos.append(Spacer(1, 6 * mm))

        linhas = [["Andar", "Local", "Modelo", "IP", "Número de Série", "Situação"]]
        for item in itens:
            situacao = "Trocado" if item.get("trocado") else "Em uso"
            linhas.append([
                Paragraph(str(item.get("andar") or "—"), estilo_celula),
                Paragraph(str(item.get("local") or "—"), estilo_celula_bold),
                Paragraph(str(item.get("modelo") or "—"), estilo_celula),
                Paragraph(str(item.get("ip") or "—"), estilo_celula),
                Paragraph(str(item.get("serie") or "—"), estilo_celula),
                Paragraph(situacao, estilo_celula_bold if item.get("trocado") else estilo_celula),
            ])

        tabela = Table(
            linhas,
            colWidths=[28 * mm, 66 * mm, 38 * mm, 46 * mm, 56 * mm, 35 * mm],
            repeatRows=1,
        )
        estilo_tabela = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f4c5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9.5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5d8")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]

        for idx, item in enumerate(itens, start=1):
            if item.get("trocado"):
                estilo_tabela.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#fff8e1")))
            elif idx % 2 == 0:
                estilo_tabela.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#f6f9fa")))

        tabela.setStyle(TableStyle(estilo_tabela))
        elementos.append(tabela)

        doc.build(elementos)
        buffer.seek(0)

        nome_arquivo = f"impressoras_cs_itamarati_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nome_arquivo,
        )
    except Exception as exc:
        return _erro(f"Falha ao gerar PDF: {exc}", 500)


init_db()


def criar_app():
    flask_app = Flask(__name__)
    flask_app.register_blueprint(impressoras_bp)
    return flask_app


if __name__ == "__main__":
    criar_app().run(debug=True)