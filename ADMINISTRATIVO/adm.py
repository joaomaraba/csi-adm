from curativos import app
from spe import spe_bp
from computadores import computadores_bp
from flask import render_template
from impressoras import impressoras_bp

app.register_blueprint(computadores_bp)
app.register_blueprint(impressoras_bp)
app.register_blueprint(spe_bp)

if __name__ == "__main__":
    app.run(debug=True)
