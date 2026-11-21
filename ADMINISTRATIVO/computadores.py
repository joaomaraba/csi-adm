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
DB_PATH = os.path.join(BASE_DIR, "computadores.db")

_DADOS = []

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


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def formatar_patrimonio(valor):
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if "-" in texto:
        return texto
    digitos = re.sub(r"\D", "", texto)
    if not digitos:
        return ""
    digitos = digitos.zfill(12)[:12]
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:10]}.{digitos[10:12]}"


def _chave_ordenacao(item):
    andar = str(item.get("andar") or "zzz").lower()
    local = str(item.get("local") or "").lower()
    partes_local = [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", local)]
    return (int(bool(item.get("trocado"))), andar, partes_local, item.get("id", 0))


def init_db():
    with _conn() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS computadores_itens (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                andar            TEXT NOT NULL DEFAULT '',
                local            TEXT NOT NULL,
                micro            TEXT NOT NULL DEFAULT '',
                monitor          TEXT NOT NULL DEFAULT '',
                modelo           TEXT NOT NULL DEFAULT '',
                trocado          INTEGER NOT NULL DEFAULT 0,
                novo_patrimonio  TEXT NOT NULL DEFAULT '',
                novo_monitor     TEXT NOT NULL DEFAULT '',
                novo_modelo      TEXT NOT NULL DEFAULT '',
                obs              TEXT NOT NULL DEFAULT '',
                trocado_em       TEXT NOT NULL DEFAULT ''
            )"""
        )

        colunas_existentes = {
            row["name"] for row in con.execute("PRAGMA table_info(computadores_itens)").fetchall()
        }
        novas_colunas = {
            "andar": "TEXT NOT NULL DEFAULT ''",
            "trocado": "INTEGER NOT NULL DEFAULT 0",
            "novo_patrimonio": "TEXT NOT NULL DEFAULT ''",
            "novo_monitor": "TEXT NOT NULL DEFAULT ''",
            "novo_modelo": "TEXT NOT NULL DEFAULT ''",
            "obs": "TEXT NOT NULL DEFAULT ''",
            "trocado_em": "TEXT NOT NULL DEFAULT ''",
        }
        for col, tipo in novas_colunas.items():
            if col not in colunas_existentes:
                con.execute(f"ALTER TABLE computadores_itens ADD COLUMN {col} {tipo}")

        # Garante que COPA fique no 2º Andar
        con.execute("UPDATE computadores_itens SET andar = '2º Andar' WHERE UPPER(TRIM(local)) = 'COPA'")

        sem_andar = con.execute(
            "SELECT id, local FROM computadores_itens WHERE TRIM(andar) = ''"
        ).fetchall()
        for r in sem_andar:
            loc = str(r["local"] or "").strip().upper()
            if loc in _LOCAIS_1_ANDAR:
                con.execute("UPDATE computadores_itens SET andar = '1º Andar' WHERE id = ?", (r["id"],))
            elif loc in _LOCAIS_2_ANDAR:
                con.execute("UPDATE computadores_itens SET andar = '2º Andar' WHERE id = ?", (r["id"],))


def _item_para_dict(row):
    item = dict(row)
    item["andar"] = item.get("andar", "")
    item["trocado"] = bool(item.get("trocado", 0))
    item["novo_patrimonio"] = item.get("novo_patrimonio", "")
    item["novo_monitor"] = item.get("novo_monitor", "")
    item["novo_modelo"] = item.get("novo_modelo", "")
    item["obs"] = item.get("obs", "")
    item["trocado_em"] = item.get("trocado_em", "")
    return item


def listar_computadores():
    with _conn() as con:
        rows = con.execute("SELECT * FROM computadores_itens").fetchall()
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
computadores_bp = Blueprint("computadores", __name__)


@computadores_bp.route("/computadores.html")
@computadores_bp.route("/computadores")
def pagina_computadores():
    return render_template("computadores.html")


@computadores_bp.route("/api/computadores")
def api_listar():
    return jsonify(listar_computadores())


@computadores_bp.route("/api/computadores", methods=["POST"])
def api_adicionar():
    d = request.get_json(silent=True) or {}
    andar = _texto(d, "andar")
    local = _texto(d, "local")
    micro = formatar_patrimonio(d.get("micro"))
    monitor = formatar_patrimonio(d.get("monitor"))
    modelo = _texto(d, "modelo")

    if not andar:
        return _erro("Informe o andar do computador.")
    if not local:
        return _erro("Informe o local do computador.")
    if not micro and not monitor:
        return _erro("Informe pelo menos o patrimônio do micro ou do monitor.")

    with _conn() as con:
        if micro and con.execute("SELECT 1 FROM computadores_itens WHERE micro = ? AND trocado = 0", (micro,)).fetchone():
            return _erro(f"O patrimônio de micro {micro} já está cadastrado em uso.", 409)
        cur = con.execute(
            """INSERT INTO computadores_itens (andar, local, micro, monitor, modelo)
               VALUES (?, ?, ?, ?, ?)""",
            (andar, local, micro, monitor, modelo),
        )
        row = con.execute("SELECT * FROM computadores_itens WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(_item_para_dict(row)), 201


@computadores_bp.route("/api/computadores/<int:item_id>", methods=["PUT"])
def api_editar(item_id):
    d = request.get_json(silent=True) or {}
    andar = _texto(d, "andar")
    local = _texto(d, "local")
    micro = formatar_patrimonio(d.get("micro"))
    monitor = formatar_patrimonio(d.get("monitor"))
    modelo = _texto(d, "modelo")

    if not andar:
        return _erro("Informe o andar do computador.")
    if not local:
        return _erro("Informe o local do computador.")

    trocado = bool(d.get("trocado"))
    novo_micro = formatar_patrimonio(d.get("novo_patrimonio")) if trocado else ""
    novo_monitor = formatar_patrimonio(d.get("novo_monitor")) if trocado else ""
    novo_modelo = _texto(d, "novo_modelo") if trocado else ""
    obs = _texto(d, "obs") if trocado else ""
    trocado_em = datetime.now().strftime("%d/%m/%Y %H:%M") if trocado else ""

    if trocado:
        if not novo_micro and not novo_monitor:
            return _erro("Informe o novo patrimônio do micro ou do monitor.")
        if not novo_modelo:
            return _erro("Informe o modelo do novo computador.")

    novo_criado = None

    with _conn() as con:
        atual = con.execute(
            "SELECT * FROM computadores_itens WHERE id = ?", (item_id,)
        ).fetchone()
        if atual is None:
            return _erro("Computador não encontrado.", 404)

        ja_estava_trocado = bool(atual["trocado"])
        if trocado and ja_estava_trocado:
            trocado_em = atual["trocado_em"]

        con.execute(
            """UPDATE computadores_itens
               SET andar = ?, local = ?, micro = ?, monitor = ?, modelo = ?,
                   trocado = ?, novo_patrimonio = ?, novo_monitor = ?, novo_modelo = ?, obs = ?, trocado_em = ?
               WHERE id = ?""",
            (andar, local, micro, monitor, modelo, int(trocado), novo_micro, novo_monitor, novo_modelo, obs, trocado_em, item_id),
        )

        if trocado and (novo_micro or novo_monitor):
            existe_novo = con.execute(
                """SELECT 1 FROM computadores_itens
                   WHERE andar = ? AND local = ? AND micro = ? AND monitor = ? AND trocado = 0""",
                (andar, local, novo_micro, novo_monitor),
            ).fetchone()
            if not existe_novo:
                cur_novo = con.execute(
                    """INSERT INTO computadores_itens (andar, local, micro, monitor, modelo)
                       VALUES (?, ?, ?, ?, ?)""",
                    (andar, local, novo_micro, novo_monitor, novo_modelo),
                )
                row_novo = con.execute(
                    "SELECT * FROM computadores_itens WHERE id = ?", (cur_novo.lastrowid,)
                ).fetchone()
                novo_criado = _item_para_dict(row_novo)

        row = con.execute("SELECT * FROM computadores_itens WHERE id = ?", (item_id,)).fetchone()

    return jsonify({"item": _item_para_dict(row), "novo_item": novo_criado})


@computadores_bp.route("/api/computadores/<int:item_id>", methods=["DELETE"])
def api_excluir(item_id):
    with _conn() as con:
        cur = con.execute("DELETE FROM computadores_itens WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            return _erro("Computador não encontrado.", 404)
    return jsonify({"ok": True})


@computadores_bp.route("/api/computadores/pdf", methods=["POST"])
def api_gerar_pdf():
    try:
        d = request.get_json(silent=True) or {}
        itens = d.get("itens")
        if itens is None:
            itens = listar_computadores()

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
            title="Relatório de Computadores - CS Itamarati",
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
            Paragraph("Centro de Saúde Itamarati — Inventário de Computadores", estilo_titulo),
            Paragraph(
                f"Emitido em {agora} &nbsp;|&nbsp; Filtro: <b>{filtro_desc}</b> &nbsp;|&nbsp; Total listado: <b>{len(itens)}</b>",
                estilo_sub,
            ),
        ]

        ativos = [i for i in itens if not i.get("trocado")]
        qtd_think = sum(1 for i in ativos if "thinkcentre" in str(i.get("modelo", "")).lower())
        qtd_pos = sum(1 for i in ativos if "positivo" in str(i.get("modelo", "")).lower())
        qtd_outros = len(ativos) - qtd_think - qtd_pos

        tabela_resumo = Table(
            [
                ["CS ITAMARATI — Resumo dos itens em uso listados", "", "", ""],
                [
                    f"THINKCENTRE: {qtd_think}",
                    f"POSITIVO: {qtd_pos}",
                    f"Outros modelos: {qtd_outros}",
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

        linhas = [["Andar", "Local", "Patrimônio Micro", "Patrimônio Monitor", "Modelo", "Situação"]]
        for item in itens:
            situacao = "Trocado" if item.get("trocado") else "Em uso"
            linhas.append([
                Paragraph(str(item.get("andar") or "—"), estilo_celula),
                Paragraph(str(item.get("local") or "—"), estilo_celula_bold),
                Paragraph(str(item.get("micro") or "Sem patrimônio"), estilo_celula),
                Paragraph(str(item.get("monitor") or "Sem monitor"), estilo_celula),
                Paragraph(str(item.get("modelo") or "—"), estilo_celula),
                Paragraph(situacao, estilo_celula_bold if item.get("trocado") else estilo_celula),
            ])

        tabela = Table(
            linhas,
            colWidths=[28 * mm, 64 * mm, 48 * mm, 48 * mm, 46 * mm, 35 * mm],
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

        nome_arquivo = f"computadores_cs_itamarati_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
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
    flask_app.register_blueprint(computadores_bp)
    return flask_app


if __name__ == "__main__":
    criar_app().run(debug=True)