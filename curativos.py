import io
import os
import sqlite3
import sys
from datetime import date

from flask import Flask, g, jsonify, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MODO_ONLINE = os.environ.get("MODO_ONLINE") == "1"

DB_PATH = os.environ.get("CURATIVOS_DB", os.path.join(os.path.dirname(__file__), "curativos.db"))

# Catálogo de materiais 
MATERIAIS_PADRAO = [
    ("ÁLCOOL ETÍLICO 70%, FRASCO 250ML", "frasco"),
    ("COMPRESSA TIPO GAZE, 7,5 X 7,5 CM, 13 FIOS, 8 DOBRAS, ESTERILIZADA", "unidade"),
    ("COMPRESSA TIPO GAZE ABERTA", "unidade"),
    ("HIPOCLORITO DE SÓDIO, A 1% FRASCO COM 1000ML", "frasco"),
    ("ESPARADRAPO 10X4,5", "unidade"),
    ("ESPARADRAPO MICROPOROSO, 25 CM X 10 M", "unidade"),
    ("ATADURA 15CM", "unidade"),
    ("AGULHA DESCARTÁVEL HIPODÉRMICA DE SEGURANÇA, TAMANHO 25 X 7", "caixa"),
    ("SERINGA DESCARTÁVEL PARA INSULINA 1ML", "unidade"),
    ("SERINGA DESCARTÁVEL 20 ML", "unidade"),
    ("SERINGA DESCARTÁVEL 10 ML", "unidade"),
    ("SERINGA DESCARTÁVEL 5 ML", "unidade"),
    ("LUVA PARA PROCEDIMENTO NÃO ESTÉRIL TAM.: P", "caixa"),
    ("LUVA PARA PROCEDIMENTO NÃO ESTÉRIL TAM.: M", "caixa"),
    ("LUVA PARA PROCEDIMENTO NÃO ESTÉRIL TAM.: G", "caixa"),
    ("SONDA URETRAL N° 12", "unidade"),
    ("SONDA URETRAL N° 14", "unidade"),
    ("COLETOR URINÁRIO EXTERNO", "caixa"),
    ("EQUIPO PARA ADMINISTRAÇÃO DE DIETA ENTERAL POR GRAVIDADE", "unidade"),
    ("FRASCO EM POLIETILENO PARA ADMINISTRAÇÃO DE DIETA ENTERAL", "unidade"),
    ("SORO FISIOLÓGICO 500ML", "unidade"),
]


app = Flask(__name__)

@app.before_request
def bloquear_curativos_online():
    if not MODO_ONLINE:
        return None
    caminhos_bloqueados = ("/curativos.html", "/api/pacientes", "/api/materiais", "/api/recibo")
    if request.path.startswith(caminhos_bloqueados):
        return "Módulo de Curativos disponível apenas na rede local da unidade.", 403
    
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(demo=False):
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT DEFAULT '',
            nascimento TEXT DEFAULT '',
            telefone TEXT DEFAULT '',
            endereco TEXT DEFAULT '',
            equipe TEXT DEFAULT '',
            programa TEXT DEFAULT 'Curativo'
        );
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            unidade TEXT DEFAULT 'unid',
            em_estoque INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS paciente_materiais (
            paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
            material_id INTEGER NOT NULL REFERENCES materiais(id) ON DELETE CASCADE,
            qtd_mensal INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (paciente_id, material_id)
        );
        """
    )
    # Migração automática de colunas novas caso o banco já exista
    cols_pac = [r[1] for r in db.execute("PRAGMA table_info(pacientes)").fetchall()]
    if "equipe" not in cols_pac:
        db.execute("ALTER TABLE pacientes ADD COLUMN equipe TEXT DEFAULT ''")
    if "nascimento" not in cols_pac:
        db.execute("ALTER TABLE pacientes ADD COLUMN nascimento TEXT DEFAULT ''")
    if "programa" not in cols_pac:
        db.execute("ALTER TABLE pacientes ADD COLUMN programa TEXT DEFAULT 'Curativo'")

    cols_mat = [r[1] for r in db.execute("PRAGMA table_info(materiais)").fetchall()]
    if "em_estoque" not in cols_mat:
        db.execute("ALTER TABLE materiais ADD COLUMN em_estoque INTEGER NOT NULL DEFAULT 1")

    # Sincroniza novos itens da lista MATERIAIS_PADRAO sem duplicar os existentes
    db.executemany("INSERT OR IGNORE INTO materiais (nome, unidade) VALUES (?, ?)", MATERIAIS_PADRAO)

    if demo and db.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO pacientes (nome, cpf, nascimento, telefone, endereco, equipe, programa) VALUES (?,?,?,?,?,?,?)",
            ("Maria da Silva (EXEMPLO)", "000.000.000-00", "1958-04-12", "(31) 90000-0000", "Rua Exemplo, 100 - Belo Horizonte/MG", "Equipe Verde", "Curativo"),
        )
        db.execute(
            "INSERT INTO pacientes (nome, cpf, nascimento, telefone, endereco, equipe, programa) VALUES (?,?,?,?,?,?,?)",
            ("José Pereira (EXEMPLO)", "111.111.111-11", "1964-09-23", "(31) 91111-1111", "Av. Teste, 200 - Belo Horizonte/MG", "Equipe Azul", "Cateterismo"),
        )
        db.executemany(
            "INSERT INTO paciente_materiais (paciente_id, material_id, qtd_mensal) VALUES (?,?,?)",
            [(1, 1, 30), (1, 3, 2), (1, 5, 4), (2, 6, 15), (2, 9, 15)],
        )
    db.commit()
    db.close()


def importar():
    init_db()
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    adicionados = 0
    atualizados = 0

  
# PÁGINAS HTML
@app.get("/")
def index():
    if MODO_ONLINE:
        return render_template("administrativo.html")
    return render_template("curativos.html")


@app.get("/curativos.html")
def pagina_curativos():
    return render_template("curativos.html")

@app.get("/administrativo.html")
def pagina_administrativo():
    return render_template("administrativo.html")


@app.get("/spe.html")
def pagina_spe():
    return render_template("spe.html")


# API PACIENTES
@app.get("/api/pacientes")
def listar_pacientes():
    q = (request.args.get("q") or "").strip()
    equipe = (request.args.get("equipe") or "").strip()
    programa = (request.args.get("programa") or "").strip()

    sql = "SELECT id, nome, cpf, nascimento, telefone, endereco, equipe, programa FROM pacientes WHERE 1=1"
    params = []

    if q:
        sql += " AND (nome LIKE ? OR cpf LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like])
    if equipe:
        sql += " AND equipe = ?"
        params.append(equipe)
    if programa:
        sql += " AND programa = ?"
        params.append(programa)

    sql += " ORDER BY nome LIMIT 200"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/pacientes/<int:pid>")
def obter_paciente(pid):
    db = get_db()
    p = db.execute("SELECT * FROM pacientes WHERE id = ?", (pid,)).fetchone()
    if not p:
        return jsonify({"erro": "Paciente não encontrado"}), 404
    kit = db.execute(
        "SELECT material_id, qtd_mensal FROM paciente_materiais WHERE paciente_id = ?", (pid,)
    ).fetchall()
    return jsonify({**dict(p), "kit": [dict(k) for k in kit]})


@app.post("/api/pacientes")
def criar_paciente():
    d = request.get_json(force=True)
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Informe o nome completo do paciente"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO pacientes (nome, cpf, nascimento, telefone, endereco, equipe, programa) VALUES (?,?,?,?,?,?,?)",
        (
            nome,
            (d.get("cpf") or "").strip(),
            (d.get("nascimento") or "").strip(),
            (d.get("telefone") or "").strip(),
            (d.get("endereco") or "").strip(),
            (d.get("equipe") or "").strip(),
            (d.get("programa") or "Curativo").strip(),
        ),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid}), 201


@app.put("/api/pacientes/<int:pid>")
def atualizar_paciente(pid):
    d = request.get_json(force=True)
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Informe o nome completo do paciente"}), 400
    db = get_db()
    if not db.execute("SELECT 1 FROM pacientes WHERE id = ?", (pid,)).fetchone():
        return jsonify({"erro": "Paciente não encontrado"}), 404
    db.execute(
        """UPDATE pacientes
           SET nome = ?, cpf = ?, nascimento = ?, telefone = ?, endereco = ?, equipe = ?, programa = ?
           WHERE id = ?""",
        (
            nome,
            (d.get("cpf") or "").strip(),
            (d.get("nascimento") or "").strip(),
            (d.get("telefone") or "").strip(),
            (d.get("endereco") or "").strip(),
            (d.get("equipe") or "").strip(),
            (d.get("programa") or "Curativo").strip(),
            pid,
        ),
    )
    db.commit()
    return jsonify({"id": pid, "ok": True})


@app.delete("/api/pacientes/<int:pid>")
def excluir_paciente(pid):
    db = get_db()
    cur = db.execute("DELETE FROM pacientes WHERE id = ?", (pid,))
    if cur.rowcount == 0:
        return jsonify({"erro": "Paciente não encontrado"}), 404
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/materiais")
def listar_materiais():
    rows = get_db().execute("SELECT id, nome, unidade, em_estoque FROM materiais ORDER BY nome").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/materiais")
def criar_material():
    d = request.get_json(force=True)
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Informe o nome do material"}), 400
    em_estoque = 1 if d.get("em_estoque", True) else 0
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO materiais (nome, unidade, em_estoque) VALUES (?, ?, ?)",
            (nome, (d.get("unidade") or "unid").strip(), em_estoque),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Esse material já existe"}), 409
    return jsonify({"id": cur.lastrowid}), 201


@app.patch("/api/materiais/<int:mid>/estoque")
def alterar_estoque_material(mid):
    d = request.get_json(force=True)
    em_estoque = 1 if d.get("em_estoque") else 0
    db = get_db()
    db.execute("UPDATE materiais SET em_estoque = ? WHERE id = ?", (em_estoque, mid))
    db.commit()
    return jsonify({"ok": True, "em_estoque": em_estoque})

@app.delete("/api/materiais/<int:mid>")
def excluir_material(mid):
    db = get_db()
    cur = db.execute("DELETE FROM materiais WHERE id = ?", (mid,))
    if cur.rowcount == 0:
        return jsonify({"erro": "Material não encontrado"}), 404
    db.commit()
    return jsonify({"ok": True})


@app.put("/api/pacientes/<int:pid>/kit")
def salvar_kit(pid):
    itens = request.get_json(force=True).get("itens", [])
    db = get_db()
    if not db.execute("SELECT 1 FROM pacientes WHERE id = ?", (pid,)).fetchone():
        return jsonify({"erro": "Paciente não encontrado"}), 404
    db.execute("DELETE FROM paciente_materiais WHERE paciente_id = ?", (pid,))
    for it in itens:
        qtd = int(it.get("qtd_mensal") or 0)
        if qtd > 0:
            db.execute(
                "INSERT INTO paciente_materiais (paciente_id, material_id, qtd_mensal) VALUES (?,?,?)",
                (pid, int(it["material_id"]), qtd),
            )
    db.commit()
    return jsonify({"ok": True})


# RECIBO EM PDF
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_extenso(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def formatar_data_br(iso_str):
    if not iso_str:
        return "—"
    try:
        d = date.fromisoformat(iso_str)
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return iso_str


# Lista de dispensadores que aparecem no recibo
DISPENSADORES = [
    "JOÃO VITOR MIRANDA MARABÁ",
    "LARISSA EMILY RAMOS COSTA",
    "MARCIO LUIZ LOPES DE MELLO SOBRINHO",
]


def montar_pdf(paciente, itens, meses, data_entrega):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title=f"Recibo - {paciente['nome']}",
    )
    base = getSampleStyleSheet()["Normal"]

    st_sec = ParagraphStyle("sec", parent=base, fontName="Helvetica-Bold", fontSize=9.5, leading=13)
    st_tit = ParagraphStyle("tit", parent=base, fontName="Helvetica-Bold", fontSize=14, alignment=1, spaceBefore=6, spaceAfter=2)
    st_sub = ParagraphStyle("sub", parent=base, fontSize=10, alignment=1, spaceAfter=8)
    st_th = ParagraphStyle("th", parent=base, fontName="Helvetica-Bold", fontSize=9.5, alignment=1)
    st_td = ParagraphStyle("td", parent=base, fontSize=9, leading=11.5)
    st_td_c = ParagraphStyle("tdc", parent=base, fontSize=9, leading=11.5, alignment=1)
    st_campo = ParagraphStyle("cmp", parent=base, fontSize=10, leading=16)
    st_disp = ParagraphStyle("dsp", parent=base, fontSize=9.5, leading=15)
    st_obs_tit = ParagraphStyle("obst", parent=base, fontName="Helvetica-Bold", fontSize=9, leading=12)
    st_obs = ParagraphStyle("obs", parent=base, fontSize=8.2, leading=11)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_pbh = os.path.join(base_dir, "static", "logo-pbh.jpeg")
    caminho_sus = os.path.join(base_dir, "static", "logo-sus.png")

    # 1. Tamanho das logos
    img_pbh = Image(caminho_pbh, width=54 * mm, height=18 * mm, kind="proportional") if os.path.exists(caminho_pbh) else ""
    img_sus = Image(caminho_sus, width=40 * mm, height=16 * mm, kind="proportional") if os.path.exists(caminho_sus) else ""

    st_cs = ParagraphStyle(
        "cs",
        parent=st_sec,
        leftIndent=15,
        spaceBefore=4,
    )

    p_sec = Paragraph("SECRETARIA MUNICIPAL DE SAÚDE", st_sec)
    p_cs = Paragraph("CENTRO DE SAÚDE ITAMARATI", st_cs)

    cabecalho = Table(
        [[img_pbh, [p_sec, p_cs], img_sus]],
        colWidths=[58 * mm, 80 * mm, 42 * mm],
    )
    cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "LEFT"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    el = [
        cabecalho,
        Spacer(1, 4),
        Paragraph("RECIBO", st_tit),
        Paragraph("Recebi o(s) medicamentos / insumo(s) abaixo", st_sub),
    ]

    # 2. Tabela de Medicamentos / Insumos
    dados = [[
        Paragraph("MEDICAMENTO / INSUMO", st_th),
        Paragraph("SITUAÇÃO", st_th),
        Paragraph("QUANTIDADE", st_th),
    ]]

    for it in itens:
        situacao = "DISPENSADO" if it.get("em_estoque", 1) else "<b>SEM ESTOQUE</b>"
        unid = it["unidade"].upper()
        if unid in ("UNID", "UNIDADE"):
            unid_txt = "UNIDADE" if it["total"] == 1 else "UNIDADES"
        elif it["total"] > 1 and not unid.endswith("S"):
            unid_txt = unid + "S"
        else:
            unid_txt = unid

        dados.append([
            Paragraph(esc(it["nome"].upper()), st_td),
            Paragraph(situacao, st_td_c),
            Paragraph(f"{it['total']} {esc(unid_txt)}", st_td_c),
        ])

    tab = Table(dados, colWidths=[104 * mm, 38 * mm, 38 * mm], repeatRows=1)
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    el.append(tab)
    el.append(Spacer(1, 30))

    # 3. Dados do paciente e campos de recebimento
    data_str = data_entrega.strftime("%d / %m / %Y") if data_entrega else "____ / ____ / ________"
    nome_pac = esc(paciente["nome"].upper())

    el.append(Paragraph(f"<b>Paciente:</b> {nome_pac}", st_campo))
    el.append(Paragraph(f"<b>Data de Entrega:</b> {data_str}", st_campo))
    el.append(Spacer(1, 14))
    bloco_entrega = Table(
        [
            [
                Paragraph("<b>Entregue para:</b> ", st_campo),
                Paragraph("<b>( &nbsp; ) paciente</b>", st_campo),
                "",
            ],
            [
                "",
                Paragraph("<b>( &nbsp; ) outro</b>", st_campo),
                Paragraph("<b>Nome:</b> ________________________________________", st_campo),
            ],
        ],
        colWidths=[28 * mm, 28 * mm, 124 * mm],
        hAlign="LEFT",
    )
    bloco_entrega.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    el.append(bloco_entrega)
    el.append(Spacer(1, 10))
    el.append(Paragraph("<b>Vínculo com paciente:</b> _________________", st_campo))
    el.append(Spacer(1, 18))
    el.append(Paragraph("<b>Assinatura:</b> _______________________________________________________", st_campo))
    el.append(Spacer(1, 10))
    el.append(Paragraph("<b>DISPENSADO POR:</b>", st_obs_tit))
    el.append(Spacer(1, 5))
    for nome_disp in DISPENSADORES:
        el.append(Paragraph(f"[ &nbsp;&nbsp; ] &nbsp; {esc(nome_disp)}", st_disp))
    el.append(Spacer(1, 30))

    periodo_txt = (
        f"ENTREGA SENDO REALIZADA PARA {meses} {'MÊS' if meses == 1 else 'MESES'}.<br/>"
        "____________________________________________________________________________________<br/><br/>"
        "AS RECEITAS DE MEDICAMENTOS SUJEITOS A CONTROLE ESPECIAL DEVERÃO SER RENOVADAS "
        "CONFORME PORTARIA MS/344/1998. PARA AS DEMAIS, A RENOVAÇÃO DEVERÁ SER SEMESTRAL, "
        "SALVO OUTRO PRAZO DETERMINADO POR ORDEM JUDICIAL, OU A CRITÉRIO DA ADMINISTRAÇÃO PÚBLICA."
    )
    quadro_obs = Table(
        [[Paragraph("OBSERVAÇÕES:", st_obs_tit)],
         [Paragraph(periodo_txt, st_obs)]],
        colWidths=[180 * mm],
    )
    quadro_obs.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    el.append(quadro_obs)

    doc.build(el)
    buf.seek(0)
    return buf


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@app.post("/api/recibo")
def gerar_recibo():
    d = request.get_json(force=True)
    try:
        pid = int(d["paciente_id"])
        meses = int(d["meses"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"erro": "Dados inválidos"}), 400
    if meses < 1 or meses > 36:
        return jsonify({"erro": "Meses deve ficar entre 1 e 36"}), 400

    db = get_db()
    paciente = db.execute("SELECT * FROM pacientes WHERE id = ?", (pid,)).fetchone()
    if not paciente:
        return jsonify({"erro": "Paciente não encontrado"}), 404

    itens = []
    for it in d.get("itens", []):
        qtd = int(it.get("qtd_mensal") or 0)
        if qtd < 1:
            continue
        m = db.execute("SELECT nome, unidade, em_estoque FROM materiais WHERE id = ?", (int(it["material_id"]),)).fetchone()
        if m:
            itens.append({
                "nome": m["nome"],
                "unidade": m["unidade"],
                "em_estoque": m["em_estoque"],
                "qtd_mensal": qtd,
                "total": qtd * meses,
            })
    if not itens:
        return jsonify({"erro": "Selecione ao menos um material"}), 400

    raw_data = (d.get("data_entrega") or "").strip()
    try:
        data_entrega = date.fromisoformat(raw_data) if raw_data else None
    except ValueError:
        data_entrega = None

    pdf = montar_pdf(dict(paciente), itens, meses, data_entrega)
    nome_arq = "recibo_" + "".join(c if c.isalnum() else "_" for c in paciente["nome"]).strip("_") + ".pdf"
    return send_file(pdf, mimetype="application/pdf", download_name=nome_arq)


if __name__ == "__main__":
    init_db(demo="--demo" in sys.argv)
    app.run(host="127.0.0.1", port=5000, debug=True)