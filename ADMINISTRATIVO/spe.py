
import os
import re
import sqlite3
from datetime import datetime

from flask import Blueprint, Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "spe.db")


RESPONSAVEIS = {
}


_DADOS = [
    # --- Esfigmomanômetro adulto (19) ---
    ("00075251", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9021406", "2024"),
    ("00075252", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9021437", "2024"),
    ("00075253", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016465", "2024"),
    ("00075254", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016750", "2024"),
    ("00075255", "Esfigmomanômetro", "Adulto", "Consultório Odontologico", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016707", "2024"),
    ("00075256", "Esfigmomanômetro", "Adulto", "Consultório 13", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9021416", "2024"),
    ("00075258", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9022535", "2024"),
    ("00075259", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016542", "2024"),
    ("00075260", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016548", "2024"),
    ("00075261", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9025384", "2024"),
    ("00075263", "Esfigmomanômetro", "Adulto", "Triagem", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9022527", "2024"),
    ("00075265", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9023956", "2024"),
    ("00075266", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016476", "2024"),
    ("00075267", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9024050", "2024"),
    ("00075268", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016466", "2024"),
    ("00075269", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016532", "2024"),
    ("00075270", "Esfigmomanômetro", "Adulto", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016534", "2024"),
    ("00075273", "Esfigmomanômetro", "Adulto", "Observação e enfermagem", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9016536", "2024"),
    ("00098923", "Esfigmomanômetro", "Adulto", "Consultório 16", "ACCUMED", "ANERÓIDE PREMIUM ADULTO", "9021418", "2024"),
    # --- Esfigmomanômetro infantil (12) ---
    ("00075309", "Esfigmomanômetro", "Infantil", "Consultório 11", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8752531", "2024"),
    ("00075310", "Esfigmomanômetro", "Infantil", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8760357", "2024"),
    ("00075311", "Esfigmomanômetro", "Infantil", "Consultório 10", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8757437", "2024"),
    ("00075312", "Esfigmomanômetro", "Infantil", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8752588", "2024"),
    ("00075313", "Esfigmomanômetro", "Infantil", "Triagem", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8752518", "2024"),
    ("00075314", "Esfigmomanômetro", "Infantil", "Observação e enfermagem", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8757488", "2024"),
    ("00075315", "Esfigmomanômetro", "Infantil", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8760479", "2024"),
    ("00075316", "Esfigmomanômetro", "Infantil", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8753403", "2024"),
    ("00075317", "Esfigmomanômetro", "Infantil", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8760347", "2024"),
    ("00075318", "Esfigmomanômetro", "Infantil", "Triagem", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8751262", "2024"),
    ("00075319", "Esfigmomanômetro", "Infantil", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8760497", "2024"),
    ("00075320", "Esfigmomanômetro", "Infantil", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM PEDIÁTRICO", "8757450", "2024"),
    # --- Esfigmomanômetro obeso (12) ---
    ("00075238", "Esfigmomanômetro", "Obeso", "Consultório 11", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "08805933", "2024"),
    ("00075239", "Esfigmomanômetro", "Obeso", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "8806182", "2024"),
    ("00075241", "Esfigmomanômetro", "Obeso", "Observação e enfermagem", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9026185", "2024"),
    ("00075242", "Esfigmomanômetro", "Obeso", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "8807891", "2024"),
    ("00075243", "Esfigmomanômetro", "Obeso", "Consultório 10", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "8807029", "2024"),
    ("00075244", "Esfigmomanômetro", "Obeso", "Observação e enfermagem", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9026697", "2024"),
    ("00075245", "Esfigmomanômetro", "Obeso", "Consultório 16", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9026186", "2024"),
    ("00075246", "Esfigmomanômetro", "Obeso", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9026674", "2024"),
    ("00075247", "Esfigmomanômetro", "Obeso", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9026154", "2024"),
    ("00075248", "Esfigmomanômetro", "Obeso", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9026158", "2024"),
    ("00075249", "Esfigmomanômetro", "Obeso", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9026685", "2024"),
    ("00075250", "Esfigmomanômetro", "Obeso", "Almoxarifado", "ACCUMED", "ANERÓIDE PREMIUM OBESO", "9027626", "2024"),
    # --- Estetoscópio adulto (21) ---
    ("00075216", "Estetoscópio", "Adulto", "Consultório Odontologico", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075217", "Estetoscópio", "Adulto", "Consultório 15", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075219", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075220", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075221", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075222", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075223", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075224", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075225", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075226", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075227", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075228", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075229", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075230", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075231", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075232", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075233", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075234", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075235", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075236", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    ("00075237", "Estetoscópio", "Adulto", "Almoxarifado", "ACCUMED", "PREMIUM ADULTO", "", "2025"),
    # --- Estetoscópio pediátrico (18) ---
    ("00075198", "Estetoscópio", "Pediátrico", "Triagem", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075199", "Estetoscópio", "Pediátrico", "Consultório 10", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075200", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075201", "Estetoscópio", "Pediátrico", "Observação e enfermagem", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075202", "Estetoscópio", "Pediátrico", "Triagem", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075203", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075204", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075205", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075206", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075207", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075208", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075209", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075210", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075211", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075212", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075213", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075214", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    ("00075215", "Estetoscópio", "Pediátrico", "Almoxarifado", "ACCUMED", "PREMIUM PEDIÁTRICO", "", "2025"),
    # --- Oftalmoscópio (1) ---
    ("00074823", "Oftalmoscópio", "", "Consultório 15", "MEDICAL DEVICES", "OMNI 300", "", "2025"),
    # --- Otoscópio (15) ---
    ("00075183", "Otoscópio", "", "Consultório 10", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075184", "Otoscópio", "", "Consultório 12", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075185", "Otoscópio", "", "Consultório 13", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075186", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075187", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075188", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075189", "Otoscópio", "", "Consultório 16", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075190", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075191", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075192", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075193", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075194", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075195", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075196", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    ("00075197", "Otoscópio", "", "Almoxarifado", "MIKATOS", "TK - LED COM 5 ESPÉCULOS", "", "2025"),
    # --- Oxímetro (2) ---
    ("00075123", "Oxímetro", "", "Observação e enfermagem", "ALFAMED", "SENSE 10", "S100121627", "2025"),
    ("00075124", "Oxímetro", "", "Triagem", "ALFAMED", "SENSE 10", "S100121628", "2025"),
    # --- Detector fetal (11) ---
    ("00069936", "Detector fetal", "", "Consultório 12", "MD", "FD-200A", "MFD2B024039129", "2024"),
    ("00069937", "Detector fetal", "", "Consultório 13", "MD", "FD-200A", "MFD2B024039156", "2024"),
    ("00069938", "Detector fetal", "", "Consultório 11", "MD", "FD-200A", "MFD2B024039130", "2024"),
    ("00069939", "Detector fetal", "", "Consultório 17", "MD", "FD-200A", "MFD2B024039176", "2024"),
    ("00069941", "Detector fetal", "", "Consultório 16", "MD", "FD-200A", "MFD2B024039131", "2024"),
    ("00069942", "Detector fetal", "", "Almoxarifado", "MD", "FD-200A", "MFD2B024039134", "2024"),
    ("00069943", "Detector fetal", "", "Almoxarifado", "MD", "FD-200A", "MFD2B024039127", "2024"),
    ("00069944", "Detector fetal", "", "Almoxarifado", "MD", "FD-200A", "MFD2B024039133", "2024"),
    ("00069945", "Detector fetal", "", "Almoxarifado", "MD", "FD-200A", "MFD2B024039178", "2024"),
    ("00069946", "Detector fetal", "", "Almoxarifado", "MD", "FD-200A", "MFD2B024039135", "2024"),
    ("00069947", "Detector fetal", "", "Almoxarifado", "MD", "FD-200A", "MFD2B024039177", "2024"),
]

# ---------------------------------------------------------------------------
# BANCO DE DADOS (SQLite)
# ---------------------------------------------------------------------------
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS spe_itens (
                patrimonio   TEXT PRIMARY KEY,
                equipamento  TEXT NOT NULL,
                tipo         TEXT NOT NULL DEFAULT '',
                fabricante   TEXT NOT NULL DEFAULT '',
                modelo       TEXT NOT NULL DEFAULT '',
                serie        TEXT NOT NULL DEFAULT '',
                ano          TEXT NOT NULL DEFAULT '',
                responsavel  TEXT NOT NULL DEFAULT '',
                sumiu        INTEGER NOT NULL DEFAULT 0,
                bo_realizado INTEGER NOT NULL DEFAULT 0,
                bo_numero    TEXT NOT NULL DEFAULT '',
                obs          TEXT NOT NULL DEFAULT '',
                sumiu_em     TEXT NOT NULL DEFAULT ''
            )"""
        )
        vazio = con.execute("SELECT COUNT(*) FROM spe_itens").fetchone()[0] == 0
        if vazio:
            con.executemany(
                """INSERT INTO spe_itens
                   (patrimonio, equipamento, tipo, fabricante, modelo, serie, ano, responsavel)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (pat, equip, tipo, fab, modelo, serie, ano, RESPONSAVEIS.get(pat, ""))
                    for (pat, equip, tipo, _local, fab, modelo, serie, ano) in _DADOS
                ],
            )


def _item_para_dict(row):
    item = dict(row)
    item["nome"] = f'{item["equipamento"]} {item["tipo"]}'.strip()
    item["sumiu"] = bool(item["sumiu"])
    item["bo_realizado"] = bool(item["bo_realizado"])
    return item


def listar_equipamentos():
    with _conn() as con:
        rows = con.execute("SELECT * FROM spe_itens ORDER BY rowid").fetchall()
    return [_item_para_dict(r) for r in rows]


def _normalizar_patrimonio(valor):
    digitos = re.sub(r"\D", "", str(valor or ""))
    return digitos.zfill(8) if digitos else ""


def _erro(msg, status=400):
    resp = jsonify({"erro": msg})
    resp.status_code = status
    return resp


def _texto(dados, campo):
    return str(dados.get(campo) or "").strip()


# ---------------------------------------------------------------------------
# ROTAS
# ---------------------------------------------------------------------------
spe_bp = Blueprint("spe", __name__)


@spe_bp.route("/")
@spe_bp.route("/spe.html")
@spe_bp.route("/spe")
def pagina_spe():
    return render_template("spe.html")


@spe_bp.route("/api/spe/equipamentos")
def api_listar():
    return jsonify(listar_equipamentos())


@spe_bp.route("/api/spe/equipamentos", methods=["POST"])
def api_adicionar():
    d = request.get_json(silent=True) or {}
    pat = _normalizar_patrimonio(d.get("patrimonio"))
    equipamento = _texto(d, "equipamento")
    if not pat:
        return _erro("Informe o número do patrimônio.")
    if not equipamento:
        return _erro("Informe o tipo do equipamento.")
    with _conn() as con:
        if con.execute("SELECT 1 FROM spe_itens WHERE patrimonio = ?", (pat,)).fetchone():
            return _erro(f"O patrimônio {pat} já está cadastrado.", 409)
        con.execute(
            """INSERT INTO spe_itens
               (patrimonio, equipamento, tipo, fabricante, modelo, serie, ano, responsavel)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pat, equipamento, _texto(d, "tipo"), _texto(d, "fabricante"), _texto(d, "modelo"),
             _texto(d, "serie"), _texto(d, "ano"), _texto(d, "responsavel")),
        )
        row = con.execute("SELECT * FROM spe_itens WHERE patrimonio = ?", (pat,)).fetchone()
    return jsonify(_item_para_dict(row)), 201


@spe_bp.route("/api/spe/equipamentos/<patrimonio>/responsavel", methods=["PUT"])
def api_responsavel(patrimonio):
    pat = _normalizar_patrimonio(patrimonio)
    d = request.get_json(silent=True) or {}
    with _conn() as con:
        cur = con.execute(
            "UPDATE spe_itens SET responsavel = ? WHERE patrimonio = ?",
            (_texto(d, "responsavel"), pat),
        )
        if cur.rowcount == 0:
            return _erro("Patrimônio não encontrado.", 404)
        row = con.execute("SELECT * FROM spe_itens WHERE patrimonio = ?", (pat,)).fetchone()
    return jsonify(_item_para_dict(row))


@spe_bp.route("/api/spe/equipamentos/<patrimonio>/sumiu", methods=["PUT"])
def api_sumiu(patrimonio):
    """Marca/desmarca como sumiu. Quando sumiu, registra se foi feito BO (e o nº, se houver)."""
    pat = _normalizar_patrimonio(patrimonio)
    d = request.get_json(silent=True) or {}
    sumiu = bool(d.get("sumiu"))
    bo = bool(d.get("bo_realizado")) if sumiu else False
    bo_numero = _texto(d, "bo_numero") if bo else ""
    obs = _texto(d, "obs") if sumiu else ""
    sumiu_em = datetime.now().strftime("%d/%m/%Y %H:%M") if sumiu else ""
    with _conn() as con:
        atual = con.execute("SELECT sumiu, sumiu_em FROM spe_itens WHERE patrimonio = ?", (pat,)).fetchone()
        if atual is None:
            return _erro("Patrimônio não encontrado.", 404)
        if sumiu and atual["sumiu"]:
            sumiu_em = atual["sumiu_em"]  # mantém a data em que foi marcado a 1ª vez
        con.execute(
            """UPDATE spe_itens
               SET sumiu = ?, bo_realizado = ?, bo_numero = ?, obs = ?, sumiu_em = ?
               WHERE patrimonio = ?""",
            (int(sumiu), int(bo), bo_numero, obs, sumiu_em, pat),
        )
        row = con.execute("SELECT * FROM spe_itens WHERE patrimonio = ?", (pat,)).fetchone()
    return jsonify(_item_para_dict(row))


init_db()


def criar_app():
    flask_app = Flask(__name__)
    flask_app.register_blueprint(spe_bp)
    return flask_app


if __name__ == "__main__":
    criar_app().run(debug=True)